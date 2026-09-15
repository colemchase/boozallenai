import json
import os
import re

CACHE_PATH = "/tmp/grey_code_cache.json"
_CACHE = {}


def _load_cache():
    global _CACHE
    if _CACHE:
        return _CACHE
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                _CACHE = data
    except Exception:
        _CACHE = {}
    return _CACHE


def _save_cache():
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_CACHE, f, separators=(",", ":"))
    except Exception:
        pass


def _event_payload(event):
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
    parts = []
    for key in ("text", "question", "prompt", "message", "challenge", "input"):
        val = payload.get(key)
        if isinstance(val, str):
            parts.append(val)
    return "\n".join(parts)


def _extract_key(text):
    m = re.search(r"\b(?P<color>[A-Za-z]+)\s+key\s+(?P<number>\d+)\s+is\s*:\s*(?P<key>\S+)", text, re.I)
    if not m:
        m = re.search(r"\b(?P<color>[A-Za-z]+)\s+key\s+(?P<number>\d+)\s+is\s+(?P<key>\S+)", text, re.I)
    if not m:
        return None
    key = m.group("key").strip().strip('"\'.,;')
    return {
        "color": m.group("color").lower(),
        "number": m.group("number"),
        "key": key,
        "code": (key[:2] + key[-2:]) if len(key) >= 2 else key,
    }


def _extract_door(text):
    m = re.search(r"\b(?P<color>[A-Za-z]+)\s+code\s+(?P<number>\d+)\b", text, re.I)
    if not m:
        return None
    return {"color": m.group("color").lower(), "number": m.group("number")}


def _ok(obj):
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(obj, separators=(",", ":")),
    }


def lambda_handler(event, context):
    payload = _event_payload(event)
    text = _text(payload)
    cache = _load_cache()

    key_info = _extract_key(text)
    if key_info:
        color = key_info["color"]
        number = key_info["number"]
        code = key_info["code"]
        cache_key = f"{color}:{number}"
        cache[cache_key] = {"key": key_info["key"], "code": code}
        _save_cache()
        return _ok({
            "mode": "key",
            "color": color,
            "number": number,
            "key": key_info["key"],
            "code": code,
            "memory": f"{color} code {number} = {code}",
        })

    door_info = _extract_door(text)
    if door_info:
        color = door_info["color"]
        number = door_info["number"]
        cache_key = f"{color}:{number}"
        stored = cache.get(cache_key, {})
        code = stored.get("code", "")
        return _ok({
            "mode": "door",
            "color": color,
            "number": number,
            "code": code,
            "answer": code,
            "memory_key": f"{color} code {number}",
        })

    return _ok({"mode": "unknown", "answer": ""})
