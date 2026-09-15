import json
import re
from typing import Any, Dict, List

DIRS = {"up", "down", "left", "right"}


def _json_load(value: Any):
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return None


def _extract_path(value: Any) -> List[str]:
    """Return a clean list of direction strings from strings, arrays, or common wrappers."""
    parsed = _json_load(value)

    if isinstance(parsed, dict):
        # Studio or examples may wrap as {path:[...]}, {output:{path:[...]}}, or {ground_truth:{path:[...]}}
        for key in ("path", "answer", "completion", "output", "ground_truth", "expected"):
            if key in parsed:
                found = _extract_path(parsed[key])
                if found:
                    return found
        return []

    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, str)]

    if isinstance(value, str):
        # Extract the first JSON array from prose/tool text.
        m = re.search(r"\[[\s\S]*?\]", value)
        if m:
            try:
                arr = json.loads(m.group(0))
                if isinstance(arr, list):
                    return [x for x in arr if isinstance(x, str)]
            except Exception:
                return []
    return []


def _assistant_response(sample: Dict[str, Any]) -> Any:
    for key in ("completion", "response", "answer", "model_output", "output"):
        if key in sample:
            return sample[key]
    for msg in sample.get("messages", []) or sample.get("prompt", []) or []:
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            return msg.get("content", "")
    return ""


def _ground_truth(sample: Dict[str, Any]) -> Any:
    rm = sample.get("reward_model", {}) or {}
    return rm.get("ground_truth") or sample.get("ground_truth") or sample.get("reference_answer", {}).get("text", "")


def reward_function(sample: Dict[str, Any], index: int) -> Dict[str, Any]:
    expected = _extract_path(_ground_truth(sample))
    actual = _extract_path(_assistant_response(sample))

    valid_array = 1.0 if actual else 0.0
    exact_match = 1.0 if actual and actual == expected else 0.0
    valid_dirs = (sum(1 for x in actual if x in DIRS) / len(actual)) if actual else 0.0

    prefix = 0
    if expected and actual:
        for a, b in zip(actual, expected):
            if a != b:
                break
            prefix += 1
    prefix_score = prefix / max(len(expected), 1) if expected else 0.0
    length_score = max(0.0, 1.0 - abs(len(actual) - len(expected)) / max(len(expected), 1)) if expected else 0.0

    aggregate = 1.0 if exact_match else (0.15 * valid_array + 0.20 * valid_dirs + 0.45 * prefix_score + 0.20 * length_score)

    return {
        "id": str(sample.get("id", sample.get("extra_info", {}).get("index", f"sample-{index:03d}"))),
        "aggregate_reward_score": float(max(0.0, min(1.0, aggregate))),
        "metrics_list": [
            {"name": "exact_match", "value": float(exact_match), "type": "Reward"},
            {"name": "valid_array", "value": float(valid_array), "type": "Metric"},
            {"name": "valid_directions", "value": float(valid_dirs), "type": "Metric"},
            {"name": "prefix_match", "value": float(prefix_score), "type": "Metric"},
            {"name": "length_match", "value": float(length_score), "type": "Metric"},
        ],
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        batch = event.get("input", event) if isinstance(event, dict) else event
        if isinstance(event, dict) and "batch" in event:
            batch = event.get("batch", [])
        elif isinstance(event, dict) and "body" in event:
            body = json.loads(event.get("body") or "{}")
            batch = body.get("batch", [])
        if isinstance(batch, dict):
            batch = [batch]
        if not batch:
            return {"error": "Missing or empty batch"}
        results = [reward_function(sample, i) for i, sample in enumerate(batch)]
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(results)}
    except Exception as exc:
        return {"statusCode": 400, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": str(exc)})}
