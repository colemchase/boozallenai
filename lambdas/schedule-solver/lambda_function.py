import json
import re


def lambda_handler(event, context):
    try:
        text = _text(event)
        sections = _extract_sections(text)
        result = _solve(sections)
        answer = json.dumps(result, separators=(",", ":"))
        return {"statusCode": 200, "body": json.dumps({"answer": answer})}
    except Exception as exc:
        fallback = {"FlaggedSections": [], "Consolidations": [], "NoAction": []}
        return {"statusCode": 200, "body": json.dumps({"answer": json.dumps(fallback, separators=(",", ":")), "error": str(exc)})}


def _text(event):
    if isinstance(event, str):
        return event
    if isinstance(event, dict):
        if "body" in event:
            body = event["body"]
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except Exception:
                    return body
            if isinstance(body, dict):
                event = body
        for k in ("question", "prompt", "text", "input"):
            v = event.get(k)
            if isinstance(v, str) and v.strip():
                return v
        return json.dumps(event)
    return ""


def _norm_time(raw):
    raw = (raw or "").strip()
    raw = re.sub(r"\s+", " ", raw)
    return raw


def _course_near(text, start):
    prefix = text[max(0, start - 220):start]
    # Prefer latest course code before the section.
    matches = [m for m in re.findall(r"\b([A-Z]{2,6}-\d{3,4})\b", prefix) if not m.startswith("SEC-")]
    return matches[-1] if matches else ""


def _instructor_near(text, start, end):
    window = text[max(0, start - 160):min(len(text), end + 160)]
    m = re.search(r"\b(Dr\.|Prof\.|Professor)\s+([A-Z][A-Za-z'-]+)", window)
    if not m:
        return ""
    title = "Prof." if m.group(1).lower().startswith("prof") else "Dr."
    return f"{title} {m.group(2)}"


def _time_from_text(window):
    patterns = [
        r"\b(Monday/Wednesday/Friday|MWF)\s+(?:at\s+)?(\d{1,2}\s*(?:AM|PM))",
        r"\b(Tuesday/Thursday|TTH|TR)\s+(?:at\s+)?(\d{1,2}\s*(?:AM|PM))",
        r"\b(MWF|TTH|TR)\s*(\d{1,2}\s*(?:AM|PM))",
        r"\bon\s+([A-Za-z/]+)\s+(?:at\s+)?(\d{1,2}\s*(?:AM|PM))",
    ]
    for pat in patterns:
        m = re.search(pat, window, re.I)
        if m:
            return _norm_time((m.group(1) + " " + m.group(2)).upper().replace("MONDAY/WEDNESDAY/FRIDAY", "MWF").replace("TUESDAY/THURSDAY", "TTH"))
    return ""


def _time_near(text, start, end, middle=""):
    # Prefer text attached to this section; only then use a small local fallback.
    return _time_from_text(middle) or _time_from_text(text[start:min(len(text), end + 80)])


def _extract_sections(text):
    sections = []
    seen = set()
    # Capture SEC-101 ... 12 out of 35, SEC-101 ... 12 students enrolled out of 35, etc.
    pat = re.compile(
        r"\b(SEC-\d{3,4})\b(?P<middle>.{0,180}?)(?:with\s+only\s+|with\s+|has\s+|is\s+running\s+)?(\d+)\s+(?:students\s+)?(?:enrolled\s+)?(?:out\s+of|of|/)\s+(\d+)",
        re.I | re.S,
    )
    for m in pat.finditer(text):
        sid = m.group(1).upper()
        if sid in seen:
            continue
        seen.add(sid)
        start, end = m.span()
        course = _course_near(text, start)
        sections.append({
            "sectionId": sid,
            "courseName": course,
            "instructor": _instructor_near(text, start, end),
            "timeSlot": _time_near(text, start, end, m.group("middle")),
            "enrolled": int(m.group(3)),
            "capacity": int(m.group(4)),
        })
    return sections


def _solve(sections):
    flagged = [s for s in sections if s.get("capacity", 0) and (s["enrolled"] / s["capacity"]) < 0.50]
    flagged_ids = [s["sectionId"] for s in flagged]
    used = set()
    consolidations = []

    for i, a in enumerate(flagged):
        if a["sectionId"] in used:
            continue
        best = None
        for b in flagged[i + 1:]:
            if b["sectionId"] in used:
                continue
            if a.get("courseName") != b.get("courseName"):
                continue
            if a.get("timeSlot") and b.get("timeSlot") and a.get("timeSlot") == b.get("timeSlot"):
                continue
            keep, cancel = (a, b) if a["enrolled"] >= b["enrolled"] else (b, a)
            combined = a["enrolled"] + b["enrolled"]
            if combined <= keep["capacity"]:
                cand = (keep, cancel, combined)
                if best is None or combined > best[2]:
                    best = cand
        if best:
            keep, cancel, combined = best
            consolidations.append({
                "keep": keep["sectionId"],
                "cancel": cancel["sectionId"],
                "combinedEnrollment": combined,
                "capacity": keep["capacity"],
            })
            used.add(keep["sectionId"])
            used.add(cancel["sectionId"])

    no_action = [s["sectionId"] for s in flagged if s["sectionId"] not in used]
    return {"FlaggedSections": flagged_ids, "Consolidations": consolidations, "NoAction": no_action}
