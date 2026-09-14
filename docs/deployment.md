# Deploy and test from the CLI

Requirements: Python 3.11+ and AWS CLI v2, with valid workshop credentials in profile `ai-league`. No Python packages, CDK, Docker, or Node installation needed.

## Current validation status

September 14, 2026: all three local pathfinding fixtures pass, template generation succeeds, and AWS `ValidateTemplate` succeeds. **Deployment is blocked:** the workshop `WSParticipantRole` denied `cloudformation:CreateChangeSet`. No candidate stack resources were deployed, and live smoke tests have not run.

The inspected role has `ReadOnlyAccess` and `ws-default-policy`; the latter permits IAM reads, service-linked role creation, and passing only `WSParticipantRole`, but does not grant the resource write operations needed here. Direct service deployment is not an available fallback under these permissions. Ask the workshop organizer for the intended development role/profile or deployment mechanism. Do not change the participant role or use another role to evade this restriction.

The supported deployment identity will need CloudFormation stack/change-set operations and the resource operations used by this template: Lambda create/update, IAM logging-role/policy management and PassRole, CloudWatch log-group management, AgentCore memory create/update, and Bedrock guardrail create/update, with rollback/delete permissions for these candidate resources. Live tests additionally need Lambda InvokeFunction, AgentCore CreateEvent/GetEvent, and Bedrock ApplyGuardrail. Organizers should scope these to the candidate resources rather than grant general administrator access.

With an organizer-provided profile for this same account, pass `--profile PROFILE` to the commands below. Account validation stays enabled.

From the repository:

```sh
cd /Users/chase/Desktop/code/boozallenai
python3 scripts/league.py test
python3 scripts/league.py deploy
python3 scripts/league.py smoke
python3 scripts/league.py outputs
```

`deploy` runs the local fixtures, builds the CloudFormation template, verifies account `311141566489`, validates the template with AWS, and creates or updates `ai-league-candidate` in `us-east-1`. It waits for deployment completion. Repeating it without changes succeeds without updating resources.

`smoke` prints PASS/FAIL and returns exit code **0** only if every check passes; otherwise it returns **1**. It tests:

- Lambda shortest-path behavior around walls.
- Lambda coin detour behavior.
- Lambda's application error for missing input, checking both invocation metadata and response body.
- An actual AgentCore memory event write and matching read in a unique test session.
- Guardrail allowance of dungeon instructions/responses and blocking of investment advice, on both INPUT and OUTPUT.

Raw test requests, responses, and a summary are saved in ignored `.local/runs/`. Memory test events remain in the candidate memory until its 30-day expiry. Guardrail evaluation is a live AWS service call; these tests do not invoke an external model from Lambda.

## What to edit

| File | Purpose |
| --- | --- |
| `src/pathfinding/handler.py` | Lambda code, initially copied from the workshop S3 demo package. |
| `infra/stack.json` | CloudFormation resources and guardrail policy. |
| `infra/pathfinding-schema.json` | Captured gateway tool schema for future integration. |
| `tests/fixtures/pathfinding.json` | Tool inputs and expected status/body. |
| `tests/fixtures/guardrail.json` | Guardrail cases and expected actions. |

The build inserts the Python source into `Code.ZipFile` in `.local/build/stack.json`, using handler `index.lambda_handler`. Edit source/template files, not generated files. Deployment uses CloudFormation's normal change-set workflow and rollback behavior. It creates a Lambda logging role with no model invocation permissions.

## Boundaries of PASS

These are **component checks**, not the official challenge grader, a leaderboard score, or proof of agent integration. The stack creates a candidate Lambda, log group, IAM role, memory, and DRAFT guardrail. It does not replace the workshop runtime or change its gateway target. New memory starts empty with no long-term extraction strategies.

The initial guardrail policy is an investment-advice test policy based on the existing setup; it is not yet tuned to the actual guardrail challenge. The initial pathfinder preserves the demo behavior, including known limitations: spike traversal, possible early treasure crossing in coin routes, permissive input repair, and no distinct unreachable-route error. Current smoke cases verify deployment and selected baseline behavior, not full routing correctness.

To use the candidates in the game, the Lambda must be registered as a gateway target with suitable invocation permissions, and the game/agent configuration must select the candidate resources. The downloaded orchestrator source accepts `memory_id`, `guardrail_id`, and `guardrail_version` in invocation payloads, and filters tools using `supervisor_targets`/subagent allowed targets. Verify the actual game configuration flow before switching.

No documented official CLI game-grading endpoint was found in the inspected source. Capture the game challenge definitions and real invocation payload before adding end-to-end agent assertions.

## Troubleshooting

- Expired credentials: refresh the `ai-league` profile from Workshop Studio.
- Account mismatch: the script stops before deployment or smoke-test mutations.
- Deployment failure: inspect events with `aws cloudformation describe-stack-events --stack-name ai-league-candidate --profile ai-league --region us-east-1`.
- A failed initial deployment in `ROLLBACK_COMPLETE` needs explicit cleanup before recreating; the script does not automatically delete stacks.
- Guardrail assertion failure: inspect its saved response and tune policy/cases using actual requirements. Do not weaken the assertion solely to obtain PASS.
- Successful component tests but a failed game: inspect gateway registration, agent tool selection, memory IDs, guardrail version, and response format.

AWS references: [Lambda inline code](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-lambda-function.html), [AgentCore memory resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrockagentcore-memory.html), and [Bedrock guardrail resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrock-guardrail.html).
