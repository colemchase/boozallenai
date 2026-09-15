# Pathfinding custom model experiment

Goal: train a small custom model for the pathfinding sub-agent only. Do not assign this model to the supervisor.

This folder is reset to the original first-version workflow: train the model to emit a `pathfinding_lambda` tool call with one `prompt` argument, then train it to relay the returned path array exactly.

Baseline to beat: current architecture with foundation model pathfinding sub-agent, `use strategy maximize_score. bad c8.`, best observed score around 11,850.

## Files

- `data/tool_calling_train.jsonl`
- `data/tool_calling_validation.jsonl`
- `data/faithfulness_train.jsonl`
- `data/faithfulness_validation.jsonl`
- `evaluators/tool_calling_reward.py`
- `evaluators/faithfulness_reward.py`

## Stage 1: tool calling

Create the evaluator in SageMaker Studio:

1. Go to Assets > Evaluators.
2. Create a Reward Function evaluator named `pathfinding-tool-calling-reward`.
3. Paste the full contents of `evaluators/tool_calling_reward.py` as the method code.
4. Test/create it.

Start the customization job from Qwen3-0.6B:

1. Customization technique: RLVR.
2. Training type: LoRA.
3. Reward function type: Custom.
4. Reward functions: `pathfinding-tool-calling-reward`.
5. Dataset and output: Upload dataset.
6. Upload:
   - train: `data/tool_calling_train.jsonl`
   - validation/evaluation: `data/tool_calling_validation.jsonl`
7. Epochs: `1`.
8. Use conservative settings:
   - learning rate: `0.00003` to `0.00005`
   - temperature: `0.1` to `0.2`
   - rollout temperature: `0.1` to `0.2`
   - LoRA rank: `8` if available
   - rollout samples per prompt: `4` if available

This teaches the custom model to emit:

```text
<tool_call>{"name":"pathfinding_lambda","arguments":{"prompt":"..."}}</tool_call>
```

## Stage 2: faithfulness

Continue from the completed Stage 1 model.

Create the evaluator:

1. Go to Assets > Evaluators.
2. Create a Reward Function evaluator named `pathfinding-faithfulness-reward`.
3. Paste the full contents of `evaluators/faithfulness_reward.py` as the method code.
4. Test/create it.

Continue customization:

1. Open the Stage 1 model details.
2. Choose Continue customization / Train with different technique.
3. Customization technique: RLVR.
4. Training type: LoRA.
5. Reward function type: Custom.
6. Reward functions: `pathfinding-faithfulness-reward`.
7. Dataset and output: Upload dataset.
8. Upload:
   - train: `data/faithfulness_train.jsonl`
   - validation/evaluation: `data/faithfulness_validation.jsonl`
9. Epochs: `1`.
10. Use lower-temperature settings:
   - learning rate: `0.00002`
   - temperature: `0.05`
   - rollout temperature: `0.05`

The faithfulness evaluator has the crash fix for Studio wrappers like `{"path":[...],"steps":77}`.

## Register/deploy/use

1. Register the completed Stage 2 training job ARN in AI League Model Workshop.
2. Deploy the registered model.
3. Assign it only to the pathfinding sub-agent.
4. Keep the supervisor on the current foundation model.
5. Test with:

```text
use strategy maximize_score. bad c8.
```

Keep it only if:

- same route or better route
- no dropped path steps
- no invented first move into a wall
- all 16 challenges still pass
- score/custom-model bonus improves

If pathfinding changes or breaks, revert the pathfinding sub-agent model to the foundation model.

## Local smoke test

Both evaluator files were smoke-tested locally against known-good samples. Each returned `aggregate_reward_score: 1.0` and Lambda-style `statusCode: 200`.
