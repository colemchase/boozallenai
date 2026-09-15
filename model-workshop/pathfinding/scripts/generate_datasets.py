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

TOOL_NAME = "pathfinding_lambda"
SYSTEM_TOOL = """Output ONLY a tool call for pathfinding. Use this exact format:\n<tool_call>\n{\"name\":\"pathfinding_lambda\",\"arguments\":{\"prompt\":<full_navigation_prompt>}}\n</tool_call>"""
SYSTEM_FAITH = "Return the tool output path array exactly. Output only the JSON array of directions, no prose."

BASE_MAP = [["wall","wall","wall","wall","wall","wall","wall","wall","wall","wall"],["wall","c18","normal","normal","c8","c7","c7","c7","c7","wall"],["wall","wall","wall","c32","wall","wall","wall","wall","wall","wall"],["normal","wall","c4","normal","normal","normal","c5","normal","normal","c2"],["normal","wall","wall","wall","wall","wall","wall","wall","wall","normal"],["c5","normal","normal","normal","c5","normal","normal","normal","c1","normal"],["wall","wall","wall","wall","wall","wall","wall","wall","wall","c4"],["normal","c5","c7","c7","c8","c42","c5","normal","normal","normal"],["c2","wall","wall","wall","wall","wall","wall","wall","c18","normal"],["normal","normal","normal","normal","c1","normal","normal","normal","normal","treasure"]]

SMALL_MAPS = [
    [["start","wall","treasure"],["normal","normal","normal"]],
    [["start","normal","treasure"],["c7","wall","wall"]],
    [["start","c42","c32","treasure"]],
    [["start","c7","treasure"],["normal","c2","normal"]],
    [["start","c8","treasure"],["normal","normal","normal"]],
]


def pos_name(row, col):
    return chr(ord('A') + col) + str(row + 1)


def prompt_for(game_map, start=(0,0), strategy="maximize_score", bad=()):
    suffix = f"use strategy {strategy}"
    for b in bad:
        suffix += f". bad {b}"
    return (
        f"Find a path from position {pos_name(*start)}, where the position is formatted as {{column}}{{row}}. "
        f"The map object's coordinates are formatted as [{{rowIndex}},{{columnIndex}}]. "
        f"The path should find the treasure on this map: {json.dumps(game_map,separators=(',',':'))}. {suffix}"
    )


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
            "description": "Pathfinding Lambda. Parses a full AI League navigation prompt and returns a path array.",
            "parameters": {
                "type": "object",
                "properties": {"prompt": {"type": "string", "description": "Full navigation prompt including map, start position, strategy, and bad/block tile hints."}},
                "required": ["prompt"]
            }
        }
    }]


def tool_sample(prompt, path, idx, split):
    args = {"prompt": prompt}
    gt = {"function": {"name": TOOL_NAME, "arguments": json.dumps(args, separators=(",", ":"))}, "output": {"path": path}}
    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_TOOL},
            {"role": "user", "content": prompt},
        ],
        "tools": tool_schema(),
        "reward_model": {"ground_truth": json.dumps(gt, separators=(",", ":")), "style": "rule"},
        "extra_info": {"index": idx, "split": split, "tool": TOOL_NAME, "steps": len(path)},
        "ability": "tool_use",
    }


def faith_sample(path, idx, split):
    tool_output = {"path": path, "steps": len(path)}
    return {
        "data_source": "pathfinding_faithfulness",
        "prompt": [
            {"role": "system", "content": SYSTEM_FAITH},
            {"role": "user", "content": "Return this tool output exactly:\n" + json.dumps(tool_output, separators=(",", ":"))},
        ],
        "ability": "tool_output_faithfulness",
        "reward_model": {"ground_truth": json.dumps(path, separators=(",", ":")), "style": "exact_match"},
        "extra_info": {"index": idx, "split": split, "steps": len(path)},
    }


def mutate_map(rng):
    # Keep the successful game layout as most samples; small maps add variety without risking invalid random mazes.
    if rng.random() < 0.70:
        return BASE_MAP, (3,0), rng.choice(["maximize_score", "get_coins", "swift"]), rng.choice([("c8",), ("c8","c18"), ()])
    m = rng.choice(SMALL_MAPS)
    return m, (0,0), rng.choice(["maximize_score", "get_coins", "swift"]), rng.choice([(), ("c8",)])


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows))


def main():
    rng = random.Random(42)
    tool_train=[]; tool_val=[]; faith_train=[]; faith_val=[]
    for split, count, tool_rows, faith_rows in [("train",500,tool_train,faith_train),("val",100,tool_val,faith_val)]:
        for i in range(count):
            game_map, start, strategy, bad = mutate_map(rng)
            prompt = prompt_for(game_map, start, strategy, bad)
            path = call_lambda(prompt)
            tool_rows.append(tool_sample(prompt, path, i, split))
            faith_rows.append(faith_sample(path, i, split))
    OUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT / "tool_calling_train.jsonl", tool_train)
    write_jsonl(OUT / "tool_calling_validation.jsonl", tool_val)
    write_jsonl(OUT / "faithfulness_train.jsonl", faith_train[:403])
    write_jsonl(OUT / "faithfulness_validation.jsonl", faith_val[:81])
    print("wrote", OUT)
    for f in sorted(OUT.glob('*.jsonl')):
        print(f.name, sum(1 for _ in f.open()), f.stat().st_size)

if __name__ == "__main__":
    main()
