# Experiment log

Three runs recorded: two user-reported summaries and one inspected combat log. Never substitute estimates for observed scores.

| Run/time | Map/seed | Strategy | Code/prompt/config version | Coins | Final score | Lives | Duration | Avg tokens/challenge | Completed? | Failures/notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 / 2026-09-14 | Not captured | `swift` (prepared UI prompt; execution log not yet inspected) | LeagueStarter; original pathfinding Lambda | 500 | 2895 | 3 | 39s inferred from 5:00 start and 4:21 remaining | 355 displayed | Victory | 1777 tokens; 5 challenges attempted; loss causes unknown |
| 2 / 2026-09-14 | Full map not included; start [3,0] | `get_coins` confirmed by InputPrompt | LeagueStarter setup; exact runtime configuration absent from log | 2250 | 2953 | 0 | 79s event time | 297 | Defeat | 2968 tokens; 10 reported challenges; fatal c32 door |
| 3 / 2026-09-14 | Not captured | `get_coins` | Supervisor-only; `memtool`; healthcare denied-topic guardrail; no sub-agent | 250 | 2307 | 5 | 10s inferred from 5:00 start and 4:50 remaining | 193 displayed | Game Over | 385 tokens; 2 challenges attempted; no treasure bonus; likely navigation/wiring failure |

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

Best observed score: get_coins 2953 (defeat). Best observed completed run: swift 2895. One run each is insufficient to establish expected performance. Best token efficiency: run 3, but it did not finish.

Change one major variable per comparison. Preserve exact navigation prompts and references to sanitized game results. Record unavailable metrics as unavailable, not zero.

For each candidate, record the hypothesis, number of runs, mean and lowest observed score, completion rate, and whether map differences confound the comparison. Track the best measured configuration separately from the newest experiment.
