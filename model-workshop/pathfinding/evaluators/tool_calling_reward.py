import json
import re
from typing import Any, Dict


def _loads(value: Any):
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return None


def _assistant_response(sample: Dict[str, Any]) -> str:
    for key in ("completion", "response", "answer", "model_output"):
        val = sample.get(key)
        if isinstance(val, str):
            return val
    for msg in sample.get("messages", []) or sample.get("prompt", []) or []:
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            return msg.get("content", "")
    return ""


def _ground_truth(sample: Dict[str, Any]) -> Dict[str, Any]:
    rm = sample.get("reward_model", {}) or {}
    gt = rm.get("ground_truth") or sample.get("ground_truth") or sample.get("reference_answer", {}).get("text", "")
    parsed = _loads(gt)
    return parsed if isinstance(parsed, dict) else {}


def _extract_tool_call(text: str) -> Dict[str, Any]:
    if not isinstance(text, str):
        return {}
    m = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.S)
    raw = m.group(1) if m else text.strip()
    parsed = _loads(raw)
    return parsed if isinstance(parsed, dict) else {}


def _norm_args(args: Any) -> Dict[str, Any]:
    if isinstance(args, str):
        parsed = _loads(args)
        return parsed if isinstance(parsed, dict) else {}
    return args if isinstance(args, dict) else {}


def reward_function(sample: Dict[str, Any], index: int) -> Dict[str, Any]:
    response = _assistant_response(sample)
    gt = _ground_truth(sample)
    call = _extract_tool_call(response)

    expected_fn = (gt.get("function") or {}).get("name") or "pathfinding_lambda"
    expected_args = _norm_args((gt.get("function") or {}).get("arguments"))

    actual_name = call.get("name") or (call.get("function") or {}).get("name")
    actual_args = _norm_args(call.get("arguments") or (call.get("function") or {}).get("arguments"))

    valid_json = 1.0 if call else 0.0
    correct_tool = 1.0 if actual_name == expected_fn else 0.0
    exact_prompt = 1.0 if actual_args.get("prompt") == expected_args.get("prompt") else 0.0
    has_prompt = 1.0 if isinstance(actual_args.get("prompt"), str) and len(actual_args.get("prompt")) > 20 else 0.0
    concise = 1.0 if len(response) < 2500 else 0.0

    aggregate = 0.15 * valid_json + 0.30 * correct_tool + 0.45 * exact_prompt + 0.05 * has_prompt + 0.05 * concise

    return {
        "id": str(sample.get("id", sample.get("extra_info", {}).get("index", f"sample-{index:03d}"))),
        "aggregate_reward_score": float(max(0.0, min(1.0, aggregate))),
        "metrics_list": [
            {"name": "valid_tool_call_json", "value": float(valid_json), "type": "Metric"},
            {"name": "correct_tool", "value": float(correct_tool), "type": "Reward"},
            {"name": "exact_prompt_argument", "value": float(exact_prompt), "type": "Reward"},
            {"name": "has_prompt_argument", "value": float(has_prompt), "type": "Metric"},
            {"name": "concise", "value": float(concise), "type": "Metric"},
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
