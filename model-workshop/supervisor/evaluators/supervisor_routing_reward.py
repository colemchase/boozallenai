import json, re
from typing import Any, Dict


def _loads(x: Any):
    if isinstance(x, (dict, list)):
        return x
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            return None
    return None


def _response(sample: Dict[str, Any]) -> str:
    for k in ("completion", "response", "answer", "model_output"):
        v = sample.get(k)
        if isinstance(v, str):
            return v.strip()
    for msg in sample.get("messages", []) or sample.get("prompt", []) or []:
        if msg.get("role") == "assistant":
            return (msg.get("content") or "").strip()
    return ""


def _truth(sample: Dict[str, Any]) -> Dict[str, Any]:
    rm = sample.get("reward_model", {}) or {}
    gt = rm.get("ground_truth") or sample.get("ground_truth") or ""
    parsed = _loads(gt)
    return parsed if isinstance(parsed, dict) else {}


def _tool_call(text: str) -> Dict[str, Any]:
    m = re.search(r"<tool_call>\s*(\{[\s\S]*?\})\s*</tool_call>", text or "")
    raw = m.group(1) if m else (text or "").strip()
    parsed = _loads(raw)
    return parsed if isinstance(parsed, dict) else {}


def _norm_tool(text: str) -> Dict[str, Any]:
    call = _tool_call(text)
    args = call.get("arguments") or (call.get("function") or {}).get("arguments") or {}
    if isinstance(args, str):
        args = _loads(args) or {}
    return {"name": call.get("name") or (call.get("function") or {}).get("name"), "arguments": args if isinstance(args, dict) else {}}


def reward_function(sample: Dict[str, Any], index: int) -> Dict[str, Any]:
    resp = _response(sample)
    gt = _truth(sample)
    mode = gt.get("mode")
    expected = (gt.get("expected") or "").strip()

    if mode == "tool":
        actual_tool = _norm_tool(resp)
        expected_tool = _norm_tool(expected)
        valid = 1.0 if actual_tool.get("name") else 0.0
        correct_name = 1.0 if actual_tool.get("name") == expected_tool.get("name") else 0.0
        correct_args = 1.0 if actual_tool.get("arguments") == expected_tool.get("arguments") else 0.0
        concise = 1.0 if resp.startswith("<tool_call>") and resp.endswith("</tool_call>") and len(resp) < len(expected) + 30 else 0.0
        aggregate = 0.15 * valid + 0.35 * correct_name + 0.40 * correct_args + 0.10 * concise
        metrics = [
            {"name":"valid_tool_call","value":valid,"type":"Metric"},
            {"name":"correct_tool_name","value":correct_name,"type":"Reward"},
            {"name":"correct_arguments","value":correct_args,"type":"Reward"},
            {"name":"tool_concise","value":concise,"type":"Metric"},
        ]
    else:
        exact = 1.0 if resp == expected else 0.0
        no_md = 1.0 if "```" not in resp and not resp.lower().startswith(("here", "the answer", "answer:", "let ")) else 0.0
        # Give exact answers full credit. Partial credit allows embedded correct answers but penalizes narration.
        contains = 1.0 if expected and expected in resp else 0.0
        aggregate = 1.0 if exact else (0.75 * contains + 0.25 * no_md)
        metrics = [
            {"name":"exact_answer","value":exact,"type":"Reward"},
            {"name":"contains_expected","value":contains,"type":"Metric"},
            {"name":"no_markdown_or_preamble","value":no_md,"type":"Metric"},
        ]
    return {"id": str(sample.get("id", sample.get("extra_info", {}).get("index", f"sample-{index:03d}"))), "aggregate_reward_score": float(max(0.0, min(1.0, aggregate))), "metrics_list": metrics}


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
