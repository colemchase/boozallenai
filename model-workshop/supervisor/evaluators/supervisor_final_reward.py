import json, re
from typing import Any, Dict


def _response(sample: Dict[str, Any]) -> str:
    for k in ("completion", "response", "answer", "model_output"):
        v = sample.get(k)
        if isinstance(v, str):
            return v.strip()
    for msg in sample.get("messages", []) or sample.get("prompt", []) or []:
        if msg.get("role") == "assistant":
            return (msg.get("content") or "").strip()
    return ""


def _truth(sample: Dict[str, Any]) -> str:
    rm = sample.get("reward_model", {}) or {}
    return str(rm.get("ground_truth") or sample.get("ground_truth") or "").strip()


def _json_equiv(a: str, b: str) -> float:
    try:
        return 1.0 if json.loads(a) == json.loads(b) else 0.0
    except Exception:
        return 0.0


def reward_function(sample: Dict[str, Any], index: int) -> Dict[str, Any]:
    resp = _response(sample)
    expected = _truth(sample)
    exact = 1.0 if resp == expected else 0.0
    json_equiv = _json_equiv(resp, expected)
    no_fence = 1.0 if "```" not in resp else 0.0
    no_preamble = 1.0 if not re.match(r"(?i)^(i |here|the answer|answer:|let)", resp) else 0.0
    short = 1.0 if len(resp) <= len(expected) + 5 else 0.0
    aggregate = 1.0 if exact else (0.55 * json_equiv + 0.15 * no_fence + 0.15 * no_preamble + 0.15 * short)
    return {"id": str(sample.get("id", sample.get("extra_info", {}).get("index", f"sample-{index:03d}"))), "aggregate_reward_score": float(max(0.0, min(1.0, aggregate))), "metrics_list": [
        {"name":"exact_match","value":exact,"type":"Reward"},
        {"name":"json_equivalent","value":json_equiv,"type":"Metric"},
        {"name":"no_code_fence","value":no_fence,"type":"Metric"},
        {"name":"no_preamble","value":no_preamble,"type":"Metric"},
        {"name":"short_output","value":short,"type":"Metric"},
    ]}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        batch = event.get("input", event) if isinstance(event, dict) else event
        if isinstance(event, dict) and "batch" in event:
            batch = event["batch"]
        elif isinstance(event, dict) and "body" in event:
            body = json.loads(event.get("body") or "{}")
            batch = body.get("batch", [])
        if isinstance(batch, dict):
            batch = [batch]
        if not batch:
            return {"error":"Missing or empty batch"}
        results = [reward_function(s, i) for i, s in enumerate(batch)]
        return {"statusCode":200,"headers":{"Content-Type":"application/json"},"body":json.dumps(results)}
    except Exception as exc:
        return {"statusCode":400,"headers":{"Content-Type":"application/json"},"body":json.dumps({"error":str(exc)})}
