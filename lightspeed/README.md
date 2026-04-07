## Prerequisite
[chainsaw](https://kyverno.github.io/chainsaw/latest/quick-start/install/) >= v0.2.12

## Chainsaw Lightspeed Setup
Chainsaw tests in `lightspeed/` handle initial setup of OpenShift Lightspeed for AI-powered trace analysis integration:

- **Lightspeed Configuration**: Deploys OLSConfig with AI provider (OpenAI) settings
- **Secret Management**: Creates credential secret for Lightspeed API authentication
- **Parameters**: Set `CYPRESS_LIGHTSPEED_PROVIDER_URL` and `CYPRESS_LIGHTSPEED_PROVIDER_TOKEN` environment variables (Cypress automatically strips the `CYPRESS_` prefix when passing them to Chainsaw via heredoc)

Example manual run from the root of repository:
```bash
chainsaw test --config ./lightspeed/.chainsaw.yaml --skip-delete ./lightspeed --values - <<EOF
LIGHTSPEED_PROVIDER_URL: "https://api.openai.com/v1"
LIGHTSPEED_PROVIDER_TOKEN: "<lightspeed-api-token>"
EOF
```
