# Pathfinding custom model experiment

Goal: train a small custom model for the pathfinding sub-agent only. Do not assign this model to the supervisor.

Baseline to beat: current architecture with foundation model pathfinding sub-agent, `use strategy maximize_score. bad c8.`, best observed score 11,851.

## Files

- `data/tool_calling_train.jsonl`
- `data/tool_calling_validation.jsonl`
- `data/faithfulness_train.jsonl`
- `data/faithfulness_validation.jsonl`
- `evaluators/tool_calling_reward.py`
- `evaluators/faithfulness_reward.py`

## Stage 1: tool calling

First create the evaluator in SageMaker Studio:

1. Go to Assets > Evaluators.
2. Create a Reward Function evaluator named `pathfinding-tool-calling-reward`.
3. Paste the full contents of `evaluators/tool_calling_reward.py` as the method code.
4. Test it if Studio offers a test button, then create it.

Then start the customization job from Qwen3-0.6B:

1. Customization technique: RLVR.
2. Training type: LoRA.
3. Reward function type: Custom.
4. Reward functions: `pathfinding-tool-calling-reward`.
5. Dataset and output: choose Upload dataset.
6. Upload:
   - train: `data/tool_calling_train.jsonl`
   - validation/evaluation: `data/tool_calling_validation.jsonl`
7. Use about 25 steps first.
8. Launch and wait for completion.

This teaches the custom model to emit a pathfinding tool call for navigation prompts.

## Stage 2: faithfulness

After Stage 1 completes, create the second evaluator:

1. Go to Assets > Evaluators.
2. Create a Reward Function evaluator named `pathfinding-faithfulness-reward`.
3. Paste the full contents of `evaluators/faithfulness_reward.py` as the method code.
4. Test it if Studio offers a test button, then create it.

Continue customization from the completed Stage 1 model, not from the base model:

1. Open the Stage 1 model details.
2. Choose Continue customization / Train with different technique.
3. Customization technique: RLVR.
4. Training type: LoRA.
5. Reward function type: Custom.
6. Reward functions: `pathfinding-faithfulness-reward`.
7. Dataset and output: choose Upload dataset.
8. Upload:
   - train: `data/faithfulness_train.jsonl`
   - validation/evaluation: `data/faithfulness_validation.jsonl`
9. Use about 30 steps.

This teaches the model to return the path array exactly.

## Register/deploy/use

1. Register the completed training job ARN in the AI League Model Workshop.
2. Deploy the registered model.
3. Assign it only to the pathfinding sub-agent.
4. Keep the supervisor on the current foundation model.
5. Test with:

```text
use strategy maximize_score. bad c8.
```

Success criteria:

- Same or better route.
- No dropped path steps.
- All 16 challenges still pass.
- `customModelCount` becomes 1 or custom model bonus appears.
- Score beats 11,851 or token/custom-model bonus improves without correctness regression.

If pathfinding changes or breaks, revert the pathfinding sub-agent model to the foundation model.

## Local smoke test

Both evaluator files were smoke-tested locally against known-good samples. Each returned `aggregate_reward_score: 1.0` and a Lambda-style `statusCode: 200` response.
