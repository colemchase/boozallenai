import json
import re


def _payload(event):
    if isinstance(event, dict):
        for key in ("payload", "body", "input", "arguments"):
            val = event.get(key)
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    return {"text": val}
            if isinstance(val, dict):
                return val
        return event
    if isinstance(event, str):
        return {"text": event}
    return {}


def _text(payload):
    for key in ("text", "question", "prompt", "message", "challenge", "input"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return json.dumps(payload)


def _extract_eob(text):
    # Prefer the JSON object following the challenge lead-in.
    m = re.search(r"ExplanationOfBenefit:\s*(\{.*\})\s*$", text, re.S)
    if m:
        return json.loads(m.group(1))
    # Fallback: first outer JSON object in the text.
    start = text.find("{")
    if start < 0:
        return {"item": []}
    return json.loads(text[start:])


def _first_code(obj, *path):
    cur = obj
    for part in path:
        if isinstance(part, int):
            if not isinstance(cur, list) or len(cur) <= part:
                return ""
            cur = cur[part]
        else:
            if not isinstance(cur, dict):
                return ""
            cur = cur.get(part, {})
    return cur if isinstance(cur, str) else ""


def _adjudication_amounts(item):
    amounts = {}
    for adj in item.get("adjudication", []) or []:
        code = _first_code(adj, "category", "coding", 0, "code")
        value = adj.get("amount", {}).get("value", 0) or 0
        if code:
            amounts[code] = float(value)
    return amounts


def _is_denied(item):
    for coding in item.get("reviewOutcome", {}).get("decision", {}).get("coding", []) or []:
        if str(coding.get("code", "")).lower() == "denied":
            return True
    return False


def _service_code(item):
    return _first_code(item, "productOrService", "coding", 0, "code")


def _carc(item):
    return _first_code(item, "reviewOutcome", "reason", "coding", 0, "code")


def _fmt_money(value):
    return f"{value:.2f}"


def _answer(eob):
    total_allowed = 0.0
    member_resp = 0.0
    denied_lines = []

    for item in eob.get("item", []) or []:
        amounts = _adjudication_amounts(item)
        if _is_denied(item):
            member_resp += amounts.get("submitted", 0.0)
            denied_lines.append({"code": _service_code(item), "carc": _carc(item)})
        else:
            eligible = amounts.get("eligible", 0.0)
            benefit = amounts.get("benefit", 0.0)
            total_allowed += eligible
            member_resp += eligible - benefit

    # Build manually so money has two decimal places as JSON numbers in the text.
    denied = json.dumps(denied_lines, separators=(",", ":"))
    return f'{{"TotalAllowed":{_fmt_money(total_allowed)},"MemberResponsibility":{_fmt_money(member_resp)},"DeniedLines":{denied}}}'


def lambda_handler(event, context):
    payload = _payload(event)
    text = _text(payload)
    try:
        eob = _extract_eob(text)
        answer = _answer(eob)
        return {
            "statusCode": 200,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"answer": answer}, separators=(",", ":")),
        }
    except Exception as exc:
        return {
            "statusCode": 200,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"answer": "", "error": str(exc)}, separators=(",", ":")),
        }
