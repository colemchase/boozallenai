# Game rules

Sources: Workshop Studio “Game Rules” and “Game Hints,” plus the AI League home-page Rules, Tools & Strategy, Bonuses, and Challenges tabs, supplied by Chase on September 14, 2026. See challenges.md for event-specific requirements. Linked contest terms have not yet been reviewed.

## Confirmed mechanics

- An AWS Agent adventurer traverses a dungeon and seeks treasure. Collect as many coins as possible within the available time.
- The adventure ends when time runs out, treasure is reached, or all lives are lost.
- Start with 5 lives. Treasure awards 1000 points; completion awards 250 points per remaining life.
- Token bonus: `1000 - (total tokens used / challenges visited)`. Rounding and a possible floor are unspecified.
- Challenges, obstacles, and bonuses may award coins, remove lives, or obstruct movement.
- Map items have identifiers `c1` through `cN`. Use the exact `mapId` when referring to items in tools or navigation.
- Incorrect challenge answers and specific obstacles can cost lives.
- Challenges require appropriate configuration, prompts, or Lambda tools to solve or maximize their reward.
- Challenge details are available on the game's home page and through the `game_guide` info button.

## Navigation

The provided pathfinding Lambda defaults to `swift`, the fastest route to treasure. It also supports `get_coins`, which seeks all coins on the screen. These are starting strategies; the workshop instructs participants to improve the function.

Before **Submit & Play**, the navigation prompt can select a strategy:

```text
use strategy get_coins
```

Workshop hints suggest supporting multiple strategies: visit all challenges, visit mastered challenge IDs, avoid spikes, optimize time, preserve health, or prioritize valuable or fast challenges. These suggestions do not establish that such strategies already exist in the Lambda.

## Tool restriction

**Lambda tools must not call external models. The workshop explicitly says doing so results in disqualification.** Use deterministic code for tool computations. Do not introduce model calls through a proxy or another service. Workshop-provided agent/model customization is a separate feature; capture its specific rules before using it.

## Other supplied hints

The game home page lists additional disqualification reasons: hardcoding navigation paths, storing map JSON within the pathfinder, hardcoding answers, and calling external sites not defined in the challenge. Compute routes and answers from current runtime inputs. Keep test fixtures and observed answers out of deployed runtime lookup data. The original demo includes map JSON in its docstring; remove that example from a future competition version to avoid ambiguity with the stated prohibition. Code is unchanged while the user supplies rules.

Web Weaver specifically permits dataset pages at registry.opendata.aws. Other URLs appearing as data identifiers (for example EOB coding-system URLs) are not instructions to fetch them.

- Read the guardrail challenge rules before configuring filters. Excessively high settings may reject all requests.
- Correct tools, memory, and guardrails still need prompts that select and use them efficiently.
- Generative AI may be used to help write Lambda tool code.

## Details still unknown

- Score rounding, bonus floors/caps, and definition of challenges visited.
- Unspecified edge cases in the supplied challenge contracts; see challenges.md.
- General movement rules, map variation, and universal revisit/effect-repeat rules.
- Scoring at timeout and whether the observed 5-minute budget applies to every mode. Run 2 retained earned coins and a token bonus on death, but no life/treasure bonus.
- Whether the path is fixed at start or can be replanned during play.
- Finale rules, submission limits, and leaderboard aggregation/tie-breaking.

Do not infer these values from the workshop's illustrative IDs or navigation examples.
