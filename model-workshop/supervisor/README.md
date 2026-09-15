# Supervisor custom model experiment

Goal: train a custom model for the current one-supervisor architecture without changing the working tools. The model should learn cheap routing and exact output style, while Lambdas still do the hard deterministic work.

Current baseline to protect:

```text
Score: 11863
Architecture: one supervisor, no sub-agents
Navigation prompt: use strategy maximize_score. bad c8.
Tools: Pathfinding, schedule-solver, claims-solver, open-data-lookup, grey-code, memtool, gr
```

There is no true guarantee that a custom model will beat the foundation model. The safest way to try is to train only the supervisor routing/relay behavior and test it against the baseline. Roll back immediately if any challenge fails.

## Files

- `data/supervisor_routing_train.jsonl`
- `data/supervisor_routing_validation.jsonl`
- `data/supervisor_final_train.jsonl`
- `data/supervisor_final_validation.jsonl`
- `evaluators/supervisor_routing_reward.py`
- `evaluators/supervisor_final_reward.py`
- `scripts/generate_datasets.py`

Regenerate datasets with:

```bash
python3 model-workshop/supervisor/scripts/generate_datasets.py
```

## Current tool names used in the dataset

These match the working one-supervisor combat logs. If the UI shows different names, edit `scripts/generate_datasets.py`, regenerate, and train with the regenerated files.

```text
AgentCoreGatewayTool-Pathfinding-38eb___find_treasure_path
AgentCoreGatewayTool-schedule-solver___analyze_sections
AgentCoreGatewayTool-claims-solver-38eb___analyze_eob
AgentCoreGatewayTool-open-data-lookup-38eb___lookup_open_data
AgentCoreGatewayTool-14451b01-38eb___process_grey_code_challenge
```

## Stage 1: routing/tool-call training

This teaches Qwen3-0.6B when to call each tool and when to answer directly.

Create evaluator:

1. SageMaker Studio > Assets > Evaluators.
2. Create Reward Function named `supervisor-routing-reward`.
3. Paste `evaluators/supervisor_routing_reward.py`.
4. Test, then Create.

Start customization:

1. Base model: `Qwen3-0.6B`.
2. Customization technique: `Reinforcement Learning with Verifiable Rewards (RLVR)`.
3. Training type: `LoRA`.
4. Reward function type: `Custom`.
5. Reward function: `supervisor-routing-reward`.
6. Upload dataset:
   - train: `data/supervisor_routing_train.jsonl`
   - validation: `data/supervisor_routing_validation.jsonl`
7. Number of epochs: `1`.
8. Suggested hyperparameters:
   - learning rate: `0.00003`
   - temperature: `0.2`
   - rollout temperature: `0.2`
   - LoRA rank: `8` if available
   - rollout samples per prompt: `4` if available

Expected success: reward climbs high and tool-name/argument rewards are near 1.0.

## Stage 2: exact final-answer relay

Continue from the completed Stage 1 model. Do not restart from the base model.

Create evaluator:

1. Create Reward Function named `supervisor-final-reward`.
2. Paste `evaluators/supervisor_final_reward.py`.
3. Test, then Create.

Continue customization:

1. Open the completed Stage 1 model.
2. Choose Continue customization / Train with different technique.
3. Customization technique: `RLVR`.
4. Training type: `LoRA`.
5. Reward function type: `Custom`.
6. Reward function: `supervisor-final-reward`.
7. Upload dataset:
   - train: `data/supervisor_final_train.jsonl`
   - validation: `data/supervisor_final_validation.jsonl`
8. Number of epochs: `1`.
9. Suggested hyperparameters:
   - learning rate: `0.00002`
   - temperature: `0.05`
   - rollout temperature: `0.05`

Expected success: exact-match/no-preamble rewards are near 1.0.

## Register, deploy, test

1. Register the completed Stage 2 training job ARN in AI League Model Workshop.
2. Deploy the registered model.
3. Attach it to the supervisor only. Keep the same tools, guardrail, memory, and compact supervisor prompt.
4. Run exactly:

```text
use strategy maximize_score. bad c8.
```

Keep it only if all are true:

- all 16 prompted challenges pass
- only one non-prompt loss: the upper c8 spike at row 1 col 4
- coins earned remains 9100
- c2 uses schedule-solver
- c18 uses claims-solver
- c4 uses open-data-lookup
- c32 returns only the code
- total score beats 11863 or at least tokens drop enough to justify retesting

Rollback immediately if:

- path is 15 steps, 77 steps, or misses 9100 coins
- c2 gets a privacy refusal or uses claims-solver
- c18 uses schedule-solver
- c4 gets a privacy refusal
- output contains `<think>`, markdown fences, or JSON wrappers around final answers

## Best expectation

A good custom supervisor probably saves a few hundred tokens and may add a custom-model bonus. It should not be expected to improve routing quality; the foundation supervisor already routes correctly. The custom model is only worth keeping if it preserves correctness and lowers token cost.
