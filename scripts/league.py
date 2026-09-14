#!/usr/bin/env python3
"""Small AWS CLI-backed deploy/test workflow; Python standard library only."""
import argparse
import contextlib
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
ACCOUNT = "311141566489"


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def aws(args, *command):
    # Explicit profile, and remove inherited credentials that could select another account.
    env = dict(os.environ)
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_SECURITY_TOKEN"):
        env.pop(key, None)
    result = subprocess.run(
        ["aws", *command, "--profile", args.profile, "--region", "us-east-1", "--no-cli-pager", "--output", "json"],
        capture_output=True, text=True, env=env,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout) if result.stdout.strip() else {}


def identity(args):
    account = aws(args, "sts", "get-caller-identity")["Account"]
    if account != ACCOUNT:
        raise RuntimeError(f"Expected workshop account {ACCOUNT}; got {account}. No changes made.")


def check_response(response, case):
    if response.get("statusCode") != case.get("status", 200):
        raise AssertionError(f"{case['name']}: unexpected status: {response}")
    body = json.loads(response["body"])
    if body != case["expected"]:
        raise AssertionError(f"{case['name']}: expected {case['expected']}, got {body}")


def local_tests():
    spec = importlib.util.spec_from_file_location("pathfinding", ROOT / "src/pathfinding/handler.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for case in read(ROOT / "tests/fixtures/pathfinding.json"):
        with contextlib.redirect_stdout(io.StringIO()):
            result = module.lambda_handler(case["event"], None)
        check_response(result, case)
        print(f"PASS local {case['name']}", flush=True)


def build():
    local_tests()
    template = read(ROOT / "infra/stack.json")
    template["Resources"]["Pathfinding"]["Properties"]["Code"]["ZipFile"] = (ROOT / "src/pathfinding/handler.py").read_text()
    path = LOCAL / "build/stack.json"
    write(path, template)
    if path.stat().st_size > 51200:
        raise RuntimeError("Template exceeds direct CloudFormation limit; use S3 packaging before deploying.")
    print(f"Built {path}", flush=True)
    return path


def outputs(args):
    stack = aws(args, "cloudformation", "describe-stacks", "--stack-name", args.stack)["Stacks"][0]
    if stack["StackStatus"] not in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
        raise RuntimeError(f"Stack not successfully deployed: {stack['StackStatus']}")
    return {item["OutputKey"]: item["OutputValue"] for item in stack.get("Outputs", [])}


def deploy(args):
    path = build()
    identity(args)
    aws(args, "cloudformation", "validate-template", "--template-body", f"file://{path}")
    print(f"Deploying {args.stack} in {ACCOUNT}/us-east-1; waiting for CloudFormation...", flush=True)
    # The deploy command emits human-readable text even with --output json.
    env = dict(os.environ)
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_SECURITY_TOKEN"):
        env.pop(key, None)
    subprocess.run([
        "aws", "cloudformation", "deploy", "--stack-name", args.stack,
        "--template-file", str(path), "--capabilities", "CAPABILITY_IAM",
        "--no-fail-on-empty-changeset", "--profile", args.profile,
        "--region", "us-east-1", "--no-cli-pager",
    ], env=env, check=True)
    result = outputs(args)
    write(LOCAL / "outputs.json", result)
    print(json.dumps(result, indent=2))


def smoke(args):
    identity(args)
    resources = outputs(args)
    run = LOCAL / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    results = []

    def check(name, fn):
        try:
            fn()
            results.append({"test": name, "status": "PASS"})
            print(f"PASS {name}", flush=True)
        except (RuntimeError, AssertionError, KeyError, ValueError) as exc:
            results.append({"test": name, "status": "FAIL", "error": str(exc)})
            print(f"FAIL {name}: {exc}", flush=True)

    for case in read(ROOT / "tests/fixtures/pathfinding.json"):
        def invoke(case=case):
            event_file = run / f"{case['name']}-event.json"
            response_file = run / f"{case['name']}-response.json"
            write(event_file, case["event"])
            meta = aws(args, "lambda", "invoke", "--function-name", resources["FunctionName"],
                       "--payload", f"fileb://{event_file}", str(response_file))
            if meta.get("FunctionError") or meta.get("StatusCode") != 200:
                raise AssertionError(f"Lambda execution failed: {meta}")
            check_response(read(response_file), case)
        check("lambda " + case["name"], invoke)

    def memory():
        session = "cli-" + uuid.uuid4().hex
        text = "CLI memory round-trip " + session
        request = {
            "memoryId": resources["MemoryId"], "actorId": "cli-smoke-test", "sessionId": session,
            "eventTimestamp": datetime.now(timezone.utc).isoformat(),
            "payload": [{"conversational": {"content": {"text": text}, "role": "USER"}}],
        }
        path = run / "memory-event.json"
        write(path, request)
        created = aws(args, "bedrock-agentcore", "create-event", "--cli-input-json", f"file://{path}")
        event_id = created["event"]["eventId"]
        result = aws(args, "bedrock-agentcore", "get-event", "--memory-id", resources["MemoryId"],
                     "--actor-id", "cli-smoke-test", "--session-id", session, "--event-id", event_id)
        write(run / "memory-response.json", result)
        if result["event"]["payload"] != request["payload"]:
            raise AssertionError("Memory read did not match the written payload")
    check("memory write/read", memory)

    for case in read(ROOT / "tests/fixtures/guardrail.json"):
        def guardrail(case=case):
            path = run / f"{case['name']}-request.json"
            write(path, {"guardrailIdentifier": resources["GuardrailId"],
                         "guardrailVersion": resources["GuardrailVersion"], "source": case["source"],
                         "content": [{"text": {"text": case["text"]}}]})
            result = aws(args, "bedrock-runtime", "apply-guardrail", "--cli-input-json", f"file://{path}")
            write(run / f"{case['name']}-response.json", result)
            if result.get("action") != case["action"]:
                raise AssertionError(f"Expected {case['action']}, got {result.get('action')}")
        check("guardrail " + case["name"], guardrail)

    write(run / "summary.json", {"resources": resources, "results": results, "official_game_result": False})
    print(f"Results: {run / 'summary.json'}")
    return 1 if any(r["status"] == "FAIL" for r in results) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["test", "build", "deploy", "outputs", "smoke"])
    parser.add_argument("--profile", default="ai-league")
    parser.add_argument("--stack", default="ai-league-candidate", choices=["ai-league-candidate"])
    args = parser.parse_args()
    try:
        if args.command == "test":
            local_tests()
        elif args.command == "build":
            build()
        elif args.command == "deploy":
            deploy(args)
        elif args.command == "outputs":
            identity(args)
            print(json.dumps(outputs(args), indent=2))
        else:
            return smoke(args)
    except (RuntimeError, AssertionError, subprocess.CalledProcessError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
