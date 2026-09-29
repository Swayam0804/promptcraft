# PromptCraft: An Adaptive Resume Analyzer Using Prompt Chaining

PromptCraft runs a candidate's resume and a target job description through a
3-stage prompt chain instead of one generic prompt:

1. **Extraction** (few-shot) — pulls structured skills/experience out of the resume.
2. **Gap Analysis** (zero-shot) — compares that profile against the job description.
3. **Rewrite** (chain-of-thought + role prompting) — produces 3 targeted bullet rewrites.

Each stage's output is shown separately in the UI.

## Setup

1. Get an API key from an OpenAI-compatible provider (OpenAI, or Groq for a free tier).
2. In your Vercel project settings, add environment variables:
   - `LLM_API_KEY` — your key
   - `LLM_BASE_URL` — optional, defaults to `https://api.openai.com/v1`
   - `LLM_MODEL` — optional, defaults to `gpt-4o-mini`
3. Deploy. No build step needed — this is a static frontend plus a Python serverless function.

## Local testing
Install deps: `pip install requests`
Vercel CLI: `vercel dev`