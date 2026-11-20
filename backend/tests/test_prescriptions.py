from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.services import ai

from io import BytesIO
from PIL import Image

def make_test_jpeg():
    buffer = BytesIO()
    image = Image.new("RGB", (100, 100), color="white")
    image.save(buffer, format="JPEG")
    return buffer.getvalue()

JPEG = make_test_jpeg()
IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).date().isoformat()


def upload(client, headers, language="Hindi", data=JPEG, name="rx.jpg"):
    return client.post("/prescriptions", headers=headers, data={"language": language, "title": "Fever"},
                       files={"file": (name, data, "image/jpeg")})


# ---------- security ----------

def test_admin_self_registration_does_not_exist(client):
    r = client.post("/auth/register/admin", json={"full_name": "Evil", "email": "e@test.com", "password": "password123"})
    assert r.status_code == 404


def test_requires_login(client):
    assert client.get("/prescriptions").status_code in (401, 403)


def test_only_patients_can_upload(client, people):
    assert upload(client, people["w"]).status_code == 403


# ---------- upload + AI pipeline (mock provider) ----------

def test_upload_and_translation(client, people):
    r = upload(client, people["p1"], "Hindi")
    assert r.status_code == 201, r.text
    rx = r.json()
    assert rx["status"] == "processed" and rx["ai_provider"] == "mock"
    assert "बुखार" in rx["summary"]                       # simplified, in Hindi
    assert len(rx["medications"]) == 3
    assert rx["medications"][0]["start_date"] == TODAY
    assert rx["disclaimer"]


def test_gujarati_and_retranslate(client, people):
    rx = upload(client, people["p1"], "Gujarati").json()
    assert "તાવ" in rx["summary"]
    r = client.post(f"/prescriptions/{rx['id']}/analyze", headers=people["p1"], json={"language": "English"})
    assert r.status_code == 200 and r.json()["language"] == "English"
    assert "fever" in r.json()["summary"].lower()
    assert client.post(f"/prescriptions/{rx['id']}/analyze", headers=people["p1"], json={"language": "French"}).status_code == 422


def test_rejects_non_images_and_huge_files(client, people):
    assert upload(client, people["p1"], data=b"%PDF-1.4 not an image", name="x.jpg").status_code == 415
    assert upload(client, people["p1"], data=b"MZ\x90\x00 virus", name="x.jpg").status_code == 415
    big = JPEG + b"0" * (settings.MAX_UPLOAD_MB * 1024 * 1024)
    assert upload(client, people["p1"], data=big).status_code == 413


def test_patients_cannot_see_each_others_records(client, people):
    rx = upload(client, people["p1"]).json()
    assert client.get(f"/prescriptions/{rx['id']}", headers=people["p2"]).status_code == 404
    assert client.get(f"/prescriptions/{rx['id']}/file", headers=people["p2"]).status_code == 404
    assert client.delete(f"/prescriptions/{rx['id']}", headers=people["p2"]).status_code == 404
    assert all(i["id"] != rx["id"] for i in client.get("/prescriptions", headers=people["p2"]).json())
    # owner and healthcare worker can open the original image
    assert client.get(f"/prescriptions/{rx['id']}/file", headers=people["p1"]).content == JPEG
    assert client.get(f"/prescriptions/{rx['id']}", headers=people["w"]).status_code == 200


def test_delete_removes_record_and_file(client, people):
    rx = upload(client, people["p1"]).json()
    assert client.delete(f"/prescriptions/{rx['id']}", headers=people["p1"]).status_code == 204
    assert client.get(f"/prescriptions/{rx['id']}", headers=people["p1"]).status_code == 404


# ---------- medication schedule + reminders ----------

def test_schedule_and_marking_doses(client, people):
    # fresh patient so the schedule only has this prescription
    client.post(
    "/auth/register/patient",
    json={
        "full_name": "Sched",
        "email": "s@test.com",
        "password": "password123",
        "native_language": "Gujarati",
        "preferred_language": "English",
    },
)
    h = {"Authorization": "Bearer " + client.post("/auth/login", json={"email": "s@test.com", "password": "password123"}).json()["access_token"]}
    upload(client, h)

    d = client.get("/doses", headers=h, params={"date": TODAY, "now": "10:30"}).json()
    assert d["total"] == 5 and len(d["as_needed"]) == 1           # 2 + 3 doses, ORS only when needed
    by = {(x["medication_name"], x["scheduled_time"]): x["status"] for x in d["doses"]}
    assert by[("Paracetamol 500 mg", "08:00")] == "missed"
    assert by[("Amoxicillin 250 mg", "14:00")] == "upcoming"
    assert d["missed"] == 2

    d = client.get("/doses", headers=h, params={"date": TODAY, "now": "08:20"}).json()
    assert {x["status"] for x in d["doses"] if x["scheduled_time"] == "08:00"} == {"due"}

    med = next(x for x in d["doses"] if x["medication_name"] == "Paracetamol 500 mg")["medication_id"]
    assert client.post("/doses/mark", headers=h, json={"medication_id": med, "date": TODAY, "time": "08:00"}).status_code == 204
    assert client.post("/doses/mark", headers=h, json={"medication_id": med, "date": TODAY, "time": "08:00"}).status_code == 204  # idempotent
    d = client.get("/doses", headers=h, params={"date": TODAY, "now": "10:30"}).json()
    assert d["taken"] == 1 and d["missed"] == 1
    client.post("/doses/mark", headers=h, json={"medication_id": med, "date": TODAY, "time": "08:00", "taken": False})
    assert client.get("/doses", headers=h, params={"date": TODAY, "now": "10:30"}).json()["taken"] == 0

    assert client.post("/doses/mark", headers=h, json={"medication_id": med, "date": TODAY, "time": "03:33"}).status_code == 404
    # after the 5-day course the schedule is empty
    later = (datetime.now(IST).date() + timedelta(days=6)).isoformat()
    assert client.get("/doses", headers=h, params={"date": later, "now": "09:00"}).json()["total"] == 0


def test_cannot_mark_someone_elses_dose(client, people):
    rx = upload(client, people["p1"]).json()
    med = rx["medications"][0]["id"]
    r = client.post("/doses/mark", headers=people["p2"], json={"medication_id": med, "date": TODAY, "time": "08:00"})
    assert r.status_code == 404


# ---------- safety: human review ----------

def test_low_confidence_goes_to_review_queue(client, people, monkeypatch):
    def fake(image, mime, language):
        return ai.AIResult(summary="x", confidence="low", needs_review=True,
                           medicines=[ai.AIMedicine(name="Unclear drug").finalize()])
    monkeypatch.setattr(ai, "analyze_prescription", fake)
    rx = upload(client, people["p1"]).json()
    assert rx["needs_review"] is True

    q = client.get("/prescriptions", headers=people["w"], params={"needs_review": True}).json()
    assert rx["id"] in [i["id"] for i in q]
    assert client.post(f"/prescriptions/{rx['id']}/review", headers=people["p1"]).status_code == 403  # patients can't verify

    r = client.post(f"/prescriptions/{rx['id']}/review", headers=people["w"]).json()
    assert r["needs_review"] is False and r["reviewed_by_name"] == "Dr Asha" and r["reviewed_at"]
    q = client.get("/prescriptions", headers=people["w"], params={"needs_review": True}).json()
    assert rx["id"] not in [i["id"] for i in q]


def test_ai_failure_is_saved_and_retry_works(client, people, monkeypatch):
    def boom(image, mime, language):
        raise ai.AIError("The AI service took too long to respond. Please try again.")
    monkeypatch.setattr(ai, "analyze_prescription", boom)
    rx = upload(client, people["p1"]).json()
    assert rx["status"] == "failed" and "too long" in rx["error_message"] and rx["medications"] == []
    monkeypatch.undo()
    r = client.post(f"/prescriptions/{rx['id']}/analyze", headers=people["p1"], json={"language": "Hindi"}).json()
    assert r["status"] == "processed" and r["error_message"] is None and len(r["medications"]) == 3


def test_admin_stats_include_prescriptions(client, people):
    s = client.get("/admin/stats", headers=people["a"]).json()
    assert s["total_prescriptions"] >= 1 and "prescriptions_needing_review" in s


# ---------- real providers: request shape + tolerant parsing (HTTP is faked) ----------

class FakeResp:
    def __init__(self, status, body):
        self.status_code, self._b = status, body
    def json(self):
        return self._b


MESSY = ('```json\n{"is_prescription": true, "summary": "ok", "confidence": "HIGH", "medicines": ['
         '{"name": "Metformin 500", "frequency_per_day": "2", "times": ["8am", "25:99"], "food": "AFTER_FOOD", "duration_days": "30"},'
         '{"name": "", "frequency_per_day": 1},'
         '{"name": "Cetirizine", "frequency_per_day": 0, "times": ["08:00"]}], "warnings": ["a", null]}\n```')


def _check(result):
    assert result.needs_review is True
    assert [m.name for m in result.medicines] == ["Metformin 500", "Cetirizine"]   # nameless one dropped
    m, c = result.medicines
    assert m.times == []           # invalid times replaced by a consistent schedule
    assert m.food == "after_food" and m.duration_days == 30 and m.frequency_per_day == 2
    assert c.times == []                           # "only when needed" has no clock times
    assert result.confidence == "high" and result.warnings == ["a"]


@pytest.mark.parametrize("provider,reply,assert_request", [
    ("anthropic", {"content": [{"type": "text", "text": MESSY}]},
     lambda u, h, b: h["x-api-key"] == "KEY" and b["messages"][0]["content"][0]["type"] == "image" and "anthropic" in u),
    ("gemini", {"candidates": [{"content": {"parts": [{"text": MESSY}]}}]},
     lambda u, h, b: h["x-goog-api-key"] == "KEY" and "inline_data" in b["contents"][0]["parts"][0] and "generativelanguage" in u),
    ("openai", {"choices": [{"message": {"content": MESSY}}]},
     lambda u, h, b: h["Authorization"] == "Bearer KEY" and b["messages"][1]["content"][1]["type"] == "image_url"),
])
def test_providers(monkeypatch, provider, reply, assert_request):
    seen = {}
    def fake_post(url, headers=None, json=None, timeout=None):
        seen["ok"] = assert_request(url, headers, json)
        return FakeResp(200, reply)
    monkeypatch.setattr(ai.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "AI_PROVIDER", provider)
    monkeypatch.setattr(settings, "AI_API_KEY", "KEY")
    _check(ai.analyze_prescription(JPEG, "image/jpeg", "Hindi"))
    assert seen["ok"]


@pytest.mark.parametrize("status,needle", [(401, "API key"), (404, "model"), (429, "busy"), (500, "error")])
def test_provider_errors_are_friendly(monkeypatch, status, needle):
    monkeypatch.setattr(ai.httpx, "post", lambda *a, **k: FakeResp(status, {}))
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "AI_API_KEY", "KEY")
    with pytest.raises(ai.AIError, match=needle):
        ai.analyze_prescription(JPEG, "image/jpeg", "English")


def test_not_a_prescription_and_garbage_and_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(settings, "AI_API_KEY", "KEY")
    for text, needle in [('{"is_prescription": false}', "does not look like"), ("sorry, I cannot", "unexpected format")]:
        monkeypatch.setattr(ai.httpx, "post", lambda *a, t=text, **k: FakeResp(200, {"choices": [{"message": {"content": t}}]}))
        with pytest.raises(ai.AIError, match=needle):
            ai.analyze_prescription(JPEG, "image/jpeg", "English")
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    with pytest.raises(ai.AIError, match="AI_API_KEY"):
        ai.analyze_prescription(JPEG, "image/jpeg", "English")
    monkeypatch.setattr(settings, "AI_PROVIDER", "nonsense")
    with pytest.raises(ai.AIError, match="Unknown"):
        ai.analyze_prescription(JPEG, "image/jpeg", "English")

def test_general_rest_instruction_is_not_medicine_duration():
    result = ai.AIResult.model_validate({
        "is_prescription": True,
        "extracted_text": (
            "Tab. Paracetamol 500 mg twice daily. "
            "Rest for 4 days."
        ),
        "summary": "Take the medicine as prescribed.",
        "medicines": [
            {
                "name": "Paracetamol 500 mg",
                "dose": "1 tablet",
                "frequency_per_day": 2,
                "times": ["08:00", "20:00"],
                "duration_days": None,
                "food": "any"
            }
        ],
        "confidence": "medium",
        "needs_review": True
    })

    medicine = result.medicines[0]

    assert medicine.duration_days is None
    assert result.needs_review is True
