"""
PromptCraft backend — Vercel Python serverless function.

Runs a 3-stage prompt chain against any OpenAI-compatible chat completions API:
  1. Extraction   — few-shot prompting to pull structured data out of a resume
  2. Gap analysis — zero-shot prompting to compare that data against a job description
  3. Rewrite      — chain-of-thought + role prompting to produce targeted bullet rewrites

Configure via environment variables (set these in Vercel project settings):
  LLM_API_KEY   (required)  API key for your provider
  LLM_BASE_URL  (optional)  default: https://api.openai.com/v1
                            for Groq (free tier): https://api.groq.com/openai/v1
  LLM_MODEL     (optional)  default: gpt-4o-mini
                            for Groq: e.g. llama-3.1-8b-instant (check Groq's current model list)
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import requests


EXTRACTION_SYSTEM = (
    "You are a precise resume parser. Output only valid JSON, no commentary, "
    "no markdown code fences."
)

EXTRACTION_FEWSHOT = """Example:
Resume: "Software engineer with 3 years experience in Python, Django, and PostgreSQL. \
Led a team of 4 to build an internal analytics tool."
JSON: {"skills": ["Python", "Django", "PostgreSQL", "Team Leadership"], \
"experience_years": 3, "roles": ["Software Engineer"], \
"highlights": ["Led a team of 4 to build an internal analytics tool"]}

Example:
Resume: "Recent CS graduate. Built a React + Node.js e-commerce site as a capstone project. \
Familiar with REST APIs and MongoDB."
JSON: {"skills": ["React", "Node.js", "REST APIs", "MongoDB"], "experience_years": 0, \
"roles": ["Student / New Grad"], "highlights": ["Built a React + Node.js e-commerce capstone project"]}"""

GAP_SYSTEM = (
    "You are a technical recruiter performing a skills gap analysis between a "
    "candidate profile and a job description. Be specific, concise, and honest — "
    "do not inflate the match. Structure your answer as: Matched Skills, Missing "
    "Skills, and a one-line Fit Verdict."
)

REWRITE_SYSTEM = (
    "You are an expert technical recruiter and resume coach. You write sharp, "
    "metric-driven, ATS-friendly resume bullet points. Think through the gap "
    "analysis step by step to decide what each bullet should emphasize, but only "
    "output the final 3 numbered bullet points — no reasoning, no preamble."
)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("LLM_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        raise RuntimeError("LLM_API_KEY environment variable is not set")

    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"LLM API error {resp.status_code}: {resp.text[:300]}")

    return resp.json()["choices"][0]["message"]["content"].strip()


def run_chain(resume: str, jd: str) -> dict:
    extraction = call_llm(
        EXTRACTION_SYSTEM,
        f"{EXTRACTION_FEWSHOT}\n\nResume:\n{resume}\n\nExtract as JSON:",
    )
    gap_analysis = call_llm(
        GAP_SYSTEM,
        f"Extracted candidate profile:\n{extraction}\n\nJob description:\n{jd}\n\n"
        "Provide the gap analysis.",
    )
    rewrite = call_llm(
        REWRITE_SYSTEM,
        f"Extracted candidate profile:\n{extraction}\n\nGap analysis:\n{gap_analysis}\n\n"
        "Give exactly 3 rewritten resume bullet points that address the gaps above.",
    )
    return {"extraction": extraction, "gap_analysis": gap_analysis, "rewrite": rewrite}


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""

        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Request body must be valid JSON."})
            return

        resume = (data.get("resume") or "").strip()
        jd = (data.get("jd") or "").strip()

        if not resume or not jd:
            self._send_json(400, {"error": "Both 'resume' and 'jd' fields are required."})
            return

        try:
            result = run_chain(resume, jd)
        except RuntimeError as exc:
            self._send_json(502, {"error": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": f"Unexpected server error: {exc}"})
            return

        self._send_json(200, result)