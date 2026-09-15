# Supervisor custom model experiment

Goal: train a custom model for the supervisor as an overnight experiment. This is higher risk than the pathfinding custom model because the supervisor must route and format every challenge correctly.

Do not replace the proven supervisor until this model passes a full game run. Keep the current foundation supervisor as the rollback.

## Files

- `data/supervisor_routing_train.jsonl`
- `data/supervisor_routing_validation.jsonl`
- `data/supervisor_final_train.jsonl`
- `data/supervisor_final_validation.jsonl`
- `evaluators/supervisor_routing_reward.py`
- `evaluators/supervisor_final_reward.py`
- `scripts/generate_datasets.py`

## What this trains

Stage 1 trains routing and direct-answer behavior:

- navigation prompt -> `pathfinding_specialist` tool call
- c4 Web Weaver -> `AgentCoreGatewayTool-open-data-lookup___lookup_open_data` tool call
- c18 Claims Creature -> `AgentCoreGatewayTool-claims-solver___analyze_eob` tool call
- c42 Grey Key -> `AgentCoreGatewayTool-grey-code___process_grey_code_challenge` tool call
- c32 Grey Door -> `AgentCoreGatewayTool-grey-code___process_grey_code_challenge` tool call
- c1 Violet Vault -> exact refusal
- c2 Schedule Sage -> raw minified JSON, no fences
- c5 Simple Question -> shortest answer

Stage 2 trains exact final-answer style:

- no markdown fences
- no preambles
- no repeated questions
- exact JSON strings
- exact tool result relay

## Stage 1: supervisor routing

Create the evaluator first:

1. Go to SageMaker Studio > Assets > Evaluators.
2. Create a Reward Function evaluator named `supervisor-routing-reward`.
3. Paste the full contents of `evaluators/supervisor_routing_reward.py` as method code.
4. Test/create it.

Start customization:

1. Base model: Qwen3-0.6B.
2. Customization technique: RLVR.
3. Training type: LoRA.
4. Reward function type: Custom.
5. Reward functions: `supervisor-routing-reward`.
6. Dataset and output: Upload dataset.
7. Upload:
   - train: `data/supervisor_routing_train.jsonl`
   - validation/evaluation: `data/supervisor_routing_validation.jsonl`
8. Number of epochs: `1`.
9. Use conservative hyperparameters:
   - learning rate: `0.00003` to `0.00005`
   - temperature: `0.2`
   - rollout temperature: `0.2`
   - LoRA rank: `8` if available
   - rollout samples per prompt: `4` if available

## Stage 2: supervisor exact final output

Continue from the completed Stage 1 supervisor model, not the base model.

Create the evaluator:

1. Go to Assets > Evaluators.
2. Create a Reward Function evaluator named `supervisor-final-reward`.
3. Paste `evaluators/supervisor_final_reward.py` as method code.
4. Test/create it.

Continue customization:

1. Open the completed Stage 1 supervisor model.
2. Choose Continue customization / Train with different technique.
3. Customization technique: RLVR.
4. Training type: LoRA.
5. Reward function type: Custom.
6. Reward functions: `supervisor-final-reward`.
7. Upload:
   - train: `data/supervisor_final_train.jsonl`
   - validation/evaluation: `data/supervisor_final_validation.jsonl`
8. Number of epochs: `1`.
9. Use lower-temperature settings:
   - learning rate: `0.00002`
   - temperature: `0.05`
   - rollout temperature: `0.05`

## Register/deploy/test

1. Register the completed Stage 2 training job ARN in AI League Model Workshop.
2. Deploy the registered model.
3. Attach it to a duplicate/test supervisor first if the UI allows duplication.
4. If duplication is not available, take a screenshot of the current model selection before switching.
5. Run exactly:

```text
use strategy maximize_score. bad c8.
```

Keep the supervisor custom model only if:

- all 16 challenges pass
- c2 returns minified JSON with no code fences
- c18 returns exact claims-solver JSON
- c32 returns only the code
- c5 answers do not repeat the question
- total score beats the foundation supervisor baseline

Rollback immediately if any challenge fails. The foundation supervisor has already beaten 11,850; correctness is worth more than custom-model count.

## Important caveat

The supervisor tool names in this dataset are based on current combat logs:

- `pathfinding_specialist`
- `AgentCoreGatewayTool-open-data-lookup___lookup_open_data`
- `AgentCoreGatewayTool-grey-code___process_grey_code_challenge`
- `AgentCoreGatewayTool-claims-solver___analyze_eob`

If the UI exposes different tool names to the custom model, regenerate the dataset with those exact names before training.
