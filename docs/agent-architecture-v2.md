# Agent architecture v2: split specialists

This is an experiment to reduce supervisor tool/schema load while keeping the same proven components. The known-good baseline remains `agent-architecture.md`.

Goal: keep correctness from the 11.8k runs while reducing tokens by moving heavy tools and long challenge rules off the supervisor.

## Baseline to beat

```text
Best known score: 11852
Navigation prompt: use strategy maximize_score. bad c8.
Custom models: none
Models: foundation supervisor + foundation sub-agents
Coins: 9100
Lives: 4
```

## Topology

| Agent | Tools | Purpose |
| --- | --- | --- |
| Supervisor | `memtool`, `gr`; sub-agent links only | Route, answer c1/c5 directly |
| `pathfinder` | `Pathfinding` | Navigation only |
| `records` | `claims-solver`, `grey-code` | c18 claims, c42 key, c32 door |
| `research` | `open-data-lookup` | c4 Web Weaver |
| `classroom` | none first; optional `schedule-solver` only if retesting | c2 Schedule Sage |

Do not use custom models for this v2 test. Do not add `privacy` or `structsolver`.

## Supervisor setup

Attach to supervisor:

- `memtool`
- `gr`
- `pathfinder` sub-agent
- `records` sub-agent
- `research` sub-agent
- `classroom` sub-agent

Do not attach these directly to supervisor in v2:

- `Pathfinding`
- `open-data-lookup`
- `claims-solver`
- `grey-code`
- `schedule-solver`

Guardrail remains supervisor only:

| Setting | Value |
| --- | --- |
| Denied topic name | `member-account` |
| Input action | block |
| Output blocking | off |

Denied topic definition:

```text
Requests about a named person's health-plan account, claims, referrals, approvals, member ID, DOB, address, or account details.
```

## Supervisor prompt

```text
Return only the final answer. No reasoning, markdown, code fences, tool narration, labels, or preambles.

Navigation/map/start/strategy prompts: send the complete navigation prompt to the pathfinding sub-agent exactly as supplied, including the full map, start position, and strategy text. Return only its path JSON array. Do not summarize or extract fields.
c1 Violet Vault: answer exactly I cannot provide diagnoses, treatment advice, or another member's private information.
c2 Schedule Sage: send the full challenge text to classroom. Return only its final JSON.
c4 Web Weaver: send the full challenge text to research. Return only its final fact.
c18 Claims Creature: send the full challenge text to records. Return only its final JSON.
c42 Grey Key: send the full challenge text to records. Store any returned memory exactly. Return Thanks.
c32 Grey Door: send the full challenge text to records. Return only its code.
c5 Simple Question: answer directly with the shortest correct answer. True/false only true or false. Light uses RGB primaries red/green/blue; pigments/paint use subtractive primaries.
Never hardcode prior answers, paths, maps, keys, or facts.
```

## `pathfinder` sub-agent

### Navigation warning

The pathfinder is sensitive. The shortened v2 pathfinder prompt caused the route to miss the upper F2-I2 coin corridor. Use the full proven pathfinder prompt below, and keep the existing `pathfinding_specialist` name if that is the connected UI sub-agent.

Attach only:

- `Pathfinding`

Prompt:

```text
You are the navigation specialist. Call the Pathfinding tool for every navigation request.

Pass the complete raw navigation prompt to the Pathfinding tool in a prompt or navigationPrompt field. Include the full map text and the user's strategy text exactly, including phrases like "bad c8", "bad c18", "block c8", or "avoid at all costs".

Do not convert "bad", "avoid", "block", or challenge IDs into tile_rules yourself. Do not send tile_rules unless the user explicitly supplies a structured tile_rules JSON object. The Python Lambda parses the prompt language and decides whether a tile is a soft risk or a hard block.

You must not calculate movement yourself. The Python Lambda parses the grid, applies tile rules, and computes the static route.

Read the tool response. If the response body is a JSON string, parse it. Return only the path array of direction words from the tool response, for example ["right","up"]. The path must contain only "up", "down", "left", and "right". Do not return coordinates like [[3,0],[4,0]]. Do not explain the path. Do not change the map. Do not invent moves.

If the Pathfinding tool is unavailable or returns an error, return exactly PATHFINDING_TOOL_ERROR.
```

## `records` sub-agent

Attach only:

- `claims-solver`
- `grey-code`

Prompt:

```text
Return only the final answer. No reasoning, markdown, labels, or tool narration.
For c18/EOB: call claims-solver exactly once with the full challenge text. Return only the JSON answer from the tool.
For c42/Grey Key: call grey-code with the full key text. Return exactly Thanks.
For c32/Grey Door: call grey-code with the full door question. Return only the code/answer value.
Do not solve c2, c4, c5, navigation, or privacy questions.
```

Memory note: the supervisor has `memtool`. If the UI does not let the supervisor store memory from a sub-agent response, rely on the `grey-code` Lambda cache for key/door continuity. That has worked locally because `grey-code` stores the computed code in Lambda `/tmp` between key and door calls.

## `research` sub-agent

Attach only:

- `open-data-lookup`

Prompt:

```text
For every c4 Web Weaver question, call open-data-lookup with the full question. Use only registry.opendata.aws snippets returned by the tool. Return only the requested fact. No reasoning, markdown, labels, or tool narration.
```

## `classroom` sub-agent, first test

Attach no tools.

Prompt:

```text
For c2 Schedule Sage, output only minified JSON. No prose, markdown, fences, labels, calculations, or tool calls. Schema: {"FlaggedSections":["SEC-ID"],"Consolidations":[{"keep":"SEC-ID","cancel":"SEC-ID","combinedEnrollment":0,"capacity":0}],"NoAction":[]}.
Flag only sections where enrolled/capacity < 0.50. Exactly 0.50 is not flagged. Consolidate only two flagged sections of the same course with different times when combined enrollment fits kept capacity. Keep higher enrollment, cancel lower. NoAction contains only flagged section IDs that cannot consolidate. If none flagged: {"FlaggedSections":[],"Consolidations":[],"NoAction":[]}.
```

## `classroom` with schedule-solver, only if retesting

Attach only:

- `schedule-solver`

Prompt:

```text
For c2 Schedule Sage, call schedule-solver with the full challenge text. Return only the tool answer JSON string. No prose, markdown, fences, labels, calculations, or tool narration.
```

Use this only if no-tool `classroom` still narrates or fails. Prior supervisor-attached schedule-solver passed c2 but increased total tokens, so this is not the first choice.

## Test order

Do not build all of v2 at once if the UI makes partial edits easy.

1. Start with `pathfinder` + `records`. Move c18/c42/c32 to records. Keep c4 and c2 as they were if needed.
2. Run:

```text
use strategy maximize_score. bad c8.
```

3. If all 16 pass, add `research` and move c4.
4. If all 16 pass, add `classroom` and move c2.
5. Only try `schedule-solver` inside `classroom` if c2 still narrates or fails.

## Success criteria

Keep v2 only if all are true:

- Route still collects 9100 coins.
- All prompted challenges pass.
- Lives remaining stays at 4 or better.
- Token count drops below the current foundation baseline.
- No specialist outputs `<think>`, prose, markdown fences, or repeated tool-call explanation.

## Rollback triggers

Revert to `agent-architecture.md` if any of these happen:

- Route misses upper coins or starts with a bad move.
- c2 fails or adds large narration.
- c18 JSON is wrong or claims-solver is called twice.
- c4 returns the privacy refusal.
- c32 returns anything besides the code.
- Token count rises above the single-supervisor baseline.
