# Experiment log

Ten runs recorded: four user-reported summaries and six inspected combat logs. Never substitute estimates for observed scores.

| Run/time | Map/seed | Strategy | Code/prompt/config version | Coins | Final score | Lives | Duration | Avg tokens/challenge | Completed? | Failures/notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 / 2026-09-14 | Not captured | `swift` (prepared UI prompt; execution log not yet inspected) | LeagueStarter; original pathfinding Lambda | 500 | 2895 | 3 | 39s inferred from 5:00 start and 4:21 remaining | 355 displayed | Victory | 1777 tokens; 5 challenges attempted; loss causes unknown |
| 2 / 2026-09-14 | Full map not included; start [3,0] | `get_coins` confirmed by InputPrompt | LeagueStarter setup; exact runtime configuration absent from log | 2250 | 2953 | 0 | 79s event time | 297 | Defeat | 2968 tokens; 10 reported challenges; fatal c32 door |
| 3 / 2026-09-14 | Not captured | `get_coins` | Supervisor-only; `memtool`; healthcare denied-topic guardrail; no sub-agent | 250 | 2307 | 5 | 10s inferred from 5:00 start and 4:50 remaining | 193 displayed | Game Over | 385 tokens; 2 challenges attempted; no treasure bonus; likely navigation/wiring failure |
| 4 / 2026-09-14 | Full map not included; start [3,0], treasure [9,9] inferred by model response | `swift` (InputPrompt empty; model said no strategy specified) | Supervisor with `memtool` + healthcare denied-topic guardrail; one `pathfinding_specialist` sub-agent with Pathfinding Lambda | 900 | 3703 | 4 | 38s inferred from 5:00 start and 4:22 remaining | 197 displayed | Victory | Won c5, c5, c1; lost c4 due missing registry lookup tool; navigation answer still verbose |
| 5 / 2026-09-14 | Same displayed map as run 4 | `get_coins` confirmed by InputPrompt | Same supervisor plus `pathfinding_specialist` setup | 4450 | 6450 | 1 | 104s inferred from 5:00 start and 3:16 remaining | 250 displayed | Victory | Best score; won c1, key, door, c2, many coins; lost c4, one c5, two spikes |
| 6 / 2026-09-14 | Same displayed map as runs 4-5 | `get_coins` confirmed by InputPrompt | Same supervisor plus `pathfinding_specialist` setup | 4300 | 6344 | 1 | 91s inferred from 5:00 start and 3:29 remaining | 206 displayed | Victory | User-reported score; won door/key/c2 but failed c1 and c4; two spikes |
| 7 / 2026-09-14 | Not moved from start [3,0] | `get_coins` confirmed by InputPrompt | After adding `open_data_lookup` and updating supervisor prompt | 0 | 1255 | 5 | log timeElapsed invalid/unusable | 995 displayed | Game Over | Navigation output returned coordinate pairs instead of direction strings |
| 8 / 2026-09-14 | Not moved from start [3,0] | `get_coins` confirmed by InputPrompt | After tightening navigation output prompt | 0 | 1250 | 5 | log timeElapsed invalid/unusable | 1895 displayed | Game Over | Supervisor could not access `pathfinding_specialist`; sub-agent wiring/tool availability likely broken |
| 9 / 2026-09-14 | User-reported; no downloaded log found yet | `get_coins` | After attempting to restore sub-agent | 0 | 1250 | 5 | 20s reported | 1212 displayed | Game Over | Returned path hit a wall; path was invented or malformed, not returned by Pathfinding Lambda |
| 10 / 2026-09-14 | Pasted transcript | `get_coins` | Fixed Pathfinding parser; supervisor + sub-agent + `open-data-lookup` | 4450 | 6515 | 1 | 92s reported | 185 displayed | Victory | New best; c4 called lookup but answered guardrail refusal; red-light c5 answered false |

## Run 1 breakdown

Source: user's pasted Victory summary following LeagueStarter setup.

- Time remaining: 4:21.
- Lives remaining: 3; life bonus: 750.
- Coins earned: 500.
- Tokens used: 1777; challenges attempted: 5; displayed average: 355 tokens/challenge.
- Token bonus: 645; treasure bonus: 1000.
- Total: `500 + 750 + 645 + 1000 = 2895`.

The result is consistent with 250 points per remaining life and a token bonus of `1000 - displayed average tokens/challenge`. These are hypotheses from one result, not confirmed general formulas; rounding, caps, and other conditions remain unknown.

Compared with the earlier observed submission (2827 points, 2117 tokens, 3 lives), this is +68 points and 340 fewer tokens. Map and earlier configuration were not captured, so this does not establish a controlled improvement.

The swift run's loss causes remain unverified because its combat log was not supplied.

## Run 2: get_coins

Source: `game-events-2026-09-14T22-06-04.json`, copied from Downloads into ignored `.local/combat-logs/`. InputPrompt explicitly selects `get_coins`. The export contains game events and agent answers, but no complete map, per-call token usage, runtime configuration, or raw tool-call trace.

Score: `2250 coins + 0 life bonus + 703 token bonus + 0 treasure bonus = 2953`. This is 58 above the swift score despite defeat. The 2250 coins comprise four c5 wins (1000), one c2 win (750), and two c7 pickups (500). Life and treasure bonuses were both lost.

Damage sequence:

| Event | Map position [row,col] | Damage | Observation |
| --- | --- | --- | --- |
| c1 Violet Vault | [5,8] | 1 | Agent wrote a long refusal; grader marked failure. Required guardrail behavior is still unknown. |
| c4 Web Weaver | [6,9] | 1 | Agent declined the requested website lookup because it lacked a browsing tool. |
| c42 Grey Key | [7,5] | 0 | Given `Grey key 1 is: AWSisAwesome`; agent asked for clarification; grader marked failure. |
| c8 spike | [7,4] | 1 | Route crossed the trap to reach coins. |
| c32 Grey Door | [2,3] | 5 | Asked `What is grey code 1?`; agent answered about binary Gray code instead of recalling the earlier key. Fatal. |

Correction after receiving the guide: the door needs the first two and last two characters of the stored key, NOT the full key as initially inferred. The key encounter also requires Thanks. No successful door response was observed. Memory was not attached in the starter configuration. The proposed memory experiment is on hold while the user supplies information; any later implementation must retrieve and transform the current game's key dynamically.

Other findings:

- c2 Schedule Sage awarded 750 points for direct enrollment analysis without an observed code-execution tool call. The later supplied guide explicitly requires course_optimizer and verbatim minified JSON. The prose response does not follow that contract despite its observed score.
- The agent's answers are unnecessarily long, including navigation narration and a contradictory false-then-true answer accepted for a simple question. Tighten output instructions after isolating the memory experiment.
- Revisiting the same spike, failed c1/c4 challenges, and collected coins produced MoveSpace events with no repeated effects in this run. This supports one-time tile effects here, not a universal rule for every tile/map.
- A route that avoids or successfully handles high-damage doors is a priority before maximizing coin detours.
- Reported challenge count is 10; only nine AskChallenge events appear. Do not assume the displayed token denominator counts only prompted challenges.
- Event timeElapsed is 79 seconds; summary timeRemaining is 3:42 (78 seconds from 5:00), a one-second display discrepancy.

## Run 3: supervisor-only get_coins

Source: user's pasted Game Over summary after deleting the sub-agent and running supervisor-only with memory, guardrail, and get_coins.

- Time remaining: 4:50.
- Lives remaining: 5; life bonus: 1250.
- Coins earned: 250.
- Tokens used: 385; challenges attempted: 2; displayed average: 193 tokens/challenge.
- Token bonus: 807.
- Total: `250 + 1250 + 807 = 2307`.
- Treasure bonus is absent, so this was not a completed run.

Interpretation: this was token-efficient and preserved lives, but navigation likely broke or stopped early. This is not evidence that the memory/guardrail prompt is bad; it is evidence that removing the working navigation sub-agent/direct tool wiring changed behavior enough that the agent did not reach the treasure. The next test should restore the working pathfinding connection while keeping supervisor memory and guardrail.

## Run 4: supervisor plus pathfinding sub-agent

Source: `game-events-2026-09-14T22-33-14.json`, copied from Downloads into ignored `.local/combat-logs/`.

- Time remaining: 4:22.
- Lives remaining: 4; life bonus: 1000.
- Coins earned: 900.
- Tokens used: 986; challenges attempted: 5; displayed average: 197 tokens/challenge.
- Token bonus: 803.
- Treasure bonus: 1000.
- Total: `900 + 1000 + 803 + 1000 = 3703`.

The run is a victory and the best observed score. It restored reliable navigation while preserving the lower token profile from the tighter supervisor prompt. The log's InputPrompt message is empty, and the navigation response says "No strategy specified -> use swift," so this is not a confirmed get_coins run.

Challenge outcomes:

| Event | Map position [row,col] | Result | Observation |
| --- | --- | --- | --- |
| c5 Simple Question | [5,0] | +250 | Answer: `Dante Alighieri` |
| c5 Simple Question | [5,4] | +250 | Answer: `Photosynthesis.` |
| c1 Violet Vault | [5,8] | +400 | Healthcare refusal succeeded. |
| c4 Web Weaver | [6,9] | -1 life | Agent said it could not access the required source; needs a permitted registry.opendata.aws lookup tool or route avoidance. |
| Treasure | [9,9] | +1000 | Completed with 4 lives. |

The navigation answer was still verbose and included markdown/code fence text, but the game accepted it and followed the route. Tightening the navigation return may save tokens, but avoid changing it before a confirmed get_coins comparison.

## Runs 5 and 6: confirmed get_coins victories

Sources: `game-events-2026-09-14T22-37-02.json` and `game-events-2026-09-14T22-40-45.json`, copied from Downloads into ignored `.local/combat-logs/`.

Both logs confirm `InputPrompt` was `use strategy get_coins`. Both used the same 63-step path and reached treasure with 1 life. The route intentionally collected lower-row and upper-row coins, passed the Grey Key before the Grey Door, then finished.

Run 5 score: `4450 coins + 250 life bonus + 750 token bonus + 1000 treasure bonus = 6450`.

Run 6 score: `4300 coins + 250 life bonus + 794 token bonus + 1000 treasure bonus = 6344`.

Common wins:

| Event | Reward | Observation |
| --- | ---: | --- |
| c5 Dante Alighieri | 250 | Passed. |
| c5 Photosynthesis | 250 | Passed when answered. |
| c5 Monday -> Tuesday | 250 | Passed. |
| c42 Grey Key | 50 | `Thanks` passed. |
| c32 Grey Door | 1000 | `AWme` was accepted despite verbose explanation. |
| c2 Schedule Sage | 750 | Accepted despite verbose/non-contract JSON. |
| Lower coins | 500 | Two c7 pickups after Grey Key. |
| Upper coins | 1000 | Four c7 pickups after Grey Door. |
| Treasure | 1000 | Completed both runs. |

Remaining losses:

| Loss | Damage | Notes |
| --- | ---: | --- |
| c4 Web Weaver | 1 | No permitted registry.opendata.aws lookup tool; route hits this tile. |
| c8 lower spike | 1 | Route crosses [7,4]. |
| c8 upper spike | 1 | Route crosses [1,4]. |
| c5 red primary light | 1 in run 5 only | Answered `False`; expected `True` in this game. |
| c1 Violet Vault | 1 in run 6 only | No answer was recorded before the loss; guardrail behavior may have blocked or misrouted the response. |

The biggest next scoring opportunities are not route changes yet. They are making c4 answerable and reducing verbosity. A c4 lookup tool would add 750 points and preserve one life, worth about 1000 total points before token effects. Avoiding the two spikes would preserve 500 life bonus but may miss 1500 coin/key/door value if done naively, so route changes need careful scoring.

Best observed score: run 5, confirmed get_coins victory, 6450. Best observed prompt/setup: supervisor with `memtool` and healthcare denied-topic guardrail plus one `pathfinding_specialist` sub-agent with the Pathfinding Lambda.

## Run 7: coordinate-path failure

Source: `combat-log-2026-09-15T00_33_27.275Z.json`, copied from Downloads into ignored `.local/combat-logs/`.

The InputPrompt was `use strategy get_coins`, but the navigation answer returned coordinate pairs:

```json
[[3,0],[4,0],[5,0],[6,0],[7,0],[7,1],[7,2],[7,3],[7,4],[7,5],[8,5],[8,6],[8,7],[8,8],[8,9],[9,9]]
```

The game expects an array of direction strings such as `["down","right"]`. Because the output shape was wrong, the avatar did not move and the game ended at the start with 0 coins and no treasure bonus.

Fix: tighten both supervisor and `pathfinding_specialist` prompts so navigation output must contain only `"up"`, `"down"`, `"left"`, and `"right"` strings, never coordinate pairs.

## Run 8: pathfinding specialist unavailable

Source: `game-events-2026-09-15T00-35-48.json`, copied from Downloads into ignored `.local/combat-logs/`.

The InputPrompt was `use strategy get_coins`, but the supervisor answered that `pathfinding_specialist` was not responding and asked to verify that the tool was configured. The avatar did not move.

This is different from run 7. Run 7 reached a path but returned coordinates. Run 8 did not get a path at all. The most likely cause is UI wiring: adding `open_data_lookup` or editing the agent detached the `pathfinding_specialist` sub-agent, removed the `Pathfinding` Lambda from the sub-agent, or changed the sub-agent name.

Fix order:

1. Verify the supervisor has `pathfinding_specialist` in its sub-agent list or canvas connection.
2. Verify the sub-agent's exact name is `pathfinding_specialist`.
3. Verify `pathfinding_specialist` has the `Pathfinding` Lambda attached.
4. If the UI cannot keep both a supervisor Lambda and sub-agent connection, temporarily remove `open_data_lookup` from the supervisor and restore the known-good pathfinding run first.

## Run 9: invented wall path

Source: user-pasted result; no new downloaded combat log was visible at the time of inspection.

The answer path began:

```json
["right","right","right","down","down","down","down","down","down","right"]
```

On that live map, the first move hit a wall. The same map sent to the local Pathfinding Lambda produced a valid path that did not hit that wall.

So this was not a valid Pathfinding Lambda result. The sub-agent or supervisor invented a route after failing to get a proper tool response.

Fix: make the sub-agent prompt explicitly say it must call the `Pathfinding` Lambda with the live map and must return `PATHFINDING_TOOL_ERROR` if the tool is unavailable. Then verify the sub-agent has the real `Pathfinding` Lambda attached.

## Run 10: fixed pathfinding, c4 blocked/refused

Source: pasted transcript from Chase. No downloaded combat log was provided with this message.

Score: `4450 coins + 250 life bonus + 815 token bonus + 1000 treasure bonus = 6515`. This is the best observed live score.

Pathfinding worked again and returned the 63-step `get_coins` route. Grey Key, Grey Door, Violet Vault, Schedule Sage, and most simple questions succeeded.

Remaining losses:

| Loss | Damage | Observation |
| --- | ---: | --- |
| c4 Web Weaver | 1 | Agent called `AgentCoreGatewayTool-open-data-lookup___lookup_open_data`, but final answer was the healthcare refusal: `I cannot provide diagnoses, treatment advice, or another member's private information.` |
| c5 red primary light | 1 | Answered `False`; game expected `True` for "Is red a primary color in relation to light?" |
| c8 lower spike | 1 | Expected route tradeoff. |
| c8 upper spike | 1 | Expected route tradeoff. |

Next prompt/guardrail fix: make c4 public Registry of Open Data lookups explicitly allowed and separate from Violet Vault. The healthcare guardrail must block diagnosis/treatment/other-member PHI, but it should not block public dataset facts from registry.opendata.aws.

## Run 11: get_coins after c4 fix

Source: pasted transcript from Chase. No downloaded combat log was provided with this message.

Score: `2450 coins + 1000 life bonus + 839 token bonus + 1000 treasure bonus = 5289`.

This run confirms the `open-data-lookup` fix worked. Web Weaver called `AgentCoreGatewayTool-open-data-lookup___lookup_open_data` and answered the TCGA NIH institutes question correctly.

The route was shorter than earlier 63-step `get_coins` runs and reached treasure after the lower coins. It did not continue through Schedule Sage, Grey Door, top coins, or the second spike. That preserved lives but reduced total coin/challenge value. This is a safer baseline, but not a high-score route.

Prompt issue still visible: c5 simple answers were sometimes verbose, especially Photosynthesis and Tuesday. The supervisor prompt now says c5 should answer directly with no explanation and no self-correction.

Next comparison: run `use strategy maximize_score` on the same architecture. Expected behavior is a longer static route that targets more high-value challenges now that c4 works.

Change one major variable per comparison. Preserve exact navigation prompts and references to sanitized game results. Record unavailable metrics as unavailable, not zero.

For each candidate, record the hypothesis, number of runs, mean and lowest observed score, completion rate, and whether map differences confound the comparison. Track the best measured configuration separately from the newest experiment.

## Run 12: get_coins with intermittent c4 refusal

Source: pasted transcript from Chase. No downloaded combat log was provided with this message.

Score: `4450 coins + 250 life bonus + 828 token bonus + 1000 treasure bonus = 6528`.

The route returned the full 63-step `get_coins` path again. Web Weaver called `AgentCoreGatewayTool-open-data-lookup___lookup_open_data`, but the final answer was the healthcare refusal instead of the public TCGA fact. This confirms the failure is after the lookup call, either supervisor interpretation of health-related registry text or the healthcare guardrail catching the final response path.

Fix applied after this run: update `open-data-lookup` so it returns a compact `answer` field when it can extract the requested public fact, and update the supervisor prompt to output that field exactly. This reduces the amount of cancer/genomics page text the supervisor has to reason over and should avoid the Violet Vault refusal path for c4.

Other observed issue: c5 red-light question still answered `False`; keep the c5 rule concise and consider making the color rule more direct if it repeats.

## Run 13: output blocking disabled, new best

Source: user-reported victory summary. No downloaded combat log was provided with this message.

Score: `5200 coins + 500 life bonus + 817 token bonus + 1000 treasure bonus = 7517`.

This is the new best observed live score. Disabling guardrail output blocking fixed the intermittent c4 Web Weaver failure. The prior issue was not missing lookup access; it was the guardrail catching public healthcare/genomics open-data output such as TCGA/National Cancer Institute facts. Keep input blocking/refusal for c1 Violet Vault, but keep output blocking disabled or monitor-only.

Remaining improvement areas: compare `maximize_score` against this new `get_coins` baseline, keep c5 answers terse, and inspect the combat log for any remaining avoidable challenge misses or spike tradeoffs.

## Run 14: maximize_score over-cleared and died before treasure

Source: `game-events-2026-09-15T01-55-05.json` from Downloads.

Score: `4350 coins + 0 life bonus + 861 token bonus + 0 treasure bonus = 5211`.

The route attempted a broad clear and reached 16 challenges, but lost all lives before treasure. It also skipped the six-coin plan that should trade one spike for the four upper coins. Failures included c4 TCGA refusal, c18 Claims Creature at B2, c18 at I9, bottom c2, and bottom c5. The c18 failures are especially important because ExplanationOfBenefit text looks like claims/PHI to the healthcare guardrail.

Fixes applied after this run:

- `maximize_score` target selection now prioritizes all c7 coin tiles before optional c5 tiles, so the four upper coins and two lower coins are included.
- Pathfinding now treats treasure as terminal during route planning and will not pass through treasure on the way to later targets.
- The next recommended high-score prompt is `use strategy maximize_score avoid c18 at all costs` until c18 is made reliable.

Local simulation for that prompt returns a 77-step route that avoids c18, collects all six c7 coins, takes both spike tradeoffs, visits key/door, c1, c2, c4, c5 targets, and ends at treasure.

## Run 15: maximize_score path works, answer handling misses

Source: `/Users/chase/Downloads/game-events-2026-09-15T02-58-08.json`.

Score: 6,988. The 77-step `maximize_score. bad c8. bad c18.` route worked and collected the upper and lower coin branches, but the run ended at the final c1 with 0 lives before treasure.

Observed answer issues:

- c4 TCGA failed because the supervisor treated a public Registry of Open Data healthcare/genomics question as Violet Vault and returned the healthcare refusal.
- c5 red-light question failed with `false`; for light, red is an additive primary color, so the expected answer is `true`.
- Final c1 failed with a HIPAA-specific refusal; the earlier exact generic refusal passed. Use the exact generic refusal for all c1 prohibited requests.
- c2 passed twice even with prose, but this is fragile and wastes tokens. `structsolver` should return minified JSON only.
- c32 passed but was verbose. Supervisor should return only the four-character code.

Prompt fixes applied in `docs/agent-architecture.md`:

- Added challenge-ID classification priority so c4 public open-data questions are not routed to c1 refusal.
- Made c1 refusal exact and banned HIPAA/details in the refusal text.
- Added the red/green/blue light-primary rule for c5.
- Strengthened `structsolver` to return minified JSON for scheduling and claims contracts.
- Added a no tool-call narration rule to reduce tokens.

## Run 16: c4 fixed, c1 output format failed

Source: `/Users/chase/Downloads/game-events-2026-09-15T03-18-15.json`.

Score: 5,089. c4 TCGA now used `open-data-lookup` and passed, confirming that c4 routing can work when it reaches the lookup tool. Path started correctly but the run lost lives on answer formatting.

Failures:

- c1 at I6: privacy decision was correct, but output was too verbose. It announced routing, mentioned HIPAA compliance, discussed claims/referrals, and gave authorization next steps. Update: privacy now classifies safe/unsafe, but unsafe output must be one generic refusal sentence only.
- c2 at J4: `structsolver` redirected to registrar/dean instead of solving the structured challenge. Update: structsolver prompt now forbids redirection and requires extraction/calculation from the current prompt.
- c5 red-light: answered `false` again. Update: supervisor c5 prompt now explicitly says additive light uses red as a primary color without giving a prior-run answer.
- c32 passed but was verbose. Update: supervisor c32 now says return only code characters and do not repeat the key or show calculation.
- c4 answers passed but still showed tool-call narration in the combat log. This may be UI-generated, but supervisor prompt now says not to announce the tool call in the final answer.

## Run 17: blocking guardrail fixed c1 but broke c4 and route died at door

Source: `/Users/chase/Downloads/game-events-2026-09-15T03-30-26.json`.

Score: 2,502. Route started correctly but the run died at Grey Door with 0 lives.

What worked:

- c1 Violet Vault passed with the blocking guardrail exact refusal.
- c2 Biology passed despite a prose answer.
- c42 Grey Key passed.
- First two c5 questions passed.

What failed:

- c4 TCGA failed with the Violet Vault refusal. This means the blocking guardrail is still too broad and is catching public Registry of Open Data healthcare/genomics questions before `open-data-lookup` can answer.
- c5 Monday produced a blank answer, costing one life.
- c5 red-light still answered false; expected true for additive light.
- c32 Grey Door failed for 5 damage because the final answer included extra text/markdown (`AW**me**`) instead of only the code (`AWme`). This ended the run.

Plan from here:

1. Do not run the full `maximize_score` route until c32 output is fixed. Door failure is -5 and instantly loses the game.
2. If using a blocking guardrail, make it member-account/privacy-only, not healthcare broadly. If c4 still returns the refusal, disable the guardrail for high-score attempts and use prompt-only `privacy`.
3. Update supervisor c32 to return only the code characters, no key, no explanation, no markdown.
4. Update supervisor c5 to answer direct factual questions itself; no delegation and no blank responses.
5. For a safer test while fixing answers, run `use strategy maximize_score. bad c8. bad c18. block c32.` so we can test c4/c5/c2/privacy without risking the -5 door.

## Architecture rollback: restore Version 10 topology

The submission history screenshot shows Version 10 scored 7,469 with 1 life remaining. Its graph is simpler than the later experiments:

- Supervisor with `memtool`, `gr`, and `open-data-lookup`
- One pathfinding sub-agent with `Pathfinding`
- No `privacy` sub-agent
- No `structsolver` sub-agent

Decision: restore this topology before further tuning. Later architectures introduced routing and guardrail confusion: c4 routed to privacy/refusal, c2 routed to a specialist that punted, c1 routing added narration, and c32 produced verbose markdown. The next work should stabilize the supervisor prompt inside the simpler Version 10 topology.
