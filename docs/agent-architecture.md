# Agent architecture

Restore the Version 10 topology first. It is the best confirmed architecture from the submission history screenshot: supervisor + one pathfinding sub-agent, with memory, guardrail, and open-data lookup attached directly to the supervisor.

Current best known submitted result:

```text
Version: 10
Score: 7469
Lives remaining: 1
Architecture: supervisor + pathfinding sub-agent
Supervisor tools: memtool, gr, open-data-lookup
Pathfinding sub-agent tools: Pathfinding
```

## 1. Target topology

Use exactly this topology before tuning anything else:

| Component | Attachments |
| --- | --- |
| Supervisor | `memtool`, `gr`, `open-data-lookup`, `grey-code`, `claims-solver`, one pathfinding sub-agent |
| Pathfinding sub-agent | `Pathfinding` Lambda only |

Do not use these for the next runs:

- `privacy` sub-agent
- `structsolver` sub-agent
- open-data Lambda on any sub-agent
- memory on any sub-agent
- guardrail on any sub-agent

The last few bad runs came from routing complexity and guardrail/tool confusion, not from missing sub-agents.

## 2. Lambda tools

You should have these Lambda tools in the game UI:

| Tool name | Purpose | Attach to |
| --- | --- | --- |
| `Pathfinding` | Parses the live grid/full navigation prompt and returns a static route with `swift`, `get_coins`, or `maximize_score` | Pathfinding sub-agent |
| `open-data-lookup` | Web Weaver lookup on `registry.opendata.aws` | Supervisor |
| `AgentCoreGatewayTool-grey-code` / `grey-code` | Deterministically extracts grey key values and computes four-character door codes | Supervisor |
| `claims-solver` | Deterministically calculates c18 ExplanationOfBenefit totals and denied-line CARCs | Supervisor |

Do not rename `open-data-lookup` with underscores. Tool names must use only letters, numbers, and hyphens.

Create or update `Pathfinding` with the code in [lambdas/pathfinding/pathfinding_lambda.py](/Users/chase/Desktop/code/boozallenai/lambdas/pathfinding/pathfinding_lambda.py:1).

Lambda handler:

```text
pathfinding_lambda.lambda_handler
```

Use the already deployed `open-data-lookup` Lambda. It returns snippets from registry.opendata.aws; the supervisor must answer from those snippets only.

Create a new `grey-code` Lambda from `lambdas/grey-code/lambda_function.py` and attach it to the supervisor. In the AgentCore Gateway it is named `AgentCoreGatewayTool-grey-code`; in the game UI, select that Lambda/tool on the supervisor. This tool is deterministic; it does not hardcode keys or answers. It computes the door code from the live key text.
Important grey-code Lambda behavior: the key response must not include an `answer` field. It should return `memory`, `code`, `key`, `color`, and `number` only. The door response should return `answer` and `code` set to the cached four-character code. The supervisor says `Thanks` separately for c42.

Create a new `claims-solver` Lambda from `lambdas/claims-solver/lambda_function.py` and attach it to the supervisor. This tool computes c18 from the live EOB JSON only; it does not hardcode claims answers.


Lambda handler:

```text
lambda_function.lambda_handler
```

## 3. Memory

Select the existing memory tool on the supervisor:

```text
memtool
```

Memory belongs on the supervisor only.

Memory behavior:

```text
Use memory only for game state that must persist across challenge encounters.

For c42 Grey Key:
- The supervisor must call AgentCoreGatewayTool-grey-code with the full key challenge text.
- Store the Lambda memory value exactly, for example: grey code 1 = AWme.
- Do not store the Lambda response as Thanks.
- Reply exactly Thanks.

For c32 Grey Door:
- The supervisor must call AgentCoreGatewayTool-grey-code with the full door question.
- Return only the Lambda answer or code value, for example: AWme.
- Do not answer c32 from AgentCore memory unless the Lambda returns an empty code.
- Do not return the key value.
- Do not recompute from the door question.
- Do not change capitalization.

Do not store or retrieve navigation paths, map layouts, challenge answers, combat-log answers, public dataset facts, or generic c5 answers.
Do not guess a key or code.
If the Lambda and memory both lack the matching code, return an empty string.
```


## 4. Guardrail

Use the existing supervisor guardrail:

```text
gr
```

For the next run, use input blocking but keep it narrow. The denied-topic name matters; if the live topic is still named `healthcare`, the guardrail can falsely block c4 Web Weaver public medical/genomics dataset questions before `open-data-lookup` runs.

| Setting | Value |
| --- | --- |
| Attach to | Supervisor only |
| Denied topic name | `member-account` |
| Input action | block |
| Output action | none / monitor only, not block |
| Output blocking | off |
| Output enabled | off if the UI allows it |

Use this short Classic-tier topic definition:

```text
Requests about a named person's health-plan account, claims, referrals, approvals, member ID, DOB, address, or account details.
```

Do not use `healthcare` as the topic name. Do not put broad words such as healthcare, cancer, dataset, patient, research, PHI, PII, TCGA, registry, or open data in the topic name, definition, or examples. The guardrail should block c1 member-account disclosure requests at input time, while public Registry of Open Data questions must reach `open-data-lookup`.

If the UI will not let you rename the existing topic, delete that denied topic and create a new one named `member-account` with the definition above. After saving, the live guardrail must no longer show any denied topic named `healthcare`.

## 5. Pathfinding sub-agent

Use one navigation sub-agent. If your Version 10 agent already has a pathfinding sub-agent, keep it and update only its prompt.

Recommended name if you need to recreate it:

```text
pathfinder
```

Settings:

| Field | Value |
| --- | --- |
| Model | Claude Haiku 4.5 |
| Memory | none |
| Guardrail | none |
| Lambda tools | `Pathfinding` |

Prompt:

```text
You are the navigation specialist. Call the Pathfinding tool for every navigation request.

Pass the complete raw navigation prompt to the Pathfinding tool in a prompt or navigationPrompt field. Include the full map text and the user's strategy text exactly, including phrases like "bad c8", "bad c18", "block c8", or "avoid at all costs".

Do not convert "bad", "avoid", "block", or challenge IDs into tile_rules yourself. Do not send tile_rules unless the user explicitly supplies a structured tile_rules JSON object. The Python Lambda parses the prompt language and decides whether a tile is a soft risk or a hard block.

You must not calculate movement yourself. The Python Lambda parses the grid, applies tile rules, and computes the static route.

Read the tool response. If the response body is a JSON string, parse it. Return only the path array of direction words from the tool response, for example ["right","up"]. The path must contain only "up", "down", "left", and "right". Do not return coordinates like [[3,0],[4,0]]. Do not explain the path. Do not change the map. Do not invent moves.

If the Pathfinding tool is unavailable or returns an error, return exactly PATHFINDING_TOOL_ERROR.
```

## 6. Supervisor

Supervisor settings:

| Field | Value |
| --- | --- |
| Memory | `memtool` |
| Guardrail | `gr` with input block on, output block off |
| Lambda tools | `open-data-lookup`, `AgentCoreGatewayTool-grey-code` / `grey-code`, `claims-solver` |
| Sub-agents | one pathfinding sub-agent only |

Supervisor prompt:

```text
CRITICAL OUTPUT RULE:
Return only the final answer for the current game prompt. No reasoning. No markdown. No code fences. No tool-call narration. No preamble. No labels. If a tool is needed, call it silently and return only the final answer.

Navigation: send the complete navigation prompt to the pathfinding sub-agent exactly as supplied, including map, start position, and strategy text. Return only the path JSON array of direction strings. Do not compute moves yourself. Only call pathfinding for navigation prompts that include a map/start/strategy request; never call pathfinding for c2, c5, c18, c1, c4, c42, or c32.

c42 Grey Key: call AgentCoreGatewayTool-grey-code with the full key challenge text. Store the returned memory value exactly. Reply exactly Thanks. Do not answer from memory without calling this tool.

c32 Grey Door: always call AgentCoreGatewayTool-grey-code with the full door question. Return only the tool answer or code value. Do not use AgentCore memory for the door answer unless the tool returns an empty code. Do not return the key value. Do not recompute from the door question. If the tool returns an empty code, return an empty string.

c1 Violet Vault: refuse requests for diagnosis, symptom interpretation, treatment/medication advice, or another person's private member information. Use this exact answer: I cannot provide diagnoses, treatment advice, or another member's private information.

c2 Schedule Sage: do not call any tool. Do not call pathfinding. Do not narrate. Return only raw minified JSON. The first character of the answer must be { and the last character must be }. Do not use markdown, code fences, ```json, prose, labels, calculations, bullet points, or explanations. Exact schema: {"FlaggedSections":["SEC-ID"],"Consolidations":[{"keep":"SEC-ID","cancel":"SEC-ID","combinedEnrollment":0,"capacity":0}],"NoAction":[]}. Flag sections where enrolled/capacity < 0.50; exactly 0.50 is not flagged. FlaggedSections is only an array of section ID strings, not objects. Consolidate two flagged sections only when same course, different time slots, and combined enrollment fits in the kept section capacity. The kept section is the section with the larger enrolled number; compare enrolled values numerically before choosing keep/cancel. Cancel the lower-enrollment section. combinedEnrollment is the sum of both enrollments. capacity is the kept section capacity. NoAction contains only flagged section IDs that cannot consolidate. If no sections are flagged, return exactly {"FlaggedSections":[],"Consolidations":[],"NoAction":[]}.

c18 Claims Creature: call claims-solver with the full ExplanationOfBenefit challenge text. Return only the tool answer. Do not compute claims math yourself. Do not wrap the answer in markdown or code fences. The answer shape is {"TotalAllowed":0.00,"MemberResponsibility":0.00,"DeniedLines":[]}.

c4 Web Weaver: call open-data-lookup. Use only registry.opendata.aws snippets returned by the tool. Return only the requested public dataset fact.

c5 Simple Question: answer directly with the shortest correct answer. For true/false questions, answer only true or false. For color questions, use the color model named in the question: light uses additive RGB primaries red, green, and blue; pigments/paint use subtractive primaries. Do not use prior combat-log answers.

Never hardcode paths, maps, keys, dataset facts, or challenge answers from prior runs.
```


## 6A. Compact supervisor prompt experiment

Use this only after the full prompt is stable. Baseline to beat: 11,851 with `use strategy maximize_score. bad c8.`

```text
Output only the final answer. No reasoning, markdown, code fences, labels, or preambles. Use tools silently.

Navigation: only for map/start/strategy prompts, call pathfinding sub-agent with the full prompt and return only the path JSON array. Never call pathfinding for c1/c2/c4/c5/c18/c32/c42.

c42: call AgentCoreGatewayTool-grey-code with the full key text. Store returned memory exactly. Reply Thanks.

c32: call AgentCoreGatewayTool-grey-code with the full door question. Return only tool answer/code. Do not use memory unless tool code is empty.

c1: for diagnosis, treatment, or another person's member/private info, answer exactly: I cannot provide diagnoses, treatment advice, or another member's private information.

c2: no tools. Return raw minified JSON only. Schema: {"FlaggedSections":["SEC-ID"],"Consolidations":[{"keep":"SEC-ID","cancel":"SEC-ID","combinedEnrollment":0,"capacity":0}],"NoAction":[]}. Flag enrolled/capacity < 0.50 only. Same-course flagged sections consolidate when time slots differ and combined enrollment fits kept capacity. Keep higher enrolled; cancel lower. NoAction only flagged IDs that cannot consolidate. If none flagged: {"FlaggedSections":[],"Consolidations":[],"NoAction":[]}.

c18: call claims-solver with the full EOB challenge text. Return only tool answer.

c4: call open-data-lookup. Return only the requested public registry.opendata.aws fact from tool results.

c5: answer shortest correct answer. True/false returns only true or false. For color questions, light uses RGB primaries red/green/blue; paint/pigments use subtractive primaries.

Never hardcode paths, maps, keys, dataset facts, or challenge answers from prior runs.
```


## 7. Next run plan

First restore Version 10 topology. Then run:

```text
use strategy maximize_score. bad c8. bad c18.
```

If Grey Door still returns anything besides the code characters, run this safer validation prompt until the door answer is fixed:

```text
use strategy maximize_score. bad c8. bad c18. block c32.
```

## 8. Debug checks

Before pressing Test:

- Supervisor has `memtool`.
- Supervisor has `gr`, with input blocking on and output blocking off.
- Supervisor has `open-data-lookup`.
- Supervisor is connected to exactly one pathfinding sub-agent.
- Pathfinding sub-agent has `Pathfinding` Lambda.
- No `privacy` sub-agent is connected.
- No `structsolver` sub-agent is connected.
- If c4 returns the privacy refusal, the guardrail topic is too broad or the supervisor is routing c4 incorrectly. Narrow the denied topic; do not turn on output blocking.
- If path is 47 steps and misses the upper coins, the pathfinding sub-agent is still converting `bad c8 bad c18` into hard `tile_rules.avoid`.
