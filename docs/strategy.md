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

The current Pathfinding Lambda supports these strategy names:

| Strategy | Purpose |
| --- | --- |
| `swift` | Baseline shortest route to treasure. |
| `get_coins` | Baseline coin collection. |
| `maximize_score` | Dynamic route search over the live map. It tries to maximize tile reward plus life and treasure bonuses while staying alive. |

These are future strategy ideas, not implemented names yet:

| Future strategy | Purpose |
| --- | --- |
| `safe_loot` | Coins plus mastered challenges, with a larger survival reserve. |
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

## Current map spike behavior

The confirmed `get_coins` route hits E8 because the current Lambda greedily targets the nearest c7 coin and treats c8 spike tiles as ordinary walkable cells. On the current board, the lower c7 pair at C8/D8 sits behind E8 when approached from the Grey Key side:

```text
F8 Grey Key -> E8 spike -> D8 coin -> C8 coin
```

The game charged the E8 spike once even though the movement path crossed it twice. That local trade is still positive on the current scoring model: two coins are worth 500 and one lost life bonus is worth 250. The real problem is survival margin: the same route also hits the upper E2 spike and c4 Web Weaver, leaving only one life.

There is a longer no-E8 approach to the lower coins through the bottom-left corridor, but it traverses additional challenge tiles such as c18, c1, c2, and c5. That route may be better only after those challenges are reliable. The next pathfinding improvement should add a risk-aware strategy rather than blindly avoiding all spikes.

Do not hardcode this map, E8, E2, or the current move list. A compliant strategy should:

- Read the live `game_map` supplied in the Lambda event.
- Load tile behavior from rule metadata, such as `c7 = coin`, `c8 = spike`, `c42 = key`, and `c32 = door`.
- Generate candidate target sets dynamically from cells present on the map.
- Score each candidate route by expected reward, expected damage, remaining life reserve, and final treasure reachability.
- Return a route computed from the current map only.

The current `maximize_score` implementation follows this pattern. The Lambda can receive either structured `game_map` input or the full navigation prompt containing the grid. It builds a Python grid data structure, merges default rule metadata with prompt-level avoid/damage hints such as `bad c18` or `bad c8`, evaluates candidate reward targets from the live map, tracks whether the Grey Key has been collected before the Grey Door, requires a final path to treasure, and falls back to `get_coins` if no scoring route is found.

## Local optimizer findings

Local route optimization is useful, but it only tests navigation and assumed tile outcomes. It does not prove the live agent will answer challenges correctly or keep token usage low.

On the September 14 map, using observed rewards and conservative assumptions that Web Weaver and Claims still fail, a local step-by-step search found a higher theoretical route than current `get_coins`:

- Current best live `get_coins`: 6450.
- Local model with c4/c18 unsolved: about 7600 before token effects, if c1/c2/c5/key/door are answered correctly.
- Local model with c4 solved by an Open Data lookup tool: about 9350 before token effects.
- Local model with both c4 and c18 solved: about 11100 before token effects.

The model still takes two spikes where the reward behind them is worth it. The improvement comes from visiting additional high-value bottom-left rewards before treasure, not from blindly avoiding c8.

Treat these as targets for implementation and testing, not official scores. The live game can differ because of model answer variance, token bonus, time, and any challenge failures.

## Prompt approach

For an initial comparison, use the confirmed navigation syntax:

```text
use strategy get_coins
```

After the updated Lambda is deployed, test the higher-score option:

```text
use strategy maximize_score
```

Until c18 Claims Creature is reliable, prefer:

```text
use strategy maximize_score. bad c8. bad c18.
```

This still lets the pathfinder target coin clusters and high-value non-claims challenges while avoiding the challenge type most likely to be blocked by the healthcare guardrail.

Use prompt-level bad IDs for soft one-life costs. For example:

```text
use strategy maximize_score and bad c8
```

That treats `c8` as a one-life soft danger and removes any positive reward for that tile. If you want to remove all `c8` tiles from the graph, use:

```text
use strategy maximize_score and block c8
```

Keep `use strategy get_coins` as the rollback baseline.

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
