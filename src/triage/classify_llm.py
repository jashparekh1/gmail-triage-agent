from __future__ import annotations
import json, os
from typing import Literal, TypedDict
import google.generativeai as genai

Label = Literal["urgent", "non-urgent", "promo"]

class LlmResult(TypedDict):
    label: Label
    reason: str

SYSTEM = """You are labeling emails for daily triage.

Labels:
- urgent: Needs timely attention or action (deadlines, failed payments, account/security, advisor/school items, interviews, time-sensitive updates).
- promo: Marketing/newsletters/sales/bulk promos/social notifications.
- non-urgent: Everything else (FYI, general discussions, low-priority updates).

Return STRICT JSON only:
{"label":"urgent|non-urgent|promo","reason":"<very short why>"}

If torn between urgent vs non-urgent, choose urgent. Never include extra text.
"""

def _ensure_model():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set. Put it in .env or shell env.")
    genai.configure(api_key=api_key)
    # fast & cheap; upgrade to 1.5-pro if you want
    return genai.GenerativeModel("gemini-1.5-flash")

def _extract_json(text: str) -> dict:
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        raise ValueError(f"LLM did not return JSON: {text[:120]}...")
    return json.loads(text[s:e+1])

def classify_with_gemini(subject: str, sender: str, snippet: str) -> LlmResult:
    model = _ensure_model()
    user_payload = f"Subject: {subject or '(no subject)'}\nFrom: {sender}\nSnippet: {snippet[:600]}"
    resp = model.generate_content(
        [{"role":"user","parts":[SYSTEM]},
         {"role":"user","parts":[user_payload]}]
    )
    obj = _extract_json(resp.text.strip())
    label = str(obj.get("label","non-urgent")).strip().lower()
    if label not in ("urgent","non-urgent","promo"):
        label = "non-urgent"
    reason = str(obj.get("reason",""))
    return {"label": label, "reason": reason}  # type: ignore[return-value]
