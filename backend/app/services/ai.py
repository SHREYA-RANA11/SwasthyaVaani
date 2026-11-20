"""Prescription reading + translation pipeline.

One vision-capable LLM call does OCR, medicine extraction, simplification and
translation together. Providers: gemini | anthropic | openai | mock.
"""
import base64
import json
import re
from io import BytesIO
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field, field_validator
from PIL import (
    Image,
    ImageEnhance,
    ImageFilter,
    ImageOps,
    ImageStat,
    UnidentifiedImageError,
)

from app.core.config import settings

LANGUAGES = {
    "English": "English",
    "Hindi": "Hindi (Devanagari script, simple everyday words)",
    "Gujarati": "Gujarati (Gujarati script, simple everyday words)",
}

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-sonnet-5-5",
    "openai": "gpt-4o",
}

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
DEFAULT_TIMES = {
    1: ["08:00"],
    2: ["08:00", "20:00"],
    3: ["08:00", "14:00", "20:00"],
    4: ["06:00", "12:00", "18:00", "22:00"],
    5: ["06:00", "10:00", "14:00", "18:00", "22:00"],
    6: ["06:00", "09:00", "12:00", "15:00", "18:00", "21:00"],
}


class AIError(Exception):
    """An error whose message is safe to show to the user."""


# ---------- result schema (validated, so bad AI output can never break the app) ----------

class AIMedicine(BaseModel):
    name: str
    dose: Optional[str] = None
    frequency_per_day: int = 1
    times: List[str] = Field(default_factory=list)
    duration_days: Optional[int] = None
    food: str = "any"
    instructions_simple: Optional[str] = None
    instructions_original: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def _name(cls, v):
        v = str(v or "").strip()
        if not v:
            raise ValueError("medicine name missing")
        return v[:200]

    @field_validator("frequency_per_day", mode="before")
    @classmethod
    def _freq(cls, v):
     try:
        value = int(v)
        if not 0 <= value <= 6:
            raise ValueError("Invalid medicine frequency")
        return value
     except (TypeError, ValueError):
        raise ValueError("Medicine frequency is unclear")

    @field_validator("duration_days", mode="before")
    @classmethod
    def _dur(cls, v):
        try:
            n = int(v)
            return n if 1 <= n <= 365 else None
        except (TypeError, ValueError):
            return None

    @field_validator("food", mode="before")
    @classmethod
    def _food(cls, v):
        v = str(v or "any").strip().lower()
        return v if v in {"before_food", "after_food", "with_food", "any"} else "any"

    @field_validator("times", mode="before")
    @classmethod
    def _times(cls, v):
        if not isinstance(v, list):
            return []
        clean = [str(t).strip() for t in v if TIME_RE.match(str(t).strip())]
        return sorted(set(clean))

    def finalize(self) -> "AIMedicine":
        """
        Keep only explicitly extracted medicine timings.
        Never invent clock times when the prescription is unclear.
        """
        if self.frequency_per_day == 0:
            self.times = []
        elif len(self.times) != self.frequency_per_day:
            self.times = []

        return self


class AIResult(BaseModel):
    is_prescription: bool = True
    doctor_name: Optional[str] = None
    diagnosis: Optional[str] = None
    extracted_text: str = ""
    summary: str = ""
    medicines: List[AIMedicine] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    follow_up: Optional[str] = None
    confidence: str = "medium"
    needs_review: bool = False

    @field_validator("medicines", mode="before")
    @classmethod
    def _meds(cls, v):
        # Keep usable entries only, so one bad medicine never rejects the whole result
        if not isinstance(v, list):
            return []
        keep = []
        for m in v:
            if isinstance(m, AIMedicine):
                keep.append(m)
            elif isinstance(m, dict) and str(m.get("name") or "").strip():
                keep.append(m)
        return keep

    @field_validator("warnings", mode="before")
    @classmethod
    def _warn(cls, v):
        return [str(w).strip() for w in v if w] if isinstance(v, list) else []

    @field_validator("extracted_text", "summary", mode="before")
    @classmethod
    def _text(cls, v):
        return "" if v is None else str(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _conf(cls, v):
        v = str(v or "medium").lower()
        return v if v in {"high", "medium", "low"} else "medium"


# ---------- prompt ----------

SYSTEM_PROMPT = """You are a careful assistant that helps rural patients in India understand medical prescriptions.
You will be shown a photo of a prescription or medical document.

Rules:

1. ACCURATE OCR TRANSCRIPTION:

   Carefully inspect the entire prescription image before extracting information.

   - Read all visible text, including headings, medicine names,
     dosages, handwritten notes and instructions.
   - Preserve the original wording and spelling in extracted_text.
   - Do not silently correct spelling or complete partially visible words.
   - Do not guess medicine names from familiar drug names or context.
   - If text is illegible, represent it as "[illegible]" in extracted_text.
   - If a specific medicine detail cannot be read confidently,
     set that field to null and needs_review to true.
   - Do not omit difficult-to-read sections.

2. MEDICINE NAME AND DOSE ACCURACY:

   - Keep medicine names in their original Latin script.
   - Preserve brand names and generic names exactly as written.
   - Never substitute a familiar medicine for an unclear medicine name.
   - Keep strength and dosage separate from medicine names.
   - Do not confuse tablet strength, number of tablets and frequency.
   - If the medicine name or dosage is uncertain, flag it for human review.
3. Write "summary", "instructions_simple", "warnings" and "follow_up" in the requested language, in short,
   simple, everyday words a person with little schooling can understand. No medical jargon.
   - Only include warnings that are explicitly written in the prescription.
   - Never invent medication cautions, side effects, or treatment advice.
   - If no warning is written, return an empty warnings list.
4. MEDICAL ABBREVIATION SAFETY:

   - Expand an abbreviation only when its meaning is clear
     from the prescription context.
   - OD/QD may mean once daily, but OD can also mean right eye.
     Do not interpret OD as once daily in an eye prescription.
   - BD/BID = twice daily, TDS/TID = three times daily,
     QID = four times daily, HS = at bedtime.
   - SOS/PRN = as needed, AC = before food,
     PC = after food.
   - If an abbreviation has multiple possible meanings,
     do not guess. Preserve it in extracted_text,
     leave the affected field null where appropriate,
     and set needs_review to true.
5. "times" are 24-hour "HH:MM" clock times.

   Only extract clock times when they are explicitly written
   in the prescription.

   Do not invent or assume clock times based on frequency.

   If the prescription says once daily, twice daily,
   or three times daily but does not specify clock times:
   - Extract frequency_per_day correctly.
   - Set times to an empty list.
   - Set needs_review to true.

   Never present suggested timings as doctor's instructions.
6. "frequency_per_day" is an integer 0-6 (0 = only when needed, with an empty "times" list).
7. "food" is one of: before_food, after_food, with_food, any.
8. If the image is not a medical document, set "is_prescription" to false and leave the lists empty.
9. Set "confidence" to high, medium or low. Set "needs_review" to true if handwriting is hard to read,
   any dose is unclear, or you are less than very sure about any medicine.

10. STRICT MEDICINE DURATION RULE:
    A medicine's duration must come only from an instruction that
    clearly applies to that specific medicine.

    NEVER interpret general advice such as:
    - "Rest for 4 days"
    - "Take rest"
    - "Follow up after 4 days"
    - "Review after one week"

    as the duration of a medicine.

    Only extract duration when the prescription explicitly links
    the duration to a particular medicine, such as:
    "Amoxicillin 250 mg - three times daily for 5 days."

    If the duration is missing, ambiguous, or cannot confidently
    be linked to that medicine:
    - Set duration_days to null.
    - Set needs_review to true.
    - Do not invent a duration.

Reply with ONE JSON object and nothing else, in exactly this shape:
{
  "is_prescription": true,
  "doctor_name": null,
  "diagnosis": null,
  "extracted_text": "full text as printed, in its original language",
  "summary": "2-4 simple sentences: what this prescription is for and what the patient should do",
  "medicines": [
    {"name": "", "dose": null, "frequency_per_day": 1, "times": [], "duration_days": null,
     "food": "after_food", "instructions_simple": "", "instructions_original": ""}
  ],
  "warnings": [],,
  "follow_up": null,
  "confidence": "high",
  "needs_review": false
}"""


def _user_prompt(language: str) -> str:
    return (
        f"Read this prescription. Write summary, instructions_simple, warnings and follow_up in "
        f"{LANGUAGES.get(language, language)}. Return only the JSON object."
    )


# ---------- providers ----------

def _model() -> str:
    return settings.AI_MODEL or DEFAULT_MODELS.get(settings.AI_PROVIDER, "")


def _post(url: str, headers: dict, body: dict) -> dict:
    try:
        r = httpx.post(url, headers=headers, json=body, timeout=settings.AI_TIMEOUT_SECONDS)
    except httpx.TimeoutException:
        raise AIError("The AI service took too long to respond. Please try again.")
    except httpx.HTTPError:
        raise AIError("Could not reach the AI service. Check the internet connection and try again.")
    if r.status_code in (401, 403):
        raise AIError("The AI service rejected the API key. Check AI_API_KEY on the server.")
    if r.status_code == 404:
        raise AIError("AI model not found. Check AI_MODEL on the server.")
    if r.status_code == 429:
        raise AIError("The AI service is busy or the free limit was reached. Please try again shortly.")
    if r.status_code >= 400:
        raise AIError(f"The AI service returned an error ({r.status_code}). Please try again.")
    try:
        return r.json()
    except ValueError:
        raise AIError("The AI service returned an unreadable response.")


def _call_anthropic(image: bytes, mime: str, language: str) -> str:
    data = _post(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": settings.AI_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        {
            "model": _model(), "max_tokens": 4000, "temperature": 0.1, "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime,
                                             "data": base64.b64encode(image).decode()}},
                {"type": "text", "text": _user_prompt(language)},
            ]}],
        },
    )
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _call_gemini(image: bytes, mime: str, language: str) -> str:
    data = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{_model()}:generateContent",
        {"x-goog-api-key": settings.AI_API_KEY, "content-type": "application/json"},
        {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [
                {"inline_data": {"mime_type": mime, "data": base64.b64encode(image).decode()}},
                {"text": _user_prompt(language)},
            ]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        },
    )
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        raise AIError("The AI could not read this image (it may have been blocked). Try a clearer photo.")
    return "".join(p.get("text", "") for p in parts)


def _call_openai(image: bytes, mime: str, language: str) -> str:
    url = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    data = _post(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {settings.AI_API_KEY}", "content-type": "application/json"},
        {
            "model": _model(), "temperature": 0.1, "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": _user_prompt(language)},
                    {"type": "image_url", "image_url": {"url": url}},
                ]},
            ],
        },
    )
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise AIError("The AI returned an unexpected response.")


# ---------- demo mode (no API key) ----------

_MOCK = {
    "English": {
        "summary": "This prescription is for a fever and a mild stomach infection. Take the tablets on time, "
                   "drink plenty of clean water and finish the full course.",
        "para": "Take 1 tablet after food. Do not take more than 3 tablets in a day.",
        "amox": "Take 1 capsule after food, three times a day. Finish all capsules even if you feel better.",
        "ors": "Mix 1 packet in a glass of clean water. Drink small sips after each loose motion.",
        "warnings": ["Finish the full course of capsules.", "Go to a doctor if the fever lasts more than 3 days."],
        "follow": "Visit the clinic after 5 days.",
    },
    "Hindi": {
        "summary": "यह पर्चा बुखार और पेट के हल्के संक्रमण के लिए है। दवा समय पर लें, खूब साफ़ पानी पिएं "
                   "और पूरा कोर्स खत्म करें।",
        "para": "खाने के बाद 1 गोली लें। एक दिन में 3 गोली से ज़्यादा न लें।",
        "amox": "खाने के बाद दिन में तीन बार 1 कैप्सूल लें। ठीक लगने पर भी सारे कैप्सूल खत्म करें।",
        "ors": "साफ़ पानी के 1 गिलास में 1 पैकेट घोलें। हर बार दस्त के बाद थोड़ा-थोड़ा पिएं।",
        "warnings": ["कैप्सूल का पूरा कोर्स खत्म करें।", "अगर बुखार 3 दिन से ज़्यादा रहे तो डॉक्टर को दिखाएं।"],
        "follow": "5 दिन बाद क्लिनिक आएं।",
    },
    "Gujarati": {
        "summary": "આ ચિઠ્ઠી તાવ અને પેટના હળવા ચેપ માટે છે. દવા સમયસર લો, પુષ્કળ સ્વચ્છ પાણી પીઓ "
                   "અને આખો કોર્સ પૂરો કરો.",
        "para": "જમ્યા પછી 1 ગોળી લો. એક દિવસમાં 3 ગોળીથી વધુ ન લો.",
        "amox": "જમ્યા પછી દિવસમાં ત્રણ વાર 1 કેપ્સ્યુલ લો. સારું લાગે તો પણ બધી કેપ્સ્યુલ પૂરી કરો.",
        "ors": "સ્વચ્છ પાણીના 1 ગ્લાસમાં 1 પેકેટ ભેળવો. દરેક ઝાડા પછી થોડું થોડું પીઓ.",
        "warnings": ["કેપ્સ્યુલનો આખો કોર્સ પૂરો કરો.", "તાવ 3 દિવસથી વધુ રહે તો ડૉક્ટરને બતાવો."],
        "follow": "5 દિવસ પછી ક્લિનિક આવો.",
    },
}


def _mock(language: str) -> AIResult:
    t = _MOCK.get(language, _MOCK["English"])
    return AIResult(
        doctor_name="Dr. Sample (demo)",
        diagnosis="Fever with mild stomach infection (demo data)",
        extracted_text="DEMO MODE - no AI key configured, so this is sample text, not your image.\n"
                       "Tab. Paracetamol 500 mg  1-0-1 x 5 days (PC)\n"
                       "Cap. Amoxicillin 250 mg  1-1-1 x 5 days (PC)\nORS sachet  SOS",
        summary=t["summary"],
        medicines=[
            AIMedicine(name="Paracetamol 500 mg", dose="1 tablet", frequency_per_day=2, times=["08:00", "20:00"],
                       duration_days=5, food="after_food", instructions_simple=t["para"],
                       instructions_original="Tab. Paracetamol 500 mg 1-0-1 x 5 days PC"),
            AIMedicine(name="Amoxicillin 250 mg", dose="1 capsule", frequency_per_day=3,
                       times=["08:00", "14:00", "20:00"], duration_days=5, food="after_food",
                       instructions_simple=t["amox"], instructions_original="Cap. Amoxicillin 250 mg 1-1-1 x 5 days PC"),
            AIMedicine(name="ORS sachet", dose="1 packet", frequency_per_day=0, times=[], duration_days=None,
                       food="any", instructions_simple=t["ors"], instructions_original="ORS sachet SOS"),
        ],
        warnings=t["warnings"], follow_up=t["follow"], confidence="high", needs_review=False,
    )
def assess_image_quality(image_bytes: bytes) -> dict:
    """
    Assess prescription image quality before AI analysis.

    Returns image measurements and warnings.
    Does not reject images automatically.
    """
    try:
        with Image.open(BytesIO(image_bytes)) as original:
            original.load()
            img = ImageOps.exif_transpose(original).convert("RGB")

            width, height = img.size
            gray = img.convert("L")

            # Average brightness: 0 (dark) to 255 (bright).
            stats = ImageStat.Stat(gray)
            brightness = stats.mean[0]

            # Contrast indicator.
            contrast = stats.stddev[0]

            # Initial sharpness indicator using edge information.
              # Laplacian variance: preliminary blur indicator.
            laplacian = ImageFilter.Kernel(
              size=(3, 3),
               kernel=(0, 1, 0, 1, -4, 1, 0, 1, 0),
               scale=1,
               offset=128,
)

            laplacian_image = gray.filter(laplacian)
            sharpness = ImageStat.Stat(laplacian_image).var[0]

            warnings = []

            if width < 600 or height < 600:
                warnings.append("low_resolution")

            if brightness < 50:
                warnings.append("image_too_dark")
            # elif brightness > 220:
            #     warnings.append("image_too_bright")

            if contrast < 25:
                warnings.append("low_contrast")

            if sharpness < 55:
                warnings.append("possible_blur")

            return {
                "width": width,
                "height": height,
                "brightness": round(brightness, 2),
                "contrast": round(contrast, 2),
                "sharpness": round(sharpness, 2),
                "is_acceptable": len(warnings) == 0,
                "warnings": warnings,
            }

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        raise AIError(
            "The prescription image could not be assessed. "
            "Please upload a valid image."
        )

def _preprocess_image(image_bytes: bytes, mime: str) -> tuple[bytes, str]:
    """
    Prepare a separate image copy for AI analysis.
    The original uploaded prescription remains unchanged.
    """
    try:
        with Image.open(BytesIO(image_bytes)) as original:
            original.load()

            # Correct orientation using EXIF metadata.
            img = ImageOps.exif_transpose(original)

            # Convert transparent images onto a white background.
            if img.mode in ("RGBA", "LA") or "transparency" in img.info:
                rgba = img.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                img = background
            else:
                img = img.convert("RGB")

            # Resize only when the image is larger than 2400 pixels.
            max_dimension = 2400

            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)

                new_size = (
                    max(1, round(img.width * ratio)),
                    max(1, round(img.height * ratio)),
                )

                img = img.resize(
                    new_size,
                    Image.Resampling.LANCZOS,
                )

            # Apply mild contrast enhancement.
            img = ImageEnhance.Contrast(img).enhance(1.10)

            # Encode an optimized JPEG for vision analysis.
            output = BytesIO()
            img.save(
                output,
                format="JPEG",
                quality=92,
                optimize=True,
            )

            return output.getvalue(), "image/jpeg"

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        raise AIError(
            "The prescription image could not be processed. "
            "Please upload a clear JPG, PNG or WEBP image."
        )


# ---------- public entry point ----------

def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except ValueError:
                pass
    raise AIError("The AI returned an answer in an unexpected format. Please try again.")


def analyze_prescription(image: bytes, mime: str, language: str) -> AIResult:
    provider = settings.AI_PROVIDER.lower()
    if provider == "mock":
        return _mock(language)

    callers = {"anthropic": _call_anthropic, "gemini": _call_gemini, "openai": _call_openai}
    if provider not in callers:
        raise AIError(f"Unknown AI_PROVIDER '{settings.AI_PROVIDER}'. Use mock, gemini, anthropic or openai.")
    if not settings.AI_API_KEY:
        raise AIError("AI_API_KEY is not set on the server.")

    # Preprocess a separate copy before sending it to the vision model.
    image, mime = _preprocess_image(image, mime)

    raw = callers[provider](image, mime, language)
    payload = _parse_json(raw)
    try:
        result = AIResult.model_validate(payload)
    except Exception:
        raise AIError("The AI returned incomplete data. Please try again with a clearer photo.")

    # Finalize medicine timings without inventing clock times.
    result.medicines = [m.finalize() for m in result.medicines]

    if not result.is_prescription:
        raise AIError(
        "This does not look like a prescription or medical document. "
        "Please upload a clear photo of one."
    )

# Require healthcare-worker review when important information is missing.
    if result.confidence == "low" or not result.medicines:
       result.needs_review = True

    for medicine in result.medicines:
      if (
        not medicine.dose
        or medicine.duration_days is None
        or (
            medicine.frequency_per_day > 0
            and not medicine.times
        )
    ):
        result.needs_review = True
    return result
def test_small_image_dimensions_preserved():
    original = create_image("JPEG", size=(400, 300))

    processed, mime = _preprocess_image(original, "image/jpeg")

    with Image.open(BytesIO(processed)) as image:
        assert image.size == (400, 300) 