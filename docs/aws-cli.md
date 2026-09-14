# AWS CLI runbook

Region: `us-east-1`, as shown in Workshop Studio. Verified September 14, 2026: profile `ai-league` resolves to account `311141566489`, assumed role `WSParticipantRole/Participant`. Use this explicit profile for workshop commands.

## Identify the account

Use Workshop Studio's **Get AWS CLI credentials** to configure a dedicated profile such as `ai-league` locally. Temporary credentials require the session token as well as the access key and secret. Never put credentials in this repository or chat.

After configuring the workshop profile:

```sh
export LEAGUE_PROFILE=ai-league
export LEAGUE_REGION=us-east-1
aws sts get-caller-identity --profile "$LEAGUE_PROFILE" --region "$LEAGUE_REGION" --no-cli-pager
```

Compare the account with the Workshop Studio console before changing resources. [AWS CLI: get-caller-identity](https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html).

## Discover the provided Lambda

```sh
aws lambda list-functions --profile "$LEAGUE_PROFILE" --region "$LEAGUE_REGION" \
  --query 'Functions[].{Name:FunctionName,Runtime:Runtime,Handler:Handler,Description:Description}' \
  --output table --no-cli-pager
```

Identify the function using the workshop's Lambda page and description, then substitute its actual name:

```sh
export LEAGUE_FUNCTION='REPLACE_WITH_WORKSHOP_FUNCTION_NAME'
aws lambda get-function --function-name "$LEAGUE_FUNCTION" \
  --profile "$LEAGUE_PROFILE" --region "$LEAGUE_REGION" \
  --query '{Configuration:Configuration,Code:Code}' --no-cli-pager
```

Keep raw output local: configuration can contain sensitive values and the code URL grants temporary download access. For ZIP functions, `Code.Location` provides a download link valid for 10 minutes. [AWS CLI: get-function](https://docs.aws.amazon.com/cli/latest/reference/lambda/get-function.html).

## Implementation and deployment sequence

1. Save original deployment package and configuration under ignored `.local/`. Record the function revision and hash for rollback and concurrency checks.
2. Inspect source, dependencies, handler, packaging, permissions, strategy names, and tool input/output contract.
3. Commit sanitized source and representative fixtures, excluding credentials, signed URLs, and private configuration.
4. Implement `safe_loot`, preserving supported interfaces. Run local tests against representative captured events.
5. Package for the existing runtime and architecture. Deploy to the identified workshop function, checking its revision to avoid overwriting intervening changes.
6. Wait for a successful Lambda update, exercise the tool with a valid event, then run a game to verify agent integration and score.
7. Log the result and restore the saved package/configuration if behavior regresses.

Exact deployment commands will be added after the real function/package and workshop integration are known. A successful Lambda invocation alone does not prove that the game accepts the tool result.
