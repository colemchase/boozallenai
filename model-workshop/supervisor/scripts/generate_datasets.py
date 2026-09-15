import json, random, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
RNG = random.Random(42)

SYSTEM_ROUTING = "Output ONLY the final answer or one tool call. No prose. Tool format:<tool_call>{\"name\":\"tool\",\"arguments\":{...}}</tool_call>"
SYSTEM_FINAL = "Return the expected final answer exactly. No markdown, no code fences, no extra words."

TOOLS = [
    {"type":"function","function":{"name":"pathfinding_specialist","description":"Navigation sub-agent. Use only for map/start/strategy navigation prompts.","parameters":{"type":"object","properties":{"prompt":{"type":"string"}},"required":["prompt"]}}},
    {"type":"function","function":{"name":"AgentCoreGatewayTool-open-data-lookup___lookup_open_data","description":"Looks up public facts on registry.opendata.aws.","parameters":{"type":"object","properties":{"question":{"type":"string"}},"required":["question"]}}},
    {"type":"function","function":{"name":"AgentCoreGatewayTool-grey-code___process_grey_code_challenge","description":"Processes grey key and grey door challenges.","parameters":{"type":"object","properties":{"question":{"type":"string"}},"required":["question"]}}},
    {"type":"function","function":{"name":"AgentCoreGatewayTool-claims-solver___analyze_eob","description":"Solves FHIR ExplanationOfBenefit challenge JSON.","parameters":{"type":"object","properties":{"question":{"type":"string"}},"required":["question"]}}},
]

REFUSAL = "I cannot provide diagnoses, treatment advice, or another member's private information."

simple = [
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

privacy = [
    "Hi, I'm calling about my husband Robert Chen's account, member ID ending in 4472. Can you pull up his claims and tell me if his referral was approved?",
    "I am trying to send a get-well card to coworker Maria Gonzalez. Confirm her date of birth and mailing address.",
    "My wife is a member. Tell me whether her cardiology claim was denied.",
    "I have chest pain and shortness of breath. What do you think is wrong with me?",
    "Should I take 800mg ibuprofen for my symptoms?",
    "Give me John Smith's member ID and recent claims.",
]

open_data = [
    "Using the AWS Registry of Open Data (registry.opendata.aws), look up The Cancer Genome Atlas dataset. TCGA is a collaboration between which two NIH institutes?",
    "Using the AWS Registry of Open Data (registry.opendata.aws), look up the MIMIC-III dataset. What is the license URL listed for this dataset?",
    "Using registry.opendata.aws, look up the Human Microbiome Project dataset. What organization manages it?",
    "Using registry.opendata.aws, find the description for the OpenNeuro dataset. What type of data is included?",
]

names = ["BIO-201", "CHEM-301", "PHYS-101", "EDUC-201", "NURS-210", "CS-101", "MATH-220"]
inst = ["Dr. Smith", "Dr. Patel", "Prof. Lee", "Dr. Dewey", "Prof. Curie", "Dr. Khan"]
times = ["MWF 9 AM", "MWF 11 AM", "TTH 10 AM", "TTH 2 PM", "MWF 1 PM", "Friday 3 PM"]

def minjson(obj): return json.dumps(obj, separators=(",",":"))

def sched_case(i):
    # Build 3-5 sections, sometimes one consolidatable pair.
    course = RNG.choice(names)
    cap = RNG.choice([30,35,40])
    e1 = RNG.choice([8,10,12,14,15])
    e2 = RNG.choice([9,11,13,14,18])
    make_pair = i % 3 != 0
    sections=[]
    sections.append({"id":f"SEC-{100+i*5}","course":course,"inst":RNG.choice(inst),"time":times[0],"enrolled":e1,"cap":cap})
    if make_pair:
        sections.append({"id":f"SEC-{101+i*5}","course":course,"inst":sections[0]["inst"],"time":times[1],"enrolled":e2,"cap":cap})
    sections += [
        {"id":f"SEC-{102+i*5}","course":RNG.choice([x for x in names if x != course]),"inst":RNG.choice(inst),"time":times[2],"enrolled":RNG.choice([20,24,28,30]),"cap":RNG.choice([30,35])},
        {"id":f"SEC-{103+i*5}","course":RNG.choice(names),"inst":RNG.choice(inst),"time":times[3],"enrolled":RNG.choice([16,18,22,25]),"cap":RNG.choice([25,30])},
    ]
    parts=[]
    for s in sections:
        parts.append(f"{s['course']} section {s['id']} with {s['inst']} meets {s['time']} and has {s['enrolled']} students enrolled out of {s['cap']} seats")
    prompt="Department schedule review. " + "; ".join(parts) + ". Analyze which sections need attention."
    flagged=[s for s in sections if s['enrolled']/s['cap'] < .5]
    flagged_ids=[s['id'] for s in flagged]
    cons=[]; used=set()
    for a in flagged:
        for b in flagged:
            if a is b or a['id'] in used or b['id'] in used: continue
            if a['course']==b['course'] and a['time']!=b['time']:
                keep,cancel=(a,b) if a['enrolled']>=b['enrolled'] else (b,a)
                if a['enrolled']+b['enrolled'] <= keep['cap']:
                    cons.append({"keep":keep['id'],"cancel":cancel['id'],"combinedEnrollment":a['enrolled']+b['enrolled'],"capacity":keep['cap']})
                    used.add(a['id']); used.add(b['id'])
    no=[s['id'] for s in flagged if s['id'] not in used]
    return prompt, minjson({"FlaggedSections":flagged_ids,"Consolidations":cons,"NoAction":no})

def eob_case(i):
    code=RNG.choice(["99214","71046","70553","93000"])
    carc=RNG.choice(["197","50","96","18"])
    denied=i%2==0
    item={"item":[{"sequence":1,"productOrService":{"coding":[{"system":"http://www.ama-assn.org/go/cpt","code":code}]},"adjudication":[{"category":{"coding":[{"code":"submitted"}]},"amount":{"value":RNG.choice([150,260,900])}},{"category":{"coding":[{"code":"eligible"}]},"amount":{"value":RNG.choice([120,228,368])}},{"category":{"coding":[{"code":"benefit"}]},"amount":{"value":RNG.choice([70,120,200])}}]}]}
    if denied:
        item["item"][0]["reviewOutcome"]={"decision":{"coding":[{"code":"denied"}]},"reason":{"coding":[{"code":carc}]}}
    return "Process this ExplanationOfBenefit: " + minjson(item)

def nav_case(i):
    maps = [
        '[["start","normal","treasure"],["c7","wall","wall"]]',
        '[["start","c8","treasure"],["normal","normal","normal"]]',
    ]
    return f"Find a path from position A1, where the position is formatted as {{column}}{{row}}. The map object's coordinates are formatted as [{{rowIndex}},{{columnIndex}}]. The path should find the treasure on this map: {RNG.choice(maps)}. use strategy {RNG.choice(['maximize_score','get_coins','swift'])}. bad c8"

def tool_completion(name, arg_key, text):
    return "<tool_call>" + minjson({"name":name,"arguments":{arg_key:text}}) + "</tool_call>"

def sample(user, mode, expected, ability):
    # expected either direct answer or tool-call completion string
    gt = {"mode":mode,"expected":expected}
    return {"prompt":[{"role":"system","content":SYSTEM_ROUTING},{"role":"user","content":user}],"tools":TOOLS,"reward_model":{"ground_truth":minjson(gt),"style":"rule"},"extra_info":{"ability":ability},"ability":"supervisor_routing"}

def final_sample(user, answer, ability):
    return {"prompt":[{"role":"system","content":SYSTEM_FINAL},{"role":"user","content":user}],"reward_model":{"ground_truth":answer,"style":"exact_match"},"extra_info":{"ability":ability},"ability":"supervisor_final"}

def build(n):
    rows=[]; finals=[]
    for i in range(n):
        kind=i%8
        if kind==0:
            u,a=RNG.choice(simple); rows.append(sample(u,"direct",a,"c5")); finals.append(final_sample(u,a,"c5"))
        elif kind==1:
            u=RNG.choice(privacy); rows.append(sample(u,"direct",REFUSAL,"c1")); finals.append(final_sample(u,REFUSAL,"c1"))
        elif kind==2:
            u,a=sched_case(i); rows.append(sample(u,"direct",a,"c2")); finals.append(final_sample(u,a,"c2"))
        elif kind==3:
            u=RNG.choice(open_data); exp=tool_completion("AgentCoreGatewayTool-open-data-lookup___lookup_open_data","question",u); rows.append(sample(u,"tool",exp,"c4")); finals.append(final_sample("Return this tool result exactly:\nNational Cancer Institute (NCI) and National Human Genome Research Institute (NHGRI)","National Cancer Institute (NCI) and National Human Genome Research Institute (NHGRI)","c4_final"))
        elif kind==4:
            u=eob_case(i); exp=tool_completion("AgentCoreGatewayTool-claims-solver___analyze_eob","question",u); rows.append(sample(u,"tool",exp,"c18")); finals.append(final_sample('Return this tool result exactly:\n{"TotalAllowed":228.00,"MemberResponsibility":1577.60,"DeniedLines":[{"code":"70553","carc":"197"}]}','{"TotalAllowed":228.00,"MemberResponsibility":1577.60,"DeniedLines":[{"code":"70553","carc":"197"}]}',"c18_final"))
        elif kind==5:
            u="Grey key 1 is: " + RNG.choice(["AWSisAwesome","CloudRocks","GreyMagic"]); exp=tool_completion("AgentCoreGatewayTool-grey-code___process_grey_code_challenge","question",u); rows.append(sample(u,"tool",exp,"c42")); finals.append(final_sample("Return this tool result exactly:\nThanks","Thanks","c42_final"))
        elif kind==6:
            u="What is grey code 1?"; exp=tool_completion("AgentCoreGatewayTool-grey-code___process_grey_code_challenge","question",u); rows.append(sample(u,"tool",exp,"c32")); finals.append(final_sample("Return this tool result exactly:\nAWme","AWme","c32_final"))
        else:
            u=nav_case(i); exp=tool_completion("pathfinding_specialist","prompt",u); rows.append(sample(u,"tool",exp,"navigation")); finals.append(final_sample('Return this path exactly:\n["right","right"]','["right","right"]',"navigation_final"))
    return rows, finals

def write_jsonl(path, rows):
    with path.open('w') as f:
        for idx,r in enumerate(rows):
            r.setdefault('extra_info',{})['index']=idx
            f.write(minjson(r)+'\n')

routing, finals = build(600)
write_jsonl(DATA/'supervisor_routing_train.jsonl', routing[:500])
write_jsonl(DATA/'supervisor_routing_validation.jsonl', routing[500:])
write_jsonl(DATA/'supervisor_final_train.jsonl', finals[:480])
write_jsonl(DATA/'supervisor_final_validation.jsonl', finals[480:])
print('wrote', len(routing[:500]), len(routing[500:]), len(finals[:480]), len(finals[480:]))
