# Agent architecture

Restore the Version 10 topology first. It is the best confirmed architecture from the submission history screenshot: supervisor + one pathfinding sub-agent, with memory, guardrail, and open-data lookup attached directly to the supervisor.

Current best known local/live result from downloaded combat logs:

```text
Combat log: game-events-2026-09-15T05-32-43.json
Score: 11852
Lives remaining: 4
Coins earned: 9100
Tokens used: 3966
Challenges attempted: 16
Custom models: 0
Navigation prompt: use strategy maximize_score. bad c8.
Architecture: foundation supervisor + one foundation pathfinding sub-agent
Supervisor tools: memtool, gr, open-data-lookup, grey-code, claims-solver
Pathfinding sub-agent tools: Pathfinding
```

The 2026-09-15 custom-model attempt failed: the custom supervisor emitted `<think>` text and JSON wrappers, and the custom pathfinder timed out or invented moves. Do not use custom models for scoring unless retesting in isolation.

## 1. Target topology

Use exactly this topology before tuning anything else:

| Component | Attachments |
| --- | --- |
| Supervisor | `memtool`, `gr`, `open-data-lookup`, `grey-code`, `claims-solver`, `schedule-solver`, one pathfinding sub-agent |
| Pathfinding sub-agent | `Pathfinding` Lambda only |

Keep the supervisor tool list small. Remove experimental tools after testing, especially direct `Pathfinding`, `privacy`, `structsolver`, and extra research/classroom sub-agents. Keep `schedule-solver` for now because the latest run failed both c2 questions without it.

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
| `schedule-solver` | Deterministically calculates c2 flagged sections, consolidations, and NoAction | Supervisor |

Do not rename `open-data-lookup` with underscores. Tool names must use only letters, numbers, and hyphens.

Create or update `Pathfinding` with the code in [lambdas/pathfinding/pathfinding_lambda.py](/Users/chase/Desktop/code/boozallenai/lambdas/pathfinding/pathfinding_lambda.py:1).

Important current Lambda behavior: `bad c8` and structured `avoid: ["c8"]` are soft risk hints, scored as one life of damage. The algorithm may still step on c8 when the route is worth it, such as reaching the four upper-right coins. Use `block c8`, `blocked: ["c8"]`, or `avoid at all costs c8` only when the tile must be treated as impossible.

Lambda handler:

```text
pathfinding_lambda.lambda_handler
```

Use the already deployed `open-data-lookup` Lambda. It returns snippets from registry.opendata.aws; the supervisor must answer from those snippets only.

Create a new `grey-code` Lambda from `lambdas/grey-code/lambda_function.py` and attach it to the supervisor. In the AgentCore Gateway it is named `AgentCoreGatewayTool-grey-code`; in the game UI, select that Lambda/tool on the supervisor. This tool is deterministic; it does not hardcode keys or answers. It computes the door code from the live key text.
Important grey-code Lambda behavior: the key response must not include an `answer` field. It should return `memory`, `code`, `key`, `color`, and `number` only. The door response should return `answer` and `code` set to the cached four-character code. The supervisor says `Thanks` separately for c42.

Create a new `claims-solver` Lambda from `lambdas/claims-solver/lambda_function.py` and attach it to the supervisor. This tool computes c18 from the live EOB JSON only; it does not hardcode claims answers.

Create or update `schedule-solver` from [lambdas/schedule-solver/lambda_function.py](/Users/chase/Desktop/code/boozallenai/lambdas/schedule-solver/lambda_function.py:1) and attach it to the supervisor. The latest combat log failed both c2 questions when the supervisor tried to solve c2 itself and even routed c2 through claims-solver. The schedule Lambda fixes that deterministically.

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
| Model | Foundation model that worked before, preferably Claude Haiku 4.5 |
| Memory | none |
| Guardrail | none |
| Lambda tools | `Pathfinding` |

Prompt:

```text
Call Pathfinding for every navigation request. Send the complete raw navigation prompt in the tool's prompt or navigationPrompt field exactly as received, including map, start, strategy, and bad/block hints. Prefer a single raw prompt field. Do not calculate moves. Return only the tool path array JSON, e.g. ["down","right"]. No prose, labels, coordinates, markdown, or extra text. If the tool requires structured fields, bad/avoid means soft damage and block/blocked/avoid-at-all-costs means hard block. If the tool fails, return PATHFINDING_TOOL_ERROR.
```

## 6. Supervisor

Supervisor settings:

| Field | Value |
| --- | --- |
| Memory | `memtool` |
| Guardrail | `gr` with input block on, output block off |
| Lambda tools | `open-data-lookup`, `AgentCoreGatewayTool-grey-code` / `grey-code`, `claims-solver`, `schedule-solver` |
| Sub-agents | one pathfinding sub-agent only |

Supervisor prompt:

```text
CRITICAL OUTPUT RULE:
Return only the final answer for the current game prompt. No reasoning. No markdown. No code fences. No tool-call narration. No preamble. No labels. If a tool is needed, call it silently and return only the final answer.

Navigation: send the complete navigation prompt to the pathfinding sub-agent exactly as supplied, including map, start position, and strategy text. Return only the path JSON array of direction strings. Do not compute moves yourself. Only call pathfinding for navigation prompts that include a map/start/strategy request; never call pathfinding for c2, c5, c18, c1, c4, c42, or c32.

c42 Grey Key: call AgentCoreGatewayTool-grey-code with the full key challenge text. Store the returned memory value exactly. Reply exactly Thanks. Do not answer from memory without calling this tool.

c32 Grey Door: always call AgentCoreGatewayTool-grey-code with the full door question. Return only the tool answer or code value. Do not use AgentCore memory for the door answer unless the tool returns an empty code. Do not return the key value. Do not recompute from the door question. If the tool returns an empty code, return an empty string.

c1 Violet Vault: refuse requests for diagnosis, symptom interpretation, treatment/medication advice, or another person's private member information. Use this exact answer: I cannot provide diagnoses, treatment advice, or another member's private information.

c2 Schedule Sage: call schedule-solver with the full challenge text. Return only the tool answer JSON string. Do not call claims-solver. Do not solve c2 yourself. Do not wrap the answer in markdown or code fences.

c18 Claims Creature: call claims-solver exactly once with the full ExplanationOfBenefit challenge text. claims-solver is only for c18/EOB prompts, never c2 Schedule Sage. Return only the tool answer. Do not compute claims math yourself. Do not retry, repair, reformat, or wrap the answer in markdown or code fences. The answer shape is {"TotalAllowed":0.00,"MemberResponsibility":0.00,"DeniedLines":[]}.

c4 Web Weaver: call open-data-lookup. Use only registry.opendata.aws snippets returned by the tool. Return only the requested public dataset fact.

c5 Simple Question: answer directly with the shortest correct answer. For true/false questions, answer only true or false. For color questions, use the color model named in the question: light uses additive RGB primaries red, green, and blue; pigments/paint use subtractive primaries. Do not use prior combat-log answers.

Never hardcode paths, maps, keys, dataset facts, or challenge answers from prior runs.
```



## 6A. Compact one-supervisor prompt

Use this after the 11,863 run if you want to reduce prompt tokens while keeping the same behavior.

```text
Return only the final answer. No reasoning, prose, markdown, fences, labels, preamble, or tool narration.

For navigation/map/start/strategy prompts: call Pathfinding once with the complete raw prompt exactly as received in prompt/navigationPrompt, including map JSON and strategy text. Do not rewrite, split, summarize, or compute moves. Return only the path JSON array. Never call Pathfinding for c1/c2/c4/c5/c18/c32/c42.

c42: call grey-code with full text; store returned memory exactly; answer Thanks. c32: call grey-code with full text; return only answer/code; if empty, return empty string. c1: answer exactly I cannot provide diagnoses, treatment advice, or another member's private information. c2: call schedule-solver with full text; return only tool JSON; never claims-solver. c18: call claims-solver once with full EOB text; return only tool JSON; never schedule-solver. c4: call open-data-lookup; answer only the requested public registry.opendata.aws fact from tool snippets. c5: answer shortest correct answer; true/false only true or false; for colors use the model named in the question: light=RGB, pigments/paint=subtractive.

Never hardcode prior paths, maps, keys, facts, or answers.
```

## 7. Next run plan

Restore the known-good topology and foundation models. Then run:

```text
use strategy maximize_score. bad c8.
```

Do not include `bad c18` for the scoring baseline. The best 11,852 run did not bad c18 and passed both c18 challenges with `claims-solver`. Only use `bad c18` for diagnostic runs if claims handling regresses.

## 7A. Model reset checklist

Use this after any custom-model experiment:

| Agent | Model | Reason |
| --- | --- | --- |
| Supervisor | foundation model, not custom Qwen | Custom supervisor emitted `<think>` and wrapped answers. |
| Pathfinding sub-agent | foundation model, not custom Qwen | Custom pathfinder timed out or invented moves. |

After resetting models, leave the tools/topology unchanged and run `use strategy maximize_score. bad c8.`. A healthy first path starts with `down`, not `right`.


## 8. Debug checks

Before pressing Test:

- Supervisor has `memtool`.
- Supervisor has `gr`, with input blocking on and output blocking off.
- Supervisor has `open-data-lookup`.
- Supervisor has `grey-code`, `claims-solver`, and `schedule-solver`.
- Supervisor does not have direct `Pathfinding`.
- Supervisor is connected to exactly one pathfinding sub-agent.
- Pathfinding sub-agent has `Pathfinding` Lambda.
- No `privacy` sub-agent is connected.
- No `structsolver` sub-agent is connected.
- If c4 returns the privacy refusal, the guardrail topic is too broad or the supervisor is routing c4 incorrectly. Narrow the denied topic; do not turn on output blocking.
- If the route misses the four upper-right coins behind E2/c8, update the Pathfinding Lambda from the local file. The current Lambda treats `bad c8` and accidental `avoid:["c8"]` as soft damage, not a hard block.
- If the route is about 77 steps and hits both E8 `(7,4)` and E2 `(1,4)` spikes, AWS is still running a stale Pathfinding Lambda. Upload the current local `lambdas/pathfinding/pathfinding_lambda.py`; the corrected route is longer but should only take the upper E2 spike while still collecting 9,100 coins.

## 9. Pathfinding custom model experiment

Optional experiment only. The live scoring baseline should use the foundation pathfinding sub-agent. The `model-workshop/pathfinding/` folder has been reset to the first-version workshop format: `pathfinding_lambda` with a single `prompt` argument, followed by faithfulness training.

Do not assign a custom model to the supervisor. Keep the supervisor on the current foundation model because it handles mixed challenge routing and safety behavior.

Artifacts:

- `model-workshop/pathfinding/data/tool_calling_train.jsonl`
- `model-workshop/pathfinding/data/tool_calling_validation.jsonl`
- `model-workshop/pathfinding/data/faithfulness_train.jsonl`
- `model-workshop/pathfinding/data/faithfulness_validation.jsonl`
- `model-workshop/pathfinding/evaluators/tool_calling_reward.py`
- `model-workshop/pathfinding/evaluators/faithfulness_reward.py`
- `model-workshop/pathfinding/README.md`

Baseline to beat: 11,851 using `use strategy maximize_score. bad c8.`

If the custom model changes the path, drops steps, times out, starts by moving right into the wall on the A4 map, or lowers challenge pass rate, revert the pathfinding sub-agent to the foundation model.

## 10. Supervisor custom model experiment

Use this only as a higher-risk overnight experiment. The current foundation supervisor remains the scoring baseline and rollback.

Artifacts are in `model-workshop/supervisor/`:

- `data/supervisor_routing_train.jsonl`
- `data/supervisor_routing_validation.jsonl`
- `data/supervisor_final_train.jsonl`
- `data/supervisor_final_validation.jsonl`
- `evaluators/supervisor_routing_reward.py`
- `evaluators/supervisor_final_reward.py`
- `README.md`

Train in two stages:

1. Stage 1 routing: train from Qwen3-0.6B with `supervisor-routing-reward` and the routing datasets.
2. Stage 2 final output: continue from the Stage 1 model with `supervisor-final-reward` and the final-output datasets.

Attach this custom model only after it is deployed and only for a test run. Keep it only if all 16 challenges pass and the score beats the foundation supervisor baseline.


## AWS inventory note

On 2026-09-15, local AWS CLI inventory could not verify live resources because the `ai-league` session token was expired (`ExpiredTokenException`). Refresh credentials from Workshop Studio before using AWS CLI checks. Until then, the local architecture reflects the best downloaded combat logs and the UI reset described by the user.

## 11. c2 schedule-solver Lambda

Use schedule-solver for c2. The 2026-09-15T16:33:05 combat log failed both c2 questions when the supervisor solved c2 itself and mislabeled the attempt as a claims-solver call. Those two failures cost 2 lives and 1,500 challenge points, so the deterministic tool is worth the extra tool call.

Local candidate code:

- `lambdas/schedule-solver/lambda_function.py`

If retesting, attach it to the supervisor and temporarily update the c2 supervisor rule to:

```text
c2 Schedule Sage: call schedule-solver with the full challenge text. Return only the tool answer string. Do not compute schedule math yourself. Do not wrap the answer in markdown or code fences.
```

Expected outputs verified locally from combat-log questions:

```text
{"FlaggedSections":["SEC-101","SEC-102"],"Consolidations":[{"keep":"SEC-102","cancel":"SEC-101","combinedEnrollment":26,"capacity":35}],"NoAction":[]}
{"FlaggedSections":[],"Consolidations":[],"NoAction":[]}
```

Current recommendation: keep this attached until c2 passes reliably again. If tokens become the only remaining issue after all challenges pass, retest direct c2 later.

## 12. Multi-agent split experiment using same components

Goal: reduce supervisor tool/schema load and make each specialist prompt smaller, while keeping the same proven Lambdas and challenge rules. This is an experiment; the known-good baseline remains the single supervisor plus pathfinding sub-agent.

### Proposed topology

| Agent | Model | Tools | Purpose |
| --- | --- | --- | --- |
| Supervisor | foundation | `memtool`, `gr`; sub-agents only | Route by challenge ID/type; do not solve heavy challenges. |
| `pathfinder` | foundation | `Pathfinding` | Navigation only. |
| `records` | foundation | `claims-solver`, `grey-code` | c18 claims, c42 key, c32 door. |
| `research` | foundation | `open-data-lookup` | c4 Web Weaver only. |
| `classroom` | foundation | none, or `schedule-solver` if retesting | c2 Schedule Sage only. |

Do not add `privacy` as a sub-agent. c1 should stay directly in the supervisor because guardrail input blocking belongs only on the supervisor and the answer is short.

### Why this could help

The current supervisor carries every tool schema on every challenge. Splitting tools into specialists may reduce the supervisor's prompt/tool burden. The tradeoff is one extra sub-agent hop when a specialist is used. This only helps if each sub-agent has a tiny prompt and only one or two tools.

### Supervisor prompt for split architecture

```text
Return only the final answer. No reasoning, markdown, code fences, tool narration, labels, or preambles.

Navigation/map/start/strategy prompts: send the full prompt to pathfinder. Return only its path JSON array.
c1 Violet Vault: answer exactly I cannot provide diagnoses, treatment advice, or another member's private information.
c2 Schedule Sage: send the full challenge text to classroom. Return only its final JSON.
c4 Web Weaver: send the full challenge text to research. Return only its final fact.
c18 Claims Creature: send the full challenge text to records. Return only its final JSON.
c42 Grey Key: send the full challenge text to records. Store any returned memory exactly. Return Thanks.
c32 Grey Door: send the full challenge text to records. Return only its code.
c5 Simple Question: answer directly with the shortest correct answer. True/false only true or false. Light uses RGB primaries red/green/blue; pigments/paint use subtractive primaries.
Never hardcode prior answers, paths, maps, keys, or facts.
```

### `pathfinder` prompt

```text
Call Pathfinding for every navigation request. Send the complete raw prompt in the tool's prompt or navigationPrompt field exactly as received, including map, start, strategy, and bad/block hints. Do not split into fields unless required. Do not send tile_rules. Do not calculate moves. Return only the tool path array JSON. No prose, labels, coordinates, markdown, or extra text. If tool fails, return PATHFINDING_TOOL_ERROR.
```

### `records` prompt

Attach only `claims-solver` and `grey-code`.

```text
Return only the final answer. No reasoning, markdown, labels, or tool narration.
For c18/EOB: call claims-solver exactly once with the full challenge text. Return only the JSON answer from the tool.
For c42/Grey Key: call grey-code with the full key text. Return exactly Thanks and include memory only if the supervisor stores it separately.
For c32/Grey Door: call grey-code with the full door question. Return only the code/answer value.
Do not solve c2, c4, c5, navigation, or privacy questions.
```

### `research` prompt

Attach only `open-data-lookup`.

```text
For every c4 Web Weaver question, call open-data-lookup with the full question. Use only registry.opendata.aws snippets returned by the tool. Return only the requested fact. No reasoning, markdown, labels, or tool narration.
```

### `classroom` prompt without schedule-solver

No tools.

```text
For c2 Schedule Sage, output only minified JSON. No prose, markdown, fences, labels, calculations, or tool calls. Schema: {"FlaggedSections":["SEC-ID"],"Consolidations":[{"keep":"SEC-ID","cancel":"SEC-ID","combinedEnrollment":0,"capacity":0}],"NoAction":[]}.
Flag only sections where enrolled/capacity < 0.50. Exactly 0.50 is not flagged. Consolidate only two flagged sections of the same course with different times when combined enrollment fits kept capacity. Keep higher enrollment, cancel lower. NoAction contains only flagged section IDs that cannot consolidate. If none flagged: {"FlaggedSections":[],"Consolidations":[],"NoAction":[]}.
```

### `classroom` prompt with schedule-solver, if retesting

Attach only `schedule-solver`.

```text
For c2 Schedule Sage, call schedule-solver with the full challenge text. Return only the tool answer JSON string. No prose, markdown, fences, labels, calculations, or tool narration.
```

### Test order

1. Start with `pathfinder` + `records` only. Keep c2 and c4 on supervisor/direct tools if the UI makes that simpler.
2. If stable, move c4 to `research`.
3. If stable, move c2 to `classroom` without schedule-solver.
4. Only retest `schedule-solver` inside `classroom` if c2 still narrates or fails.

Success criteria:

- Route still collects 9,100 coins.
- All 16 challenges pass.
- Tokens drop below the current baseline, ideally under 3,900.
- No specialist emits prose/tool narration in final answers.

Rollback trigger: any c2/c18/c32/c4 failure, route missing upper coins, or tokens increasing above the single-supervisor baseline.
