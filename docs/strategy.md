# Strategy

Status: source inspected, two baseline runs recorded, and event-specific rules captured. Implementation is paused while the user supplies more information; the next experiment has not been chosen. Custom route strategies are not implemented.

## Corrections from the event guide

- Grey Door needs the first two plus last two key characters, not the whole key. Grey Key requires Thanks and memory.
- Schedule Sage explicitly requires course_optimizer and minified JSON despite the baseline prose answer being accepted once.
- Claims Creature needs claim calculations and precise JSON money formatting.
- Violet Vault requires healthcare-specific guardrails; the existing investment-advice policy is insufficient.
- Web Weaver requires fetching the relevant permitted dataset page. Hardcoded answers and other external sites are prohibited.
- Compute routes dynamically. Do not embed navigation paths, map JSON, or fixed challenge answers in deployed tools.

These requirements inform the next discussion; they are not yet applied to the running agent.

## Objective

Maximize measured final score: collected coins plus the actual life and token bonuses. Initially prioritize reliable rewards and finishing alive. Once the scoring formula is known, compare risky detours against their expected score benefit rather than assuming every challenge is worth visiting.

Use this planning model until exact scoring is available:

```text
expected route value = expected collected coins
                    + expected completion/life bonus
                    + expected token bonus
```

Track time and survival separately as constraints. Do not invent bonus weights. Expected damage alone is insufficient: a route with acceptable average damage can still have an unacceptable chance of death.

## Improvement order

1. Capture the game guide and fill the challenge inventory. Download the provided Lambda and inspect its real request/response contract.
2. Record baseline runs with `swift` and `get_coins`, including final score, remaining lives, elapsed time, tokens, and failures.
3. Master high-reward, inexpensive challenges with deterministic tools or the required configuration. Verify actual game success before labeling a challenge mastered.
4. Implement a route that targets coins and mastered challenges, avoids spikes when feasible, and reserves enough time and health to reach treasure.
5. Tighten prompts to call the correct tool once, use its result faithfully, and satisfy the required answer format.
6. Tune memory and guardrails only for documented challenge requirements. Evaluate model customization after establishing a strong baseline and reading its rules.
7. Keep the strongest measured configuration available for rollback. Test the final candidate on varied maps, including sparse rewards, forced obstacles, and low-health situations.

## Strategy menu

Only `swift` and `get_coins` are confirmed built-ins. Other names below are proposed additions and must not be used until implemented and verified.

| Strategy | Purpose |
| --- | --- |
| `swift` | Baseline shortest route to treasure. |
| `get_coins` | Baseline coin collection. |
| `safe_loot` | Coins plus mastered challenges, with spike avoidance and a survival reserve. First implementation target. |
| `high_value` | Favor high expected reward per added travel and solving time. |
| `full_clear` | Visit all profitable challenges when success and completion are reliable. |
| `survival` | Favor a feasible low-damage exit when health or time is limited. |

## Pathfinding design

- Preserve the provided event schema, output schema, and built-in strategy behavior.
- Parse actual terrain and challenge IDs; do not assume `c1`, `c2`, or `c3` means a particular item type.
- Treat treasure as a terminal tile. Paths between other targets must not pass through it and accidentally end the game.
- Calculate reachable routes using the game's movement rules. Compare travel distance and damage; retain alternatives when a longer route preserves lives.
- Select reward targets using measured success rates, coin values, damage outcomes, and solve times. Count collectible rewards only as permitted by the revisit rules.
- For small target sets, consider subset search; for larger maps, use a bounded heuristic with route insertion and local improvements. Choose only after seeing map size and Lambda limits.
- Include the final leg to treasure in every candidate's health and time budget. Reserve time for measured tool/agent overhead.
- If runtime replanning is supported, update the route after a failure or changed health/time. Otherwise build the reserve into the initial route.
- Return explicit errors for invalid or unreachable maps according to the existing contract. Never fabricate a traversable route.

Meaningful tests after implementation: terminal treasure, unreachable rewards, spike detours, no duplicate reward credit, health exhaustion, time budget, exact map IDs, and compatibility with captured Lambda events.

## Prompt approach

For an initial comparison, use the confirmed navigation syntax:

```text
use strategy get_coins
```

After `safe_loot` is implemented, test `use strategy safe_loot`. Add only parameters the actual tool supports.

Challenge prompt draft, to adapt after inspecting the agent and tool schemas:

```text
Identify the challenge and its required answer format. Use the matching
available tool when needed, passing the exact provided inputs and mapId.
Use the tool result to produce the required answer concisely. Do not invent
tool results. Retry only when the error is recoverable and inputs can be corrected.
```

Keep exact formatting instructions even if they cost tokens. Optimize token use after correctness; measure total average tokens per challenge, including retries and tool responses where counted.

## Decision discipline

Compare repeated runs on the same map when possible. If maps vary, record their identities and avoid attributing a favorable map to a code improvement. Judge final score, completion rate, and score variability together. Use observed results to choose a reliable competition configuration; retain speculative strategies for separate experiments.
