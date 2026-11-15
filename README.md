# SwasthyaVaani — AI-Driven Healthcare Assistance Platform

Helps rural patients understand prescriptions in their own language (English, Hindi, Gujarati):
photo of a prescription → AI reads it → simple explanation → voice → medicine schedule → reminders.

**Stack:** FastAPI · PostgreSQL · SQLAlchemy · Alembic · JWT (Argon2) · React 19 · Vite · Axios

## Features
| Feature | Status |
|---|---|
| Patient / healthcare-worker registration, JWT login, role-based access | Done |
| Profile and language preference | Done |
| Prescription photo upload (validated, size-limited, access-controlled) | Done |
| AI reading + medicine extraction + simplification + translation (Hindi, Gujarati, English) | Done — one vision-LLM pipeline; providers: Gemini, Anthropic, OpenAI; demo mode without a key |
| Original and simplified text side by side, with a "not medical advice" notice | Done |
| Human safety check: low-confidence results go to a healthcare-worker review queue | Done |
| Voice: read prescriptions and reminders aloud (browser text-to-speech) | Done — needs a voice for the language on the device |
| Medication schedule generated from the prescription, mark doses taken, missed-dose detection | Done |
| Reminders: notifications + spoken reminders + on-screen "take now" banner | Done — while the app is open |
| Offline mode: saved prescriptions/schedule viewable without internet; app shell cached (PWA) | Done |
| Patient, healthcare-worker and admin dashboards, user management, platform statistics | Done |
| Emergency numbers (112, 108, 102, 1098) | Done |
| Image compression before upload (saves mobile data) | Done |
| Health education content, knowledge base, symptom explanation | Planned |
| Speech-to-text voice queries, recommendation engine | Planned |
| Caregiver notifications, background push reminders, native mobile apps (React Native + SQLite) | Planned |
| Docker deployment | Planned |

## Run the backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # fill in DATABASE_URL and SECRET_KEY
alembic upgrade head
python -m scripts.create_admin # creates the first administrator
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

### Turn on real AI reading
In `backend/.env` set the provider and key (a free Google Gemini key works):
```
AI_PROVIDER="gemini"      # or anthropic / openai
AI_API_KEY="your-key"
```
Leave `AI_PROVIDER="mock"` for demos without a key — the app clearly labels the output as sample data.
Prescription photos are sent to the chosen AI provider; get patient consent before using real data.

### Run the tests
```bash
cd backend
pytest
```
Tests use their own database and never touch the one in `.env`.

## Run the frontend
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:5173

## Roles
| Role | Page | Created by |
|---|---|---|
| Patient | `/patient` | Self-registration |
| Healthcare worker | `/worker` | Self-registration |
| Administrator | `/admin` | `python -m scripts.create_admin` only |

## Known limitations
- Reminders fire only while the app is open (background push needs the native app or web-push, planned).
- Spoken Gujarati/Hindi depends on the voices installed on the device.
- AI output can be wrong; every result carries a disclaimer and unsure results are queued for a healthcare worker.
- Healthcare workers can currently see all patients (no assignment model yet).
