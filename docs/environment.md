# Workshop environment

Read-only AWS CLI inventory on September 14, 2026. Profile: `ai-league`. Region: `us-east-1`. STS identity: account `311141566489`, assumed role `WSParticipantRole/Participant`. No deployments, game runs, or configuration changes performed.

## Game resources

| Resource | Name / ID | Observed state |
| --- | --- | --- |
| Pathfinding Lambda | `AgentCoreGatewayTool-Pathfinding` | Active; last update successful |
| AgentCore memory | `memtool` / `memtool-2g9JjYEzxL` | ACTIVE; event expiry 30 days; strategies empty |
| Bedrock guardrail | `dr` / `k0ulrujl1ob7` | READY; inspected version DRAFT |
| AgentCore runtime | `ai_league_agent_runtime-v7uc024Ccl` | READY; version 1 |
| AgentCore gateway | `ai-league-gateway-bvneeru6xy` | READY; MCP protocol; AWS_IAM authorization |
| Gateway target | `PathfindingLambdaTarget` / `SAUSVIQGFO` | READY; points to the pathfinding Lambda |

## Pathfinding Lambda

- Runtime: Python 3.11, architecture `arm64`.
- Handler: `pathfinding_lambda.lambda_handler`.
- Timeout: 190 seconds; memory: 3584 MB.
- Last modified: `2026-09-13T21:02:37.214+0000`.
- Log group: `/aws/lambda/AgentCoreGatewayTool-Pathfinding`.
- Revision: `8724b804-a223-43d5-ae53-95133474c962`.
- Code SHA-256 reported by AWS: `fBDZJlG464/a2oeLcaBg+2eNDog2pRLycGF7iU9wyg8=`.
- Gateway schema location: `s3://ai-league-agent-codebuild-sources-311141566489-us-east-1/demo/pathfinding_schema.json`.

The gateway uses its IAM role to access the tool. Source and schema contents have not yet been downloaded, so custom strategy support is unverified.

## Memory

`memtool` exists and is active, with `eventExpiryDuration: 30` and `strategies: []`. No configured memory strategies were returned. Event contents and actual agent use were not inspected; an empty strategy list does not establish that the memory contains no events.

## Guardrail

The inspected DRAFT has one denied topic:

- Name: `denied topic`.
- Definition: `no investment advice`.
- Type: DENY, CLASSIC tier.
- Input and output enabled, both actions BLOCK.
- Both blocked-response messages: `Don't worry about it`.
- No other policy categories were returned by this inspection.

Whether this meets the challenge requirements is unknown until the challenge guide is captured. Runtime application of this guardrail and the selected version are also unverified.

## Agent runtime

Version 1 uses container `311141566489.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-ai_league_main_agent:latest`. No environment variables were returned. This does not rule out memory/guardrail settings supplied in source, configuration files, or invocation inputs. The runtime being READY does not establish successful game execution.

## Other Lambda functions

Seven functions total were returned. Besides pathfinding:

- `ai-league-bootstrap-stack-CreateConfigFunction-w6C5zB9otWJO`
- `ai-league-bootstrap-stack-TriggerCodeBuildFunction-mFJQ9tEMP6DC`
- `ai-league-bootstrap-stack-CreateCodeEditorSpaceFun-3PIIgNJ1w360`
- `ai-league-bootstrap-stack-S3ExtractFunction-JWCuOF5KQ9Xk`
- `WSConcurrencyCurtailer-DO-NOT-USE`
- `template-AccountAuthorizationCodeGeneratorFunction-VSxbGKHgB8Ws`

These appear to support workshop provisioning/account operations by name. Their source and behavior have not been inspected.

## Next investigation

1. Download the pathfinding source and S3 tool schema, preserving originals locally.
2. Inspect agent configuration/source to locate prompt, memory, and guardrail wiring.
3. Capture challenge-specific rules before choosing memory strategies or changing guardrail policies.
4. Record baseline game scores before modifying navigation.

## Follow-up: source and deployment workflow

Downloaded the workshop S3 `demo/pathfinding_lambda.zip`, gateway schema, and `source/` agent files to ignored `.local/baseline/`. The repo candidate source is copied from this demo ZIP; it has not been hash-verified against the live Lambda deployment. Source confirms the agent accepts memory and guardrail IDs through invocation payloads. This identifies a wiring mechanism, not proof of the game’s current selections.

Added candidate CloudFormation and CLI tests; see [deployment status and commands](deployment.md). Local checks and AWS template validation passed. The attempt to create a change set was denied by the participant role, so no candidate resources were created. Live smoke tests remain unexecuted.
