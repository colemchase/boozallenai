# Pathfinding custom model experiment

Goal: train a small custom model for the pathfinding sub-agent only. This is the safest custom-model target because it should only do two things:

1. call the Pathfinding Gateway tool with the complete raw navigation prompt
2. relay the returned path array exactly

Do not assign this model to the supervisor.

Leaderboard baseline to protect:

```text
Score: 11823
Architecture: supervisor + pathfinding sub-agent
Navigation prompt: use strategy maximize_score. bad c8.
Supervisor model: foundation
Pathfinding sub-agent model: foundation, replace only for this experiment
```

## Files

- `data/tool_calling_train.jsonl` — 700 samples
- `data/tool_calling_validation.jsonl` — 140 samples
- `data/faithfulness_train.jsonl` — 560 samples
- `data/faithfulness_validation.jsonl` — 112 samples
- `evaluators/tool_calling_reward.py`
- `evaluators/faithfulness_reward.py`
- `scripts/generate_datasets.py`

Regenerate datasets from the current local Lambda:

```bash
python3 model-workshop/pathfinding/scripts/generate_datasets.py
```

## Critical tool-name check

The dataset currently trains this live Gateway tool name from the combat logs:

```text
AgentCoreGatewayTool-Pathfinding-38eb___find_treasure_path
```

Before training, confirm the pathfinding sub-agent's tool schema in the UI still exposes that name. If the suffix or function name changed, edit `TOOL_NAME` in `scripts/generate_datasets.py`, regenerate all four JSONL files, and train on the regenerated files.

This matters. Training on a placeholder like `pathfinding_lambda` can make the custom model useless in the game UI.

## Stage 1: tool calling

This teaches the model to emit exactly one tool call with one `prompt` argument containing the complete raw navigation prompt.

Create evaluator:

1. SageMaker Studio > Assets > Evaluators.
2. Create Reward Function named `pathfinding-tool-calling-reward`.
3. Paste `evaluators/tool_calling_reward.py`.
4. Test, then Create.

Start customization from Qwen3-0.6B:

1. Customization technique: `RLVR`.
2. Training type: `LoRA`.
3. Reward function type: `Custom`.
4. Reward function: `pathfinding-tool-calling-reward`.
5. Upload dataset:
   - train: `data/tool_calling_train.jsonl`
   - validation: `data/tool_calling_validation.jsonl`
6. Epochs: `1`.
7. Suggested hyperparameters:
   - learning rate: `0.00005`
   - temperature: `0.1`
   - rollout temperature: `0.1`
   - LoRA rank: `8` or `16` if available
   - rollout samples per prompt: `4` if available
   - epochs: start with `3`; continue/retry only if reward is still climbing

Expected success: reward should climb past `0.85`. The updated evaluator rewards preserving the critical Lambda inputs rather than exact-copying every word: correct tool name, prompt argument, full map JSON, start position, strategy, bad/block hints, and no direct path hallucination.


## Phase 1 retry note

If tool-calling reward plateaus around `0.55`, do not continue to Phase 2. That usually means the model learned the tool name but failed to preserve the navigation prompt. Use the current `tool_calling_reward.py`, which gives component credit for preserving the map, start, strategy, and bad/block hints. Continue to Phase 2 only if Phase 1 reaches about `0.85+`.


## Final Phase 1 improvement

The latest dataset trains the model to receive the full game navigation prompt but send a compact Lambda prompt. This is intentional. The Lambda needs only:

```text
Find a path from position A4. Map: [[...]]. use strategy maximize_score. bad c8.
```

It does not need the whole coordinate-explanation paragraph. This reduces the tool-call argument length and should make Qwen3-0.6B better at preserving the map, start, strategy, and bad/block hints.

For one last Phase 1 attempt, continue from the current partially trained Phase 1 model if the UI allows it, not from base Qwen. Use the regenerated `tool_calling_train.jsonl` and `tool_calling_validation.jsonl`, the current `tool_calling_reward.py`, and:

```text
Epochs: 2 or 3
Learning rate: 0.00003 if continuing, 0.00005 if starting from base
Temperature: 0.1
Rollout temperature: 0.1
LoRA rank: 8 or 16
Rollout samples per prompt: 4
```

Continue to Phase 2 only if reward reaches about `0.85+`. If it lands around `0.75`, it may be better than before but is still risky for leaderboard play.

## Stage 2: faithfulness

Continue from the completed Stage 1 model. Do not restart from the base model.

This teaches the model to copy the Lambda path array exactly without dropping moves, adding prose, or inventing a shortcut.

Create evaluator:

1. Create Reward Function named `pathfinding-faithfulness-reward`.
2. Paste `evaluators/faithfulness_reward.py`.
3. Test, then Create.

Continue customization:

1. Open the Stage 1 model.
2. Continue customization / Train with different technique.
3. Customization technique: `RLVR`.
4. Training type: `LoRA`.
5. Reward function type: `Custom`.
6. Reward function: `pathfinding-faithfulness-reward`.
7. Upload dataset:
   - train: `data/faithfulness_train.jsonl`
   - validation: `data/faithfulness_validation.jsonl`
8. Epochs: `1`.
9. Suggested hyperparameters:
   - learning rate: `0.00002`
   - temperature: `0.05`
   - rollout temperature: `0.05`

Expected success: `exact_match`, `prefix_match`, and `length_match` should be near 1.0.

## Assign and test

After Stage 2 completes:

1. Register the Stage 2 training job ARN in AI League Model Workshop.
2. Deploy the registered model.
3. Assign it only to the pathfinding sub-agent.
4. Keep the supervisor on the foundation model and keep the leaderboard-baseline supervisor prompt.
5. Run local play with:

```text
use strategy maximize_score. bad c8.
```

Keep the custom pathfinder only if:

- the path is not 15 steps
- the path is not the stale 77-step lower-spike route
- it returns a complete JSON array only
- it collects 9,100 coins on the known local map
- it hits only the upper c8 spike on the known local map
- all prompted challenges still pass
- leaderboard score beats 11,823 or receives enough custom-model bonus to justify it

Rollback immediately if:

- first move hits a wall
- path misses upper-right coins
- path hits the lower E8 spike on the known local map
- path output includes prose, coordinates, markdown, or `<think>`
- leaderboard lives drop below 4

## Pathfinding sub-agent prompt to use with the custom model

Keep this prompt short. The custom model was trained for raw-prompt tool calling and exact relay.

```text
Call Pathfinding once for every navigation request. Pass the complete raw navigation prompt exactly as received in the prompt field, including map, start, strategy, and bad/block hints. Do not compute moves. Return only the path JSON array from the tool. No prose, markdown, labels, coordinates, or retries. If the tool fails, return PATHFINDING_TOOL_ERROR.
```

## Local smoke test result

The regenerated datasets and evaluators were smoke-tested locally:

```text
tool_calling_reward: 1.0 on an exact generated tool-call sample
faithfulness_reward: 1.0 on an exact generated path relay sample
first faithfulness sample path steps: 91
```
