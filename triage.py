"""Ticket triage logic: LLM-based, with a keyword fallback when no API key is set."""
import json
import os

MODEL = os.getenv("TRIAGE_MODEL", "claude-sonnet-5-5")
CATEGORIES = ["billing", "technical", "account", "sales", "other"]
PRIORITIES = ["low", "medium", "high"]

SYSTEM_PROMPT = (
    "You triage customer support tickets. Respond with ONLY a JSON object, "
    "no markdown, with keys: category (one of billing, technical, account, "
    "sales, other), priority (low, medium, high), summary (one sentence), "
    "draft_reply (a short, polite reply)."
)


def _fallback(message: str) -> dict:
    text = message.lower()
    if any(w in text for w in ("charge", "refund", "invoice", "payment")):
        category = "billing"
    elif any(w in text for w in ("error", "crash", "bug", "not working", "broken")):
        category = "technical"
    elif any(w in text for w in ("password", "login", "account")):
        category = "account"
    elif any(w in text for w in ("price", "quote", "demo", "buy")):
        category = "sales"
    else:
        category = "other"
    urgent = any(w in text for w in ("urgent", "asap", "immediately", "down"))
    return {
        "category": category,
        "priority": "high" if urgent else "medium",
        "summary": message[:100],
        "draft_reply": "Thanks for reaching out. We've received your message and will respond shortly.",
        "source": "fallback",
    }


def _validate(data: dict) -> dict:
    if data.get("category") not in CATEGORIES:
        data["category"] = "other"
    if data.get("priority") not in PRIORITIES:
        data["priority"] = "medium"
    data.setdefault("summary", "")
    data.setdefault("draft_reply", "")
    return data


def triage_message(message: str) -> dict:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return _fallback(message)
    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        data = _validate(json.loads(response.content[0].text))
        data["source"] = "llm"
        return data
    except Exception:
        # Never fail the request because the LLM failed or returned bad JSON.
        return _fallback(message)
