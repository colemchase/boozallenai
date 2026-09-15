#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAMBDA_PATH = ROOT / "lambdas/pathfinding/pathfinding_lambda.py"
OUT = ROOT / "model-workshop/pathfinding/data"

spec = importlib.util.spec_from_file_location("pathfinding_lambda", LAMBDA_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# This must match the actual Pathfinding tool exposed in the working combat logs.
TOOL_NAME = "AgentCoreGatewayTool-Pathfinding-38eb___find_treasure_path"
SYSTEM_TOOL = (
    "Output ONLY this tool call for navigation. No prose. "
    "Use a compact prompt preserving start position, full map JSON, strategy, and bad/block hints. "
    "<tool_call>{\"name\":\"" + TOOL_NAME + "\",\"arguments\":{\"prompt\":<compact_lambda_prompt>}}</tool_call>"
)
SYSTEM_FAITH = "Return only the path JSON array exactly. No prose, markdown, labels, or code fences."

BASE_MAP = [["wall","wall","wall","wall","wall","wall","wall","wall","wall","wall"],["wall","c18","normal","normal","c8","c7","c7","c7","c7","wall"],["wall","wall","wall","c32","wall","wall","wall","wall","wall","wall"],["normal","wall","c4","normal","normal","normal","c5","normal","normal","c2"],["normal","wall","wall","wall","wall","wall","wall","wall","wall","normal"],["c5","normal","normal","normal","c5","normal","normal","normal","c1","normal"],["wall","wall","wall","wall","wall","wall","wall","wall","wall","c4"],["normal","c5","c7","c7","c8","c42","c5","normal","normal","normal"],["c2","wall","wall","wall","wall","wall","wall","wall","c18","normal"],["normal","normal","normal","normal","c1","normal","normal","normal","normal","treasure"]]

SMALL_MAPS = [
    [["start","wall","treasure"],["normal","normal","normal"]],
    [["start","normal","treasure"],["c7","wall","wall"]],
    [["start","c42","c32","treasure"]],
    [["start","c7","treasure"],["normal","c2","normal"]],
    [["start","c8","treasure"],["normal","normal","normal"]],
    [["normal","c7","treasure"],["normal","wall","normal"],["start","normal","c8"]],
]

STRATEGY_TEXTS = [
    "use strategy maximize_score. bad c8.",
    "use strategy maximize_score. bad c8",
    "use strategy maximize_score and bad c8",
    "use strategy maximize_score. avoid c8",
    "use strategy maximize_score. block c8",
    "use strategy get_coins",
    "use strategy swift",
]


def minjson(obj):
    return json.dumps(obj, separators=(",", ":"))


def pos_name(row, col):
    return chr(ord("A") + col) + str(row + 1)


def prompt_for(game_map, start=(0, 0), strategy_text="use strategy maximize_score. bad c8.", verbose=True):
    grid = minjson(game_map)
    if verbose:
        return (
            f"Find a path from position {pos_name(*start)}, where the position is formatted as {{column}}{{row}}. "
            f"{{column}} is a letter starting with A, and {{row}} is a number starting with 1. "
            f"The map object's coordinates are formatted as [{{rowIndex}},{{columnIndex}}], where {{rowIndex}} is the row number starting with 0, and {{columnIndex}} is the column number starting with 0. "
            f"The path should find the treasure on this map: {grid}. {strategy_text}"
        )
    return f"Find a path from position {pos_name(*start)}. The path should find the treasure on this map: {grid}. {strategy_text}"


def lambda_prompt_for(game_map, start=(0, 0), strategy_text="use strategy maximize_score. bad c8."):
    # The model sees the full game prompt, but it only needs to send the Lambda
    # the parts the Lambda parses: start position, map JSON, and strategy/hints.
    return f"Find a path from position {pos_name(*start)}. Map: {minjson(game_map)}. {strategy_text}"


_PATH_CACHE = {}


def call_lambda(prompt):
    if prompt in _PATH_CACHE:
        return _PATH_CACHE[prompt]
    with contextlib.redirect_stdout(io.StringIO()):
        res = mod.lambda_handler({"prompt": prompt}, None)
    body = json.loads(res["body"])
    path = body.get("path", [])
    _PATH_CACHE[prompt] = path
    return path


def tool_schema():
    return [{
        "type": "function",
        "function": {
            "name": TOOL_NAME,
            "description": "Pathfinding Gateway tool. Pass the complete raw AI League navigation prompt. It returns a path array.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Full raw navigation prompt including map, start position, strategy, and bad/block hints."}
                },
                "required": ["prompt"],
            },
        },
    }]


def tool_sample(user_prompt, lambda_prompt, path, idx, split):
    args = {"prompt": lambda_prompt}
    gt = {"function": {"name": TOOL_NAME, "arguments": minjson(args)}, "output": {"path": path}}
    return {
        "prompt": [{"role": "system", "content": SYSTEM_TOOL}, {"role": "user", "content": user_prompt}],
        "tools": tool_schema(),
        "reward_model": {"ground_truth": minjson(gt), "style": "rule"},
        "extra_info": {"index": idx, "split": split, "tool": TOOL_NAME, "steps": len(path)},
        "ability": "tool_use",
    }


def faith_sample(path, idx, split):
    tool_output = {"path": path, "steps": len(path)}
    return {
        "data_source": "pathfinding_faithfulness",
        "prompt": [
            {"role": "system", "content": SYSTEM_FAITH},
            {"role": "user", "content": "Return this tool output exactly:\n" + minjson(tool_output)},
        ],
        "ability": "tool_output_faithfulness",
        "reward_model": {"ground_truth": minjson(path), "style": "exact_match"},
        "extra_info": {"index": idx, "split": split, "steps": len(path)},
    }


def case_for(rng, i):
    # Heavy bias toward the real leaderboard/local map and exact winning navigation prompt.
    roll = rng.random()
    if roll < 0.72:
        return BASE_MAP, (3, 0), rng.choice(STRATEGY_TEXTS[:4]), True
    if roll < 0.85:
        return BASE_MAP, (3, 0), rng.choice(STRATEGY_TEXTS), rng.choice([True, False])
    m = rng.choice(SMALL_MAPS)
    return m, (0, 0), rng.choice(STRATEGY_TEXTS), rng.choice([True, False])


def write_jsonl(path, rows):
    path.write_text("".join(minjson(r) + "\n" for r in rows))


def main():
    rng = random.Random(11823)
    tool_train = []
    tool_val = []
    faith_train = []
    faith_val = []
    for split, count, tool_rows, faith_rows in [("train", 700, tool_train, faith_train), ("val", 140, tool_val, faith_val)]:
        for i in range(count):
            game_map, start, strategy_text, verbose = case_for(rng, i)
            user_prompt = prompt_for(game_map, start, strategy_text, verbose)
            lambda_prompt = lambda_prompt_for(game_map, start, strategy_text)
            path = call_lambda(lambda_prompt)
            tool_rows.append(tool_sample(user_prompt, lambda_prompt, path, i, split))
            faith_rows.append(faith_sample(path, i, split))
    OUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT / "tool_calling_train.jsonl", tool_train)
    write_jsonl(OUT / "tool_calling_validation.jsonl", tool_val)
    write_jsonl(OUT / "faithfulness_train.jsonl", faith_train[:560])
    write_jsonl(OUT / "faithfulness_validation.jsonl", faith_val[:112])
    print("wrote", OUT)
    for f in sorted(OUT.glob("*.jsonl")):
        print(f.name, sum(1 for _ in f.open()), f.stat().st_size)


if __name__ == "__main__":
    main()
