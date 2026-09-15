import heapq
import json
import re
from collections import deque

DEFAULT_RULES = {
    "walls": {"wall"},
    "rewards": {
        "c7": 250,
        "c42": 50,
        "c32": 1000,
        "c5": 250,
        "c2": 750,
        "c1": 400,
        "c4": 750,
        "c18": 750,
    },
    "damage": {},
    "locked_damage": {"c32": 5},
    "requires": {"c32": "c42"},
    "items": {"c42"},
    "avoid": set(),
    "starting_lives": 5,
    "life_bonus": 250,
    "treasure_bonus": 1000,
    "max_steps": 120,
    "max_targets": 64,
    "step_cost": 5,
}

DIRECTIONS = [(-1, 0, "up"), (1, 0, "down"), (0, -1, "left"), (0, 1, "right")]
PROMPT_FIELDS = ("prompt", "input", "inputPrompt", "InputPrompt", "navigation_prompt", "navigationPrompt", "question", "text")


def lambda_handler(event, context):
    """
    Pathfinding Lambda.

    The tool accepts either structured input:
      {"game_map": [[...]], "start_pos": [3,0], "strategy": "maximize_score"}

    or a full navigation prompt containing a grid JSON array and text such as:
      Find a path from position A4 ... map: [[...]]. use strategy maximize_score

    Optional tile rules can be passed with tile_rules/rules/tile_overrides. Those
    override the default challenge-rule metadata without changing the algorithm.
    """
    try:
        body = _body(event)
        prompt_text = _prompt_text(body)
        print(f"DEBUG: Received event: {body}")

        game_map = body.get("game_map") or body.get("map") or _parse_grid_from_prompt(prompt_text)
        if game_map:
            game_map = _normalize_map(game_map)
        if not game_map:
            return _err(400, "Missing game_map")

        rules = _build_rules(body, prompt_text)
        rows, cols = len(game_map), len(game_map[0])

        start_pos = _start_position(body, prompt_text)
        if not _in_bounds(start_pos, rows, cols):
            start_pos = (0, 0)

        treasure = _find_cell(game_map, "treasure")
        if treasure is None:
            return _err(400, "No treasure found on map")

        strategy = _strategy(body, prompt_text)
        if strategy == "maximize_score":
            path = maximize_score_path(game_map, rows, cols, start_pos, treasure, rules)
        elif strategy == "get_coins":
            path = get_coins_path(game_map, rows, cols, start_pos, treasure, rules)
        else:
            path = swift_path(game_map, rows, cols, start_pos, treasure, rules)

        path = _prune_zero_gain_loops(game_map, start_pos, path, rules)
        result = {"path": path, "steps": len(path), "start_position": list(start_pos)}
        print(f"RESULT: strategy={strategy} steps={len(path)} start={list(start_pos)}")
        return {"statusCode": 200, "body": json.dumps(result)}
    except Exception as e:
        print(f"ERROR: {e}")
        return _err(500, str(e))


def _body(event):
    if isinstance(event, str):
        return {"prompt": event}
    if isinstance(event, dict) and "body" in event:
        raw = event["body"]
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"prompt": raw}
        return raw if isinstance(raw, dict) else {}
    return event if isinstance(event, dict) else {}


def _err(code, msg):
    return {"statusCode": code, "body": json.dumps({"error": msg})}


def _prompt_text(body):
    for field in PROMPT_FIELDS:
        value = body.get(field) if isinstance(body, dict) else None
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _parse_grid_from_prompt(text):
    if not text:
        return []
    start = text.find("[[")
    if start < 0:
        return []
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                raw = text[start:i + 1]
                try:
                    parsed = json.loads(raw)
                    return parsed if isinstance(parsed, list) else []
                except json.JSONDecodeError:
                    return []
    return []


def _normalize_map(game_map):
    rows = []
    for row in game_map:
        if isinstance(row, list):
            rows.append([str(cell) for cell in row])
    if not rows:
        return []
    max_cols = max(len(row) for row in rows)
    return [row + ["normal"] * (max_cols - len(row)) for row in rows]


def _parse_start(pos):
    try:
        if isinstance(pos, (list, tuple)):
            if len(pos) == 1:
                return _parse_start(pos[0])
            if len(pos) >= 2:
                a = re.sub(r"[^A-Za-z0-9-]", "", str(pos[0]))
                b = re.sub(r"[^A-Za-z0-9-]", "", str(pos[1]))
                if a.isalpha():
                    return (int(b) - 1, ord(a.upper()) - ord("A"))
                return (int(a), int(b))
        raw = str(pos)
        compact = re.sub(r"[^A-Za-z0-9-]", "", raw)
        m = re.match(r"([A-Za-z])(\d+)", compact)
        if m:
            return (int(m.group(2)) - 1, ord(m.group(1).upper()) - ord("A"))
        nums = re.findall(r"-?\d+", raw)
        if len(nums) >= 2:
            return (int(nums[0]), int(nums[1]))
    except (ValueError, TypeError, IndexError):
        pass
    return (0, 0)


def _start_position(body, prompt_text):
    map_config = body.get("map_config", {}) if isinstance(body.get("map_config"), dict) else {}
    for value in (
        map_config.get("playerStart"),
        body.get("playerStart"),
        body.get("start_pos"),
        body.get("start"),
        body.get("position"),
    ):
        if value not in (None, "", {}):
            return _parse_start(value)
    if prompt_text:
        m = re.search(r"from\s+position\s+([A-Za-z]\d+)", prompt_text, re.IGNORECASE)
        if not m:
            m = re.search(r"position\s+([A-Za-z]\d+)", prompt_text, re.IGNORECASE)
        if m:
            return _parse_start(m.group(1))
    return (0, 0)


def _strategy(body, prompt_text):
    raw = str(body.get("strategy") or "").lower().strip()
    if not raw and prompt_text:
        m = re.search(r"use\s+strategy\s+([a-zA-Z0-9_-]+)", prompt_text, re.IGNORECASE)
        if m:
            raw = m.group(1).lower()
    if "max" in raw or "score" in raw or "best" in raw or "loot" in raw:
        return "maximize_score"
    if "coin" in raw:
        return "get_coins"
    if "swift" in raw or "fast" in raw or "quick" in raw:
        return "swift"
    return "swift"


def _build_rules(body, prompt_text=""):
    rules = {
        "walls": set(DEFAULT_RULES["walls"]),
        "rewards": dict(DEFAULT_RULES["rewards"]),
        "damage": dict(DEFAULT_RULES["damage"]),
        "locked_damage": dict(DEFAULT_RULES["locked_damage"]),
        "requires": dict(DEFAULT_RULES["requires"]),
        "items": set(DEFAULT_RULES["items"]),
        "avoid": set(DEFAULT_RULES["avoid"]),
        "starting_lives": int(DEFAULT_RULES["starting_lives"]),
        "life_bonus": int(DEFAULT_RULES["life_bonus"]),
        "treasure_bonus": int(DEFAULT_RULES["treasure_bonus"]),
        "max_steps": int(DEFAULT_RULES["max_steps"]),
        "max_targets": int(DEFAULT_RULES["max_targets"]),
        "step_cost": int(DEFAULT_RULES["step_cost"]),
    }
    for key in ("tile_rules", "rules", "tile_overrides"):
        overrides = body.get(key)
        if isinstance(overrides, dict):
            _merge_rules(rules, overrides)
    if prompt_text:
        _merge_prompt_rule_hints(rules, prompt_text)
    return rules


def _merge_rules(rules, overrides):
    aliases = {
        "reward": "rewards",
        "rewards": "rewards",
        "points": "rewards",
        "damage": "damage",
        "damages": "damage",
        "locked_damage": "locked_damage",
        "requires": "requires",
        "required": "requires",
    }
    for source_key, target_key in aliases.items():
        value = overrides.get(source_key)
        if isinstance(value, dict):
            for cell, amount in value.items():
                if amount is None:
                    rules[target_key].pop(str(cell), None)
                elif target_key == "requires":
                    rules[target_key][str(cell)] = str(amount)
                else:
                    rules[target_key][str(cell)] = _number(amount, rules[target_key].get(str(cell), 0))
    for set_key in ("walls", "items"):
        value = overrides.get(set_key)
        if isinstance(value, dict):
            for cell, enabled in value.items():
                if enabled:
                    rules[set_key].add(str(cell))
                else:
                    rules[set_key].discard(str(cell))
        elif isinstance(value, (list, tuple, set)):
            rules[set_key].update(str(cell) for cell in value)
        elif isinstance(value, str) and value:
            rules[set_key].add(value)

    # Treat structured "avoid" as a soft risk, not a hard wall. Agents often
    # translate prompt text like "bad c8" into avoid=["c8"]. Hard blocking is
    # reserved for explicit block/blocked fields or avoid-at-all-costs wording.
    avoid_value = overrides.get("avoid")
    if isinstance(avoid_value, dict):
        for cell, enabled in avoid_value.items():
            if enabled:
                _mark_soft_risk(rules, str(cell), 1)
            else:
                rules["damage"].pop(str(cell), None)
    elif isinstance(avoid_value, (list, tuple, set)):
        for cell in avoid_value:
            _mark_soft_risk(rules, str(cell), 1)
    elif isinstance(avoid_value, str) and avoid_value:
        _mark_soft_risk(rules, avoid_value, 1)

    blocked = overrides.get("blocked") or overrides.get("block")
    if isinstance(blocked, (list, tuple, set)):
        for cell in blocked:
            _mark_hard_block(rules, str(cell))
    elif isinstance(blocked, dict):
        for cell, enabled in blocked.items():
            if enabled:
                _mark_hard_block(rules, str(cell))
    for scalar in ("starting_lives", "life_bonus", "treasure_bonus", "max_steps", "max_targets", "step_cost"):
        if scalar in overrides:
            rules[scalar] = int(_number(overrides[scalar], rules[scalar]))
    for cell, config in overrides.items():
        if isinstance(config, dict) and re.fullmatch(r"c\d+", str(cell)):
            _merge_cell_config(rules, str(cell), config)


def _merge_cell_config(rules, cell, config):
    if "reward" in config or "points" in config:
        rules["rewards"][cell] = _number(config.get("reward", config.get("points")), 0)
    if "damage" in config:
        _mark_soft_risk(rules, cell, _number(config["damage"], 0))
    if config.get("blocked") or str(config.get("value", "")).lower() in {"avoid_at_all_cost", "avoid_at_all_costs", "blocked", "block"}:
        _mark_hard_block(rules, cell)
    elif config.get("avoid") or str(config.get("value", "")).lower() == "avoid":
        _mark_soft_risk(rules, cell, 1)
    if config.get("wall"):
        rules["walls"].add(cell)
    if "requires" in config:
        rules["requires"][cell] = str(config["requires"])
    if config.get("item") or config.get("collectible"):
        rules["items"].add(cell)


def _mark_soft_risk(rules, cell, amount=1):
    cell = str(cell)
    rules["avoid"].discard(cell)
    rules["damage"][cell] = int(_number(amount, 1))
    rules["rewards"].pop(cell, None)


def _mark_hard_block(rules, cell):
    cell = str(cell)
    rules["avoid"].add(cell)
    rules["damage"].pop(cell, None)


def _merge_prompt_rule_hints(rules, text):
    lowered = text.lower()

    # Prompt language:
    #   bad/avoid/danger c8 -> soft danger, assume 1 life damage unless a number is given
    #   block/forbid/never c18 -> hard block, remove from graph
    clauses = re.split(r"\b(?:and)\b|[.;,]", lowered)
    for clause in clauses:
        cells = re.findall(r"\bc\d+\b", clause)
        if not cells:
            continue

        hard_block = re.search(
            r"\b(?:block|blocked|forbid|forbidden|never|hard\s+avoid|avoid\s+at\s+all\s+costs?)\b",
            clause,
        )
        if hard_block:
            for cell in cells:
                _mark_hard_block(rules, cell)
            continue

        damage_match = re.search(r"\b(?:damage|costs?|life|lives)\b[^0-9\n]{0,10}(\d+)", clause)
        soft_danger = re.search(r"\b(?:bad|avoid|danger|dangerous|hazard|hazardous|risky|trap|spike)\b", clause)
        if damage_match or soft_danger:
            amount = int(damage_match.group(1)) if damage_match else 1
            for cell in cells:
                _mark_soft_risk(rules, cell, amount)

    # Backstop for compact hard-block forms that do not split neatly.
    for cell in re.findall(
        r"\b(c\d+)\b[^.\n]{0,50}?\b(?:block|forbid|never|hard\s+avoid|avoid\s+at\s+all\s+costs?)\b",
        lowered,
    ):
        _mark_hard_block(rules, cell)
    for cell in re.findall(
        r"\b(?:block|forbid|never|hard\s+avoid|avoid\s+at\s+all\s+costs?)\b[^.\n]{0,50}?\b(c\d+)\b",
        lowered,
    ):
        _mark_hard_block(rules, cell)


def _number(value, default):
    try:
        return float(value) if isinstance(default, float) else int(float(value))
    except (TypeError, ValueError):
        return default


def _in_bounds(pos, rows, cols):
    return isinstance(pos, tuple) and len(pos) == 2 and 0 <= pos[0] < rows and 0 <= pos[1] < cols


def _find_cell(game_map, wanted):
    for r, row in enumerate(game_map):
        for c, cell in enumerate(row):
            if cell == wanted:
                return (r, c)
    return None


def _cell_blocked(cell, rules, items, is_goal=False):
    if cell in rules["walls"]:
        return True
    if cell in rules["avoid"]:
        return True
    required = rules["requires"].get(cell)
    if required and required not in items and not is_goal:
        return True
    return False


def _move_damage(cell, rules):
    return int(rules["damage"].get(cell, 0))


def _shortest_path(game_map, rows, cols, start, goal, rules, items=None, damage_weight=0):
    items = set(items or [])
    heap = [(0, 0, start[0], start[1], [])]
    best = {(start[0], start[1]): 0}
    while heap:
        cost, steps, r, c, path = heapq.heappop(heap)
        if (r, c) == goal:
            return path
        if cost != best.get((r, c)):
            continue
        for dr, dc, move in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            cell = game_map[nr][nc]
            if cell == "treasure" and (nr, nc) != goal:
                continue
            if _cell_blocked(cell, rules, items, is_goal=(nr, nc) == goal):
                continue
            next_cost = cost + 1 + (_move_damage(cell, rules) * damage_weight)
            if next_cost < best.get((nr, nc), 10**12):
                best[(nr, nc)] = next_cost
                heapq.heappush(heap, (next_cost, steps + 1, nr, nc, path + [move]))
    return None


def swift_path(game_map, rows, cols, start, treasure, rules):
    return _shortest_path(game_map, rows, cols, start, treasure, rules, damage_weight=0) or []


def _walk_path(start, path):
    r, c = start
    for move in path:
        if move == "up":
            r -= 1
        elif move == "down":
            r += 1
        elif move == "left":
            c -= 1
        elif move == "right":
            c += 1
        yield (r, c)


def _route_delta(game_map, start, path, collected, items, rules):
    reward = 0
    damage = 0
    new_collected = set(collected)
    new_items = set(items)
    for pos in _walk_path(start, path):
        r, c = pos
        cell = game_map[r][c]
        if pos in new_collected:
            continue
        required = rules["requires"].get(cell)
        if required and required not in new_items:
            damage += int(rules["locked_damage"].get(cell, 0))
            new_collected.add(pos)
            continue
        if cell in rules["damage"]:
            damage += int(rules["damage"].get(cell, 0))
            new_collected.add(pos)
            continue
        if cell in rules["rewards"]:
            reward += int(rules["rewards"].get(cell, 0))
            new_collected.add(pos)
            if cell in rules["items"]:
                new_items.add(cell)
            continue
        if cell in rules["items"]:
            new_items.add(cell)
            new_collected.add(pos)
    return reward, damage, new_collected, new_items


def _find_targets(game_map, rows, cols, rules):
    target_cells = set(rules["rewards"]) | set(rules["items"])
    targets = []
    for r in range(rows):
        for c in range(cols):
            if game_map[r][c] in target_cells and game_map[r][c] not in rules["avoid"]:
                targets.append((r, c))
    return targets




def _limit_targets(game_map, rows, cols, start, rules, targets, max_targets):
    """Fallback only for unusually large maps; 10x10 boards search all targets."""
    required_cells = set(rules["items"]) | set(rules["requires"]) | {
        cell for cell, value in rules["rewards"].items() if value >= 400
    }

    def distance(pos):
        path = _shortest_path(game_map, rows, cols, start, pos, rules, damage_weight=int(rules["life_bonus"]))
        return len(path) if path is not None else 10**6

    def priority(pos):
        cell = game_map[pos[0]][pos[1]]
        coin_bias = 0 if cell == "c7" else 1
        return (coin_bias, -int(rules["rewards"].get(cell, 0)), distance(pos), pos[0], pos[1])

    must_keep = [pos for pos in targets if game_map[pos[0]][pos[1]] in required_cells]
    optional = [pos for pos in targets if pos not in must_keep]
    coins = [pos for pos in optional if game_map[pos[0]][pos[1]] == "c7"]
    other_optional = [pos for pos in optional if pos not in coins]
    slots = max(0, max_targets - len(must_keep))
    selected_optional = sorted(coins, key=priority)[:slots]
    remaining_slots = max(0, slots - len(selected_optional))
    selected_optional += sorted(other_optional, key=priority)[:remaining_slots]
    return must_keep + selected_optional

def _state_after_path(game_map, start, path, rules):
    reward, damage, collected, items = _route_delta(game_map, start, path, set(), set(), rules)
    return reward, damage, collected, items


def _prune_zero_gain_loops(game_map, start, path, rules):
    """Remove route spurs that return to the same square without gaining score."""
    changed = True
    pruned = list(path)
    while changed:
        changed = False
        coords = [start]
        for pos in _walk_path(start, pruned):
            coords.append(pos)
        for i in range(len(coords) - 2):
            _, _, prefix_collected, prefix_items = _state_after_path(game_map, start, pruned[:i], rules)
            for j in range(i + 2, len(coords)):
                if coords[i] != coords[j]:
                    continue
                loop = pruned[i:j]
                reward, damage, _, _ = _route_delta(
                    game_map,
                    coords[i],
                    loop,
                    prefix_collected,
                    prefix_items,
                    rules,
                )
                effect = reward - (damage * int(rules["life_bonus"]))
                touches_treasure = any(game_map[r][c] == "treasure" for r, c in coords[i + 1:j + 1])
                if not touches_treasure and effect <= 0:
                    pruned = pruned[:i] + pruned[j:]
                    changed = True
                    break
            if changed:
                break
    return pruned


def maximize_score_path(game_map, rows, cols, start, treasure, rules):
    """Compute a highest-score treasure route with a move-level knapsack search."""
    effect_positions = []
    effect_cells = set(rules["rewards"]) | set(rules["damage"]) | set(rules["items"]) | set(rules["requires"])
    for r in range(rows):
        for c in range(cols):
            cell = game_map[r][c]
            if cell in effect_cells and cell not in rules["avoid"]:
                effect_positions.append((r, c))

    max_targets = int(rules.get("max_targets", 64))
    if len(effect_positions) > max_targets:
        effect_positions = _limit_targets(game_map, rows, cols, start, rules, effect_positions, max_targets)

    effect_index = {pos: i for i, pos in enumerate(effect_positions)}
    item_bits = {}
    for pos, bit_index in effect_index.items():
        cell = game_map[pos[0]][pos[1]]
        if cell in rules["items"]:
            item_bits[cell] = item_bits.get(cell, 0) | (1 << bit_index)

    def has_item(mask, item):
        return bool(item_bits.get(item, 0) & mask)

    def step_effect(pos, mask, lives, score):
        cell = game_map[pos[0]][pos[1]]
        bit = 1 << effect_index[pos] if pos in effect_index else 0
        if bit and not (mask & bit):
            required = rules["requires"].get(cell)
            if required and not has_item(mask, required):
                return None
            if cell in rules["damage"]:
                lives -= int(rules["damage"].get(cell, 0))
            if cell in rules["rewards"]:
                score += int(rules["rewards"].get(cell, 0))
            mask |= bit
        return mask, lives, score

    max_steps = int(rules.get("max_steps", 120))
    step_cost = int(rules.get("step_cost", 0))
    life_bonus = int(rules["life_bonus"])
    treasure_bonus = int(rules["treasure_bonus"])
    starting_lives = int(rules["starting_lives"])

    # State is exact position, collected one-time effects, and remaining lives.
    # Value is reward minus movement cost so far plus the path that produced it.
    states = {(start[0], start[1], 0, starting_lives): (0, tuple())}
    best_score = -10**12
    best_path = None

    for _step in range(max_steps):
        next_states = {}
        for (r, c, mask, lives), (score, path_tuple) in states.items():
            for dr, dc, move in DIRECTIONS:
                nr, nc = r + dr, c + dc
                if not (0 <= nr < rows and 0 <= nc < cols):
                    continue
                cell = game_map[nr][nc]
                if cell in rules["walls"] or cell in rules["avoid"]:
                    continue

                new_score = score - step_cost
                new_lives = lives
                new_mask = mask
                if (nr, nc) != treasure:
                    effect = step_effect((nr, nc), new_mask, new_lives, new_score)
                    if effect is None:
                        continue
                    new_mask, new_lives, new_score = effect
                    if new_lives <= 0:
                        continue
                    key = (nr, nc, new_mask, new_lives)
                    new_path = path_tuple + (move,)
                    old = next_states.get(key)
                    if old is None or new_score > old[0] or (new_score == old[0] and len(new_path) < len(old[1])):
                        next_states[key] = (new_score, new_path)
                    continue

                # Treasure ends the run; do not move past it.
                new_path = path_tuple + (move,)
                total_score = new_score + (new_lives * life_bonus) + treasure_bonus
                if total_score > best_score or (total_score == best_score and len(new_path) < len(best_path or new_path)):
                    best_score = total_score
                    best_path = list(new_path)

        if not next_states:
            break
        states = next_states

    if best_path is not None:
        return best_path
    return get_coins_path(game_map, rows, cols, start, treasure, rules)

def get_coins_path(game_map, rows, cols, start, treasure, rules):
    """Greedily collect reachable coins, carrying key/item state forward."""
    board = [row[:] for row in game_map]
    r, c = start
    full_path = []
    items = set()
    collected = set()
    coin_cells = {cell for cell, reward in rules["rewards"].items() if cell == "c7" or str(cell).lower() == "coin"}

    for _ in range(50):
        queue = deque([(r, c, [])])
        visited = {(r, c)}
        targets = []
        while queue:
            cr, cc, p = queue.popleft()
            if board[cr][cc] in coin_cells and (cr, cc) != (r, c):
                targets.append((len(p), p, cr, cc))
            for dr, dc, move in DIRECTIONS:
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < rows and 0 <= nc < cols) or (nr, nc) in visited:
                    continue
                cell = board[nr][nc]
                if (nr, nc) == treasure:
                    continue
                if _cell_blocked(cell, rules, items):
                    continue
                visited.add((nr, nc))
                queue.append((nr, nc, p + [move]))
        if not targets:
            break
        targets.sort()
        _, path_to, nr, nc = targets[0]
        _, _, collected, items = _route_delta(game_map, (r, c), path_to, collected, items, rules)
        full_path.extend(path_to)
        r, c = nr, nc
        board[r][c] = "normal"

    path_end = _shortest_path(board, rows, cols, (r, c), treasure, rules, items=items, damage_weight=0)
    if path_end is not None:
        full_path.extend(path_end)
        return full_path
    return swift_path(game_map, rows, cols, start, treasure, rules)
