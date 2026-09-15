import json
import re
from typing import Any, Dict


def _loads(value: Any):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("path"), list):
            return value.get("path")
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict) and isinstance(parsed.get("path"), list):
                return parsed.get("path")
            return parsed
        except Exception:
            m = re.search(r"\[[\s\S]*\]", value)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    return None
    return None


def _assistant_response(sample: Dict[str, Any]) -> str:
    for key in ("completion", "response", "answer", "model_output"):
        val = sample.get(key)
        if isinstance(val, str):
            return val
    for msg in sample.get("messages", []) or sample.get("prompt", []) or []:
        if msg.get("role") == "assistant":
            return msg.get("content", "")
    return ""


def _ground_truth(sample: Dict[str, Any]):
    rm = sample.get("reward_model", {}) or {}
    return rm.get("ground_truth") or sample.get("ground_truth") or sample.get("reference_answer", {}).get("text", "")


def reward_function(sample: Dict[str, Any], index: int) -> Dict[str, Any]:
    response = _assistant_response(sample)
    expected = _loads(_ground_truth(sample))
    actual = _loads(response)

    valid_array = 1.0 if isinstance(actual, list) else 0.0
    exact_match = 1.0 if isinstance(actual, list) and actual == expected else 0.0

    valid_dirs_set = {"up", "down", "left", "right"}
    valid_dirs = 0.0
    prefix_score = 0.0
    length_score = 0.0
    if isinstance(expected, list) and isinstance(actual, list) and actual:
        valid_dirs = sum(1 for x in actual if x in valid_dirs_set) / len(actual)
        prefix = 0
        for a, b in zip(actual, expected):
            if a != b:
                break
            prefix += 1
        prefix_score = prefix / max(len(expected), 1)
        length_score = max(0.0, 1.0 - abs(len(actual) - len(expected)) / max(len(expected), 1))

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
