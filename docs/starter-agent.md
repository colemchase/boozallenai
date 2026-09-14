# LeagueStarter

Configured through the AI League game UI on September 14, 2026. Both supervisor and sub-agent saves returned success. The user subsequently reported a victory with 2895 points, 3 lives, and 1777 tokens; see the [experiment log](experiments.md). Execution details have not yet been verified against the combat log.

## Supervisor

Name: `LeagueStarter`. Model: `Claude Haiku 4.5`. Memory, guardrail, and direct Lambda selections were empty. Uses the existing specialist connection.

```text
You are a dungeon game agent. For navigation, delegate to pathfinding_specialist. Pass the complete map, start position, and requested strategy exactly as supplied. Do not rename cells, shorten the map, or invent moves. If no strategy is requested, use swift. Return only the specialist's path as a JSON array of quoted directions, with no explanation. Answer simple factual and arithmetic challenges directly and concisely in the requested format. Never invent tool results.
```

## Specialist

Name: `pathfinding_specialist` (renamed from `Pathfinding`). Model: `Claude Haiku 4.5`. Existing attached Lambda tool: `Pathfinding`.

```text
You are a pathfinding tool caller. Call the available find_path tool with the complete game_map and start_pos exactly as provided. Pass the requested strategy; use swift if none is specified. Never shorten or change the map. Read the tool response; if its body is a JSON string, parse it. On success return ONLY its path array as JSON, such as ["right","up"]. Do not add commentary or invent moves. If the tool returns an error, report that error concisely.
```

## First test

The game page is open at https://aileague.aws.dev/agentic/play with navigation prompt:

```text
use strategy swift
```

Click **Test your agent**. Capture final score, remaining lives, tokens, and combat log. Then compare `use strategy get_coins`. No test or leaderboard submission was started during this setup.

The existing Lambda supports both strategies. Its current coin strategy can traverse spikes and can pass through treasure prematurely; it is a comparison baseline, not an optimized strategy.

## Earlier observed result

Submission history already showed a completed run at September 14, 2026, 4:19:45 PM (UI display time), agent version `50a8c741-3725-4701-a54c-95f595054e99`: score 2827, tokens 2117, lives remaining 3, lives lost 2. Its map, prompt, and settings were not inspected. This result predates LeagueStarter and must not be attributed to it.
