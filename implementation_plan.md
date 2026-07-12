# Implementation Plan - Groq API Integration for End-to-End Voice Chat

We will integrate the Groq API into the agricultural advisor system backend. This will enable ultra-fast Speech-to-Text (STT) via Groq Whisper, and conversational completions and translations via Groq's LLMs (`llama-3.3-70b-versatile` or `llama-3.1-8b-instant`), delivering a highly responsive voice-to-voice chat experience for farmers.

## User Review Required

> [!IMPORTANT]
> The **C:** drive is completely full (0 bytes free), so I am saving this implementation plan and all workspace changes directly to the **F:** drive where space is available.
>
> We will add a `GROQ_API_KEY` placeholder inside `.env.local`. You will need to provide your Groq API key there.

## Proposed Changes

### Configuration

#### [MODIFY] [.env.local](file:///f:/FProjects/project%20folder/Advisory%20agricultue%20week-1-2/.env.local)
- Add `GROQ_API_KEY` variable.

---

### Backend Components

#### [MODIFY] [backend/main.py](file:///f:/FProjects/project%20folder/Advisory%20agricultue%20week-1-2/backend/main.py)
- Import and read `GROQ_API_KEY` from the environment.
- Add `query_groq_parser` to `NLPManager` class to extract language, intent, and entities using Groq (which is much faster and cheaper than OpenAI GPT-4o-mini).
- Implement `groq_translate` as a translation helper function.
- Integrate Groq chat completion (`llama-3.3-70b-versatile`) in `/api/chat` to formulate responses.
- Integrate Groq Whisper (`whisper-large-v3` or `whisper-large-v3-turbo`) in `/api/stt` to transcribe speech instantly.
- Update `/api/health` to expose Groq configuration state.

---

## Verification Plan

### Automated Tests
- Run backend FastAPI server and check health check endpoint.
- Verify status code and correctness of STT and Chat endpoints via requests or curl.

### Manual Verification
- Start the server using `npm run dev` (which runs Next.js) and start Python backend.
- Test frontend microphone transcription and text synthesis (TTS).
