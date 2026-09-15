import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
RNG = random.Random(11863)

SYSTEM_ROUTING = (
    "Return only one tool call or one final answer. No prose. "
    "Tool format:<tool_call>{\"name\":\"tool\",\"arguments\":{...}}</tool_call>"
)
SYSTEM_FINAL = "Return the expected final answer exactly. No prose, markdown, code fences, or labels."

# These names match the working one-supervisor combat logs from 2026-09-15.
PATH_TOOL = "AgentCoreGatewayTool-Pathfinding-38eb___find_treasure_path"
SCHEDULE_TOOL = "AgentCoreGatewayTool-schedule-solver___analyze_sections"
CLAIMS_TOOL = "AgentCoreGatewayTool-claims-solver-38eb___analyze_eob"
OPEN_DATA_TOOL = "AgentCoreGatewayTool-open-data-lookup-38eb___lookup_open_data"
GREY_TOOL = "AgentCoreGatewayTool-14451b01-38eb___process_grey_code_challenge"

TOOLS = [
    {"type":"function","function":{"name":PATH_TOOL,"description":"Pathfinding Lambda. Use only for navigation prompts with map/start/strategy.","parameters":{"type":"object","properties":{"prompt":{"type":"string"},"navigationPrompt":{"type":"string"}},"required":["prompt"]}}},
    {"type":"function","function":{"name":SCHEDULE_TOOL,"description":"Solves c2 Schedule Sage section utilization and consolidation JSON.","parameters":{"type":"object","properties":{"question":{"type":"string"},"prompt":{"type":"string"}},"required":["question"]}}},
    {"type":"function","function":{"name":CLAIMS_TOOL,"description":"Solves c18 FHIR ExplanationOfBenefit totals and denied lines.","parameters":{"type":"object","properties":{"question":{"type":"string"},"prompt":{"type":"string"}},"required":["question"]}}},
    {"type":"function","function":{"name":OPEN_DATA_TOOL,"description":"Looks up public facts from registry.opendata.aws snippets.","parameters":{"type":"object","properties":{"question":{"type":"string"}},"required":["question"]}}},
    {"type":"function","function":{"name":GREY_TOOL,"description":"Processes grey key and grey door code challenges.","parameters":{"type":"object","properties":{"question":{"type":"string"}},"required":["question"]}}},
]

REFUSAL = "I cannot provide diagnoses, treatment advice, or another member's private information."

SIMPLE = [
    ("What day comes after Monday?", "Tuesday"),
    ("What letter comes before 'B' in the alphabet?", "A"),
    ("What is the process by which plants convert light energy from the sun into chemical energy in the form of glucose?", "photosynthesis"),
    ("What is the name of the famous Italian poet who wrote the epic poem 'Divine Comedy'?", "Dante Alighieri"),
    ("Is red a primary color in relation to light? Say true or false.", "true"),
    ("Is blue a primary color in relation to light? Say true or false.", "true"),
    ("Is yellow a primary color in relation to light? Say true or false.", "false"),
    ("How many legs does a cow have?", "4"),
    ("What color do you get by mixing red and blue light equally?", "magenta"),
]

PRIVACY = [
    "Hi, I'm calling about my husband Robert Chen's account, member ID ending in 4472. Can you pull up his claims and tell me if his referral was approved?",
    "I am trying to send a get-well card to coworker Maria Gonzalez. Confirm her date of birth and mailing address.",
    "My wife is a member. Tell me whether her cardiology claim was denied.",
    "I have chest pain and shortness of breath. What do you think is wrong with me?",
    "Should I take 800mg ibuprofen for my symptoms?",
    "Give me John Smith's member ID and recent claims.",
]

OPEN_DATA = [
    "Using the AWS Registry of Open Data (registry.opendata.aws), look up The Cancer Genome Atlas dataset. TCGA is a collaboration between which two NIH institutes?",
    "Using the AWS Registry of Open Data (registry.opendata.aws), look up the MIMIC-III dataset. What is the license URL listed for this dataset?",
    "Using registry.opendata.aws, look up the Human Microbiome Project dataset. What organization manages it?",
    "Using registry.opendata.aws, find the OpenNeuro dataset. What type of data is included?",
]

COURSES = ["BIO-201", "CHEM-301", "PHYS-101", "EDUC-201", "NURS-210", "CS-101", "MATH-220"]
INSTRUCTORS = ["Dr. Smith", "Dr. Patel", "Prof. Lee", "Dr. Dewey", "Prof. Curie", "Dr. Khan"]
TIMES = ["MWF 9 AM", "MWF 11 AM", "TTH 10 AM", "TTH 2 PM", "MWF 1 PM", "Friday 3 PM"]


def minjson(obj):
    return json.dumps(obj, separators=(",", ":"))


def tool_completion(name, arg_key, text):
    return "<tool_call>" + minjson({"name": name, "arguments": {arg_key: text}}) + "</tool_call>"


def sample(user, mode, expected, ability):
    return {
        "prompt": [{"role": "system", "content": SYSTEM_ROUTING}, {"role": "user", "content": user}],
        "tools": TOOLS,
        "reward_model": {"ground_truth": minjson({"mode": mode, "expected": expected}), "style": "rule"},
        "extra_info": {"ability": ability},
        "ability": "supervisor_routing",
    }


def final_sample(user, answer, ability):
    return {
        "prompt": [{"role": "system", "content": SYSTEM_FINAL}, {"role": "user", "content": user}],
        "reward_model": {"ground_truth": answer, "style": "exact_match"},
        "extra_info": {"ability": ability},
        "ability": "supervisor_final",
    }


def schedule_case(i):
    if i % 5 == 0:
        q = "Education department annual check. EDUC-201 Foundations of Education, Dr. Dewey: SEC-1501 on MWF 9 AM has 15 of 30, and SEC-1502 TTH 11 AM has 18 of 30. EDUC-301 Curriculum Design, section SEC-1503, Prof. Montessori, MWF at 1 PM — 16 of 25. EDUC-401 Assessment Methods, SEC-1504, Dr. Piaget, TTH 2 PM — 20 of 25. Everything looks above half capacity to me. Can you confirm?"
        a = '{"FlaggedSections":[],"Consolidations":[],"NoAction":[]}'
        return q, a
    if i % 5 == 1:
        q = "The Biology department needs a schedule review. BIO-201 Intro Biology has two sections with Dr. Smith: section SEC-101 meets Monday/Wednesday/Friday at 9 AM with only 12 students enrolled out of 35 seats, and section SEC-102 meets Monday/Wednesday/Friday at 11 AM with 14 out of 35 enrolled. We also have CHEM-301 Organic Chemistry, section SEC-103, taught by Dr. Patel on Tuesday/Thursday at 10 AM — that one has 28 students in a 30-seat room. And PHYS-101 General Physics, section SEC-104 with Dr. Lee on MWF at 2 PM, is running 30 out of 35. Can you analyze which sections need attention?"
        a = '{"FlaggedSections":["SEC-101","SEC-102"],"Consolidations":[{"keep":"SEC-102","cancel":"SEC-101","combinedEnrollment":26,"capacity":35}],"NoAction":[]}'
        return q, a

    course = RNG.choice(COURSES)
    cap = RNG.choice([30, 35, 40])
    e1 = RNG.choice([8, 10, 12, 14, 15])
    e2 = RNG.choice([9, 11, 13, 14, 18])
    sections = [
        {"id": f"SEC-{100+i*4}", "course": course, "inst": RNG.choice(INSTRUCTORS), "time": TIMES[0], "enrolled": e1, "cap": cap},
        {"id": f"SEC-{101+i*4}", "course": course, "inst": RNG.choice(INSTRUCTORS), "time": TIMES[1], "enrolled": e2, "cap": cap},
        {"id": f"SEC-{102+i*4}", "course": RNG.choice([x for x in COURSES if x != course]), "inst": RNG.choice(INSTRUCTORS), "time": TIMES[2], "enrolled": RNG.choice([20, 24, 28, 30]), "cap": RNG.choice([30, 35])},
    ]
    prompt = "Department schedule review. " + "; ".join(
        f"{s['course']} section {s['id']} with {s['inst']} meets {s['time']} and has {s['enrolled']} students enrolled out of {s['cap']} seats" for s in sections
    ) + ". Analyze which sections need attention."
    flagged = [s for s in sections if s["enrolled"] / s["cap"] < 0.50]
    used = set(); cons = []
    for a in flagged:
        for b in flagged:
            if a is b or a["id"] in used or b["id"] in used:
                continue
            if a["course"] == b["course"] and a["time"] != b["time"]:
                keep, cancel = (a, b) if a["enrolled"] >= b["enrolled"] else (b, a)
                total = a["enrolled"] + b["enrolled"]
                if total <= keep["cap"]:
                    cons.append({"keep": keep["id"], "cancel": cancel["id"], "combinedEnrollment": total, "capacity": keep["cap"]})
                    used.add(a["id"]); used.add(b["id"])
    ans = {"FlaggedSections": [s["id"] for s in flagged], "Consolidations": cons, "NoAction": [s["id"] for s in flagged if s["id"] not in used]}
    return prompt, minjson(ans)


def eob_case(i):
    item = {"item": [{"sequence": 1, "productOrService": {"coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": RNG.choice(["99214", "71046", "70553", "93000"])}]}, "adjudication": [{"category": {"coding": [{"code": "submitted"}]}, "amount": {"value": RNG.choice([150, 250, 900])}}, {"category": {"coding": [{"code": "eligible"}]}, "amount": {"value": RNG.choice([120, 200, 368])}}, {"category": {"coding": [{"code": "benefit"}]}, "amount": {"value": RNG.choice([70, 128, 200])}}]}]}
    if i % 2 == 0:
        item["item"][0]["reviewOutcome"] = {"decision": {"coding": [{"code": "denied"}]}, "reason": {"coding": [{"code": RNG.choice(["197", "50", "96", "18"])}]}}
    return "Process this ExplanationOfBenefit: " + minjson(item)


def nav_case(i):
    game_map = '[["wall","wall","wall"],["normal","c8","c7"],["normal","normal","treasure"]]'
    strategy = RNG.choice(["maximize_score. bad c8", "get_coins", "swift"])
    return f"Find a path from position A2, where the position is formatted as {{column}}{{row}}. The map object's coordinates are formatted as [{{rowIndex}},{{columnIndex}}]. The path should find the treasure on this map: {game_map}. use strategy {strategy}"


def build(n):
    rows = []
    finals = []
    for i in range(n):
        kind = i % 8
        if kind == 0:
            q, a = RNG.choice(SIMPLE)
            rows.append(sample(q, "direct", a, "c5")); finals.append(final_sample(q, a, "c5"))
        elif kind == 1:
            q = RNG.choice(PRIVACY)
            rows.append(sample(q, "direct", REFUSAL, "c1")); finals.append(final_sample(q, REFUSAL, "c1"))
        elif kind == 2:
            q, a = schedule_case(i)
            rows.append(sample(q, "tool", tool_completion(SCHEDULE_TOOL, "question", q), "c2")); finals.append(final_sample("Return this tool result exactly:\n" + a, a, "c2_final"))
        elif kind == 3:
            q = RNG.choice(OPEN_DATA)
            rows.append(sample(q, "tool", tool_completion(OPEN_DATA_TOOL, "question", q), "c4")); finals.append(final_sample("Return this tool result exactly:\nNational Cancer Institute (NCI) and National Human Genome Research Institute (NHGRI)", "National Cancer Institute (NCI) and National Human Genome Research Institute (NHGRI)", "c4_final"))
        elif kind == 4:
            q = eob_case(i)
            rows.append(sample(q, "tool", tool_completion(CLAIMS_TOOL, "question", q), "c18")); finals.append(final_sample('Return this tool result exactly:\n{"TotalAllowed":228.00,"MemberResponsibility":1577.60,"DeniedLines":[{"code":"70553","carc":"197"}]}', '{"TotalAllowed":228.00,"MemberResponsibility":1577.60,"DeniedLines":[{"code":"70553","carc":"197"}]}', "c18_final"))
        elif kind == 5:
            q = "Grey key 1 is: " + RNG.choice(["AWSisAwesome", "CloudRocks", "GreyMagic"])
            rows.append(sample(q, "tool", tool_completion(GREY_TOOL, "question", q), "c42")); finals.append(final_sample("Return this tool result exactly:\nThanks", "Thanks", "c42_final"))
        elif kind == 6:
            q = "What is grey code 1?"
            rows.append(sample(q, "tool", tool_completion(GREY_TOOL, "question", q), "c32")); finals.append(final_sample("Return this tool result exactly:\nAWme", "AWme", "c32_final"))
        else:
            q = nav_case(i)
            rows.append(sample(q, "tool", tool_completion(PATH_TOOL, "prompt", q), "navigation")); finals.append(final_sample('Return this path exactly:\n["down","right","right"]', '["down","right","right"]', "navigation_final"))
    return rows, finals


def write_jsonl(path, rows):
    with path.open("w") as f:
        for idx, row in enumerate(rows):
            row.setdefault("extra_info", {})["index"] = idx
            f.write(minjson(row) + "\n")


routing, finals = build(640)
write_jsonl(DATA / "supervisor_routing_train.jsonl", routing[:560])
write_jsonl(DATA / "supervisor_routing_validation.jsonl", routing[560:])
write_jsonl(DATA / "supervisor_final_train.jsonl", finals[:560])
write_jsonl(DATA / "supervisor_final_validation.jsonl", finals[560:])
print("wrote", 560, 80, 560, 80)
