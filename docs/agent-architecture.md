# Agent architecture

This is the recommended first UI setup after the baseline runs. The goal is to fix the preventable losses before adding more infrastructure.

Current UI setup:

- one memory tool
- one guardrail
- the existing pathfinding Lambda
- no sub-agents in the latest test

The latest supervisor-only test was very token-efficient but did not reach treasure. Keep the supervisor as the shared memory/guardrail owner, but restore whichever pathfinding connection makes the agent reliably call the existing Lambda and return the complete path.

## Supervisor

Recommended UI values:

| Field | Value |
| --- | --- |
| Name | `LeagueStarter` |
| Model | `Claude Haiku 4.5` |
| Memory | `memtool` |
| Guardrail | healthcare guardrail described below |
| Lambda tools | none unless the UI requires a direct Lambda |
| Sub-agents | `pathfinding_specialist` |

This is the simplest target architecture: supervisor owns memory and guardrail; navigation uses the known-working Pathfinding Lambda wiring.

## Sub-agent setup

Create one sub-agent for navigation.

Recommended UI values:

| Field | Value |
| --- | --- |
| Name | `pathfinding_specialist` |
| Model | `Claude Haiku 4.5` |
| Memory | none |
| Guardrail | none |
| Lambda tools | `Pathfinding` |
| Connected to supervisor | yes |

The sub-agent should only do navigation. Do not give it the memory tool or healthcare guardrail. Keeping memory on the supervisor matters because the supervisor sees both Grey Key and Grey Door challenge text.

Paste this into the sub-agent prompt:

```text
You are the navigation specialist. Call the Pathfinding tool with the complete game_map, start_pos, goal_pos, and strategy exactly as provided. Use swift if strategy is missing.

Read the tool response. If the response body is a JSON string, parse it. Return only the path array, for example ["right","up"]. Do not explain the path. Do not change the map. Do not invent moves.
```

Expected connection:

```text
LeagueStarter supervisor -> pathfinding_specialist sub-agent -> Pathfinding Lambda
```

If the UI offers a visual canvas, connect the supervisor node to `pathfinding_specialist`. If it offers a sub-agent selector, add `pathfinding_specialist` to the supervisor's sub-agents.

## Supervisor prompt

Paste this into the supervisor prompt:

```text
You are the AI League supervisor. Keep answers short and exact.

Navigation: call pathfinding_specialist with the complete map, start position, goal position, and requested strategy exactly as supplied. Use swift if no strategy is requested. Return only the path JSON array when navigation is requested.

c42 Grey Key: save the key in memory with its color and number. Reply exactly Thanks.

c32 Grey Door: retrieve the matching key from memory. The door code is the first two characters plus the last two characters of the key, preserving case. Return only that code.

c1 Violet Vault: for diagnosis, symptom interpretation, treatment or medication recommendations, or another member's PHI/PII, politely refuse in one short sentence. Do not reveal or infer protected information.

c2 Schedule Sage: extract all course sections. Flag enrolled/capacity below 0.50. Consolidate only same-course flagged sections with different time slots when combined enrollment fits the kept section capacity; keep the higher-enrollment section. Return only minified JSON with FlaggedSections, Consolidations, and NoAction.

c18 Claims Creature: calculate from the supplied EOB. TotalAllowed is eligible amounts for non-denied lines only. MemberResponsibility is eligible minus benefit for non-denied lines and submitted amount for denied lines. DeniedLines contains code and carc. Return only minified JSON with TotalAllowed, MemberResponsibility, and DeniedLines. Money uses two decimals.

c4 Web Weaver: use only a permitted registry.opendata.aws lookup tool if available. Return only the requested fact. If no permitted lookup tool is available, answer that you cannot access the required source.

c5 Simple Question: answer directly with the shortest correct answer.

Never invent tool results. Never hardcode paths, maps, keys, or challenge answers. Never add markdown, code fences, or explanations unless the challenge explicitly asks for them.
```

## Memory tool

Use the existing AgentCore memory resource:

| Field | Value |
| --- | --- |
| UI selection | `memtool` |
| Memory id | `memtool-2g9JjYEzxL` |
| Status | `ACTIVE` |
| Expiration | 30 days |
| Strategies | none observed |

Memory behavior needed for the game:

- Store Grey Key values by color and number.
- Preserve exact case.
- For c42, the answer must be exactly `Thanks`.
- For c32, derive the door code from the stored current key: first two characters plus last two characters.
- Do not store fixed answers from old games.

Example memory intent:

```text
Store: grey key 1 = AWSisAwesome
Door answer: AWme
```

That example explains the transform only. Do not paste `AWSisAwesome` or `AWme` into the live prompt as a hardcoded answer.

## Guardrail

Create or update the selected guardrail for Violet Vault. The current discovered guardrail was named `dr`, but its existing investment-advice topic does not match the healthcare challenge. Use a healthcare-specific guardrail instead.

Recommended UI configuration:

| Field | Value |
| --- | --- |
| Name | `healthcare-member-services` |
| Input action | Block / refuse |
| Output action | Block / refuse |
| Scope | diagnosis, treatment advice, medication advice, other-member PHI/PII |
| Safe answer style | one short refusal sentence |

The UI only exposes denied topics, so do not look for an "allowed topics" field. Put the allowed member-service topics in the supervisor prompt by implication: the agent may answer ordinary benefits, plan, provider-directory, and appointment-scheduling questions, but the guardrail denies medical advice and privacy violations.

Denied topic text:

```text
The agent must not diagnose or interpret symptoms, recommend treatments, medications, or dosages, reveal another member's information, or disclose another member's PHI or PII, including SSNs, member IDs, dates of birth, and claims details.
```

Blocked input message:

```text
I cannot provide diagnoses, treatment advice, or another member's private information.
```

Blocked output message:

```text
I cannot provide diagnoses, treatment advice, or another member's private information.
```

Allowed member-services topics for the supervisor prompt, not the guardrail UI:

- general benefits questions
- plan information
- provider directories
- appointment scheduling

Do not make the guardrail so broad that it blocks every healthcare-related question. Violet Vault wants refusal for prohibited medical or privacy requests, not refusal for ordinary plan support.

## Lambda tool

Use the existing pathfinding Lambda first:

| Field | Value |
| --- | --- |
| Lambda name | `AgentCoreGatewayTool-Pathfinding` |
| UI tool name | `Pathfinding` |
| Handler | `pathfinding_lambda.lambda_handler` in AWS; local source is `src/pathfinding/handler.py` |
| Runtime | Python 3.11 |
| Region | `us-east-1` |
| Strategies | `swift`, `get_coins` |

Tool request shape:

```json
{
  "game_map": [["start","normal","treasure"]],
  "start_pos": [0, 0],
  "goal_pos": [0, 2],
  "strategy": "get_coins"
}
```

Tool response shape:

```json
{"path":["right","right"],"steps":2,"start_position":[0,0]}
```

The current Lambda is a baseline. It can collect coins, but it does not avoid spikes or high-risk challenges intelligently yet.

### Current Lambda code

The local copy is [src/pathfinding/handler.py](/Users/chase/Desktop/code/boozallenai/src/pathfinding/handler.py:1).

```python
import json
import re
from collections import deque

CELL_POINTS = {"c7": 250}
COLLECTIBLE_COINS = {"c7"}
DIRECTIONS = [(-1, 0, "up"), (1, 0, "down"), (0, -1, "left"), (0, 1, "right")]


def _parse_start(pos):
    """Parse start position from any format Nova might send."""
    try:
        if isinstance(pos, (list, tuple)):
            if len(pos) == 1:
                return _parse_start(pos[0])
            if len(pos) >= 2:
                a = re.sub(r'[^A-Za-z0-9]', '', str(pos[0]))
                b = re.sub(r'[^A-Za-z0-9]', '', str(pos[1]))
                if a.isalpha():
                    return (int(b) - 1, ord(a.upper()) - ord('A'))
                return (int(a), int(b))
        s = re.sub(r'[^A-Za-z0-9]', '', str(pos))
        m = re.match(r'([A-Za-z])(\d+)', s)
        if m:
            return (int(m.group(2)) - 1, ord(m.group(1).upper()) - ord('A'))
        nums = re.findall(r'\d+', s)
        if len(nums) >= 2:
            return (int(nums[0]), int(nums[1]))
    except (ValueError, TypeError, IndexError):
        pass
    return (0, 0)


def lambda_handler(event, context):
    """
    AWS Lambda function for pathfinding using Swift path strategy by default
    Handles both API Gateway format and direct AgentCore Gateway format

    Strategies:
      swift     - BFS shortest path to treasure (default)
      get_coins - Greedily collect c7 coins on the way to treasure
    """
    try:
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        print(f"DEBUG: Received event: {body}")
        game_map = body.get('game_map', [])

        if game_map:
            max_cols = max(len(row) for row in game_map)
            game_map = [row + ['normal'] * (max_cols - len(row)) for row in game_map]

        map_config = body.get('map_config', {})
        player_start = map_config.get('playerStart') or body.get('playerStart') or {}
        if isinstance(player_start, str):
            start_pos = _parse_start(player_start)
        elif isinstance(player_start, dict) and player_start:
            start_pos = (player_start.get('row', 0), player_start.get('col', 0))
        else:
            raw = body.get('start_pos') or body.get('start') or body.get('position') or [0, 0]
            start_pos = _parse_start(raw)

        if game_map and (start_pos[0] >= len(game_map) or start_pos[1] >= len(game_map[0])):
            start_pos = (0, 0)

        strategy = str(body.get('strategy', 'swift')).lower().strip()
        if 'coin' in strategy:
            strategy = 'get_coins'
        elif 'swift' in strategy or 'fast' in strategy or 'quick' in strategy:
            strategy = 'swift'
        else:
            strategy = 'swift'

        if not game_map:
            return _err(400, 'Missing game_map')

        rows, cols = len(game_map), len(game_map[0])
        treasure = None
        for r in range(rows):
            for c in range(cols):
                if game_map[r][c] == 'treasure':
                    treasure = (r, c)
                    break
            if treasure:
                break

        if not treasure:
            return _err(400, 'No treasure found on map')

        if strategy == 'get_coins':
            path = get_coins_path(game_map, rows, cols, start_pos, treasure)
        else:
            path = swift_path(game_map, rows, cols, start_pos, treasure)

        result = {'path': path, 'steps': len(path), 'start_position': list(start_pos)}
        print(f"RESULT: strategy={strategy} steps={len(path)} start={list(start_pos)}")
        return {'statusCode': 200, 'body': json.dumps(result)}

    except Exception as e:
        print(f"ERROR: {e}")
        return _err(500, str(e))


def _err(code, msg):
    return {'statusCode': code, 'body': json.dumps({'error': msg})}


def _bfs(game_map, rows, cols, start, goal):
    """BFS shortest path between two points."""
    queue = deque([(start[0], start[1], [])])
    visited = {(start[0], start[1])}
    while queue:
        r, c, path = queue.popleft()
        if (r, c) == goal:
            return path
        for dr, dc, move in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and game_map[nr][nc] != 'wall' and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append((nr, nc, path + [move]))
    return None


def swift_path(game_map, rows, cols, start, treasure):
    """BFS shortest path to treasure."""
    return _bfs(game_map, rows, cols, start, treasure) or []


def get_coins_path(game_map, rows, cols, start, treasure):
    """Greedily BFS to best coins-per-step c7 cell, then BFS to treasure."""
    board = [row[:] for row in game_map]
    r, c = start
    full_path = []

    for _ in range(50):
        queue = deque([(r, c, [])])
        visited = {(r, c)}
        targets = []
        while queue:
            cr, cc, p = queue.popleft()
            if board[cr][cc] in COLLECTIBLE_COINS and (cr, cc) != (r, c):
                dist = max(len(p), 1)
                targets.append((dist, p, cr, cc))
            for dr, dc, move in DIRECTIONS:
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != 'wall' and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    queue.append((nr, nc, p + [move]))

        if not targets:
            break
        targets.sort()
        _, path_to, r, c = targets[0]
        full_path.extend(path_to)
        board[r][c] = 'normal'

    path_end = _bfs(board, rows, cols, (r, c), treasure)
    if path_end is not None:
        full_path.extend(path_end)
        return full_path
    return swift_path(game_map, rows, cols, start, treasure)
```

## First test

Use this navigation prompt:

```text
use strategy get_coins
```

Pass signs:

- c42 replies exactly `Thanks`.
- c32 returns the transformed key code instead of explaining Gray code.
- c5 answers are very short.
- The run finishes alive or loses fewer lives than the previous `get_coins` run.

Save the combat log after the run and record the score in [experiments.md](/Users/chase/Desktop/code/boozallenai/docs/experiments.md:1).
