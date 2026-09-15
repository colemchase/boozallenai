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
            return val.strip()
    for msg in sample.get("messages", []) or sample.get("prompt", []) or []:
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            return (msg.get("content") or "").strip()
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


def _expected_prompt(gt: Dict[str, Any]) -> str:
    args = _norm_args((gt.get("function") or {}).get("arguments"))
    return str(args.get("prompt") or args.get("navigationPrompt") or "")


def _actual_prompt(call: Dict[str, Any]) -> str:
    args = _norm_args(call.get("arguments") or (call.get("function") or {}).get("arguments"))
    return str(args.get("prompt") or args.get("navigationPrompt") or "")


def _grid_text(text: str) -> str:
    start = text.find("[[")
    if start < 0:
        return ""
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return ""


def _grid_equal_or_present(actual: str, expected: str) -> float:
    exp_grid = _grid_text(expected)
    act_grid = _grid_text(actual)
    if not exp_grid:
        return 1.0
    if not act_grid:
        return 0.0
    try:
        return 1.0 if json.loads(act_grid) == json.loads(exp_grid) else 0.0
    except Exception:
        # Whitespace-insensitive textual fallback.
        compact_exp = re.sub(r"\s+", "", exp_grid)
        compact_act = re.sub(r"\s+", "", act_grid)
        return 1.0 if compact_exp == compact_act else 0.0


def _start_pos(text: str) -> str:
    m = re.search(r"\bposition\s+([A-Za-z]\d+)\b", text, re.I)
    return m.group(1).upper() if m else ""


def _strategy(text: str) -> str:
    raw = text.lower()
    m = re.search(r"use\s+strategy\s+([a-z0-9_-]+)", raw, re.I)
    if m:
        return m.group(1).lower()
    if "maximize" in raw or "max score" in raw:
        return "maximize_score"
    if "get_coins" in raw or "coins" in raw:
        return "get_coins"
    if "swift" in raw:
        return "swift"
    return ""


def _hint_cells(text: str):
    raw = text.lower()
    cells = set()
    for clause in re.split(r"[.;,]|\band\b", raw):
        if re.search(r"\b(?:bad|avoid|block|blocked|forbid|never|danger|trap|spike)\b", clause):
            cells.update(re.findall(r"\bc\d+\b", clause))
    return cells


def _has_path_array(text: str) -> float:
    # Penalize responses that skip the tool and output a route directly.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
            return 1.0
    except Exception:
        pass
    # Also catch prose containing a direction array outside a tool call.
    cleaned = re.sub(r"<tool_call>[\s\S]*?</tool_call>", "", text)
    return 1.0 if re.search(r"\[\s*\"(?:up|down|left|right)\"", cleaned) else 0.0


def reward_function(sample: Dict[str, Any], index: int) -> Dict[str, Any]:
    response = _assistant_response(sample)
    gt = _ground_truth(sample)
    call = _extract_tool_call(response)

    expected_fn = (gt.get("function") or {}).get("name") or "pathfinding_lambda"
    actual_name = call.get("name") or (call.get("function") or {}).get("name")
    expected_prompt = _expected_prompt(gt)
    actual_prompt = _actual_prompt(call)

    valid_json = 1.0 if call else 0.0
    correct_tool = 1.0 if actual_name == expected_fn else 0.0
    has_prompt = 1.0 if len(actual_prompt) > 20 else 0.0
    grid_ok = _grid_equal_or_present(actual_prompt, expected_prompt)
    start_ok = 1.0 if _start_pos(expected_prompt) and _start_pos(actual_prompt) == _start_pos(expected_prompt) else 0.0
    strategy_ok = 1.0 if _strategy(expected_prompt) and _strategy(actual_prompt) == _strategy(expected_prompt) else 0.0
    expected_hints = _hint_cells(expected_prompt)
    actual_hints = _hint_cells(actual_prompt)
    hints_ok = 1.0 if expected_hints.issubset(actual_hints) else 0.0
    no_direct_path = 1.0 - _has_path_array(response)
    concise = 1.0 if len(response) < max(1200, len(expected_prompt) + 350) else 0.0

    # Component scoring: preserve the critical data for the Lambda instead of exact-copying every word.
    aggregate = (
        0.10 * valid_json +
        0.20 * correct_tool +
        0.10 * has_prompt +
        0.25 * grid_ok +
        0.10 * start_ok +
        0.10 * strategy_ok +
        0.05 * hints_ok +
        0.05 * no_direct_path +
        0.05 * concise
    )

    return {
        "id": str(sample.get("id", sample.get("extra_info", {}).get("index", f"sample-{index:03d}"))),
        "aggregate_reward_score": float(max(0.0, min(1.0, aggregate))),
        "metrics_list": [
            {"name": "valid_tool_call_json", "value": float(valid_json), "type": "Metric"},
            {"name": "correct_tool", "value": float(correct_tool), "type": "Reward"},
            {"name": "has_prompt_argument", "value": float(has_prompt), "type": "Metric"},
            {"name": "grid_preserved", "value": float(grid_ok), "type": "Reward"},
            {"name": "start_preserved", "value": float(start_ok), "type": "Reward"},
            {"name": "strategy_preserved", "value": float(strategy_ok), "type": "Reward"},
            {"name": "hints_preserved", "value": float(hints_ok), "type": "Metric"},
            {"name": "no_direct_path", "value": float(no_direct_path), "type": "Reward"},
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
