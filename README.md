# Booz Allen AWS AI League

Working playbook for **BAH AWS AI League September 2026 — Batch 2**, Agentic Challenge. Use this repository to preserve rules, develop tools and prompts, and compare game results. AWS work uses the CLI in **us-east-1**.

## Playbook

- [Game rules](docs/game-rules.md): confirmed rules from the supplied Workshop Studio text.
- [Strategy](docs/strategy.md): route planning, challenge mastery, prompts, and improvement priorities.
- [Challenge inventory](docs/challenges.md): record exact map IDs, rewards, damage, and solving requirements.
- [AWS CLI runbook](docs/aws-cli.md): account identification, discovery, and deployment workflow.
- [Environment inventory](docs/environment.md): discovered workshop resources and integration status.
- [Deploy and test](docs/deployment.md): deploy our candidate stack and run CLI checks.
- [Starter agent](docs/starter-agent.md): simple configuration saved in the game UI and ready for a baseline test.
- [Agent architecture](docs/agent-architecture.md): recommended supervisor/sub-agent split and UI prompts for the next experiment.
- [Experiment log](docs/experiments.md): baseline and candidate comparisons.

## Current status

As of September 14, 2026: AWS access verified using `ai-league`, account `311141566489`, region `us-east-1`. Existing resources inventoried; workshop S3 agent and Lambda source inspected. Candidate infrastructure and CLI tests are implemented; three local fixtures and AWS template validation pass. Deployment is blocked by workshop role permissions (`cloudformation:CreateChangeSet` denied). No AWS resources have been changed. Live tests and official game scoring have not run. Proposed custom pathfinding strategies are not implemented yet.

Next: update the game UI to use the two-sub-agent architecture in [Agent architecture](docs/agent-architecture.md), attach memory/guardrail where supported, and rerun `get_coins` before changing Lambda code.
