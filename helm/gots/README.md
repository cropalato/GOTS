# GOTS Helm Chart

Grafana-Okta Team Sync (GOTS) - A Helm chart for deploying the GOTS service to Kubernetes.

## Overview

This Helm chart deploys GOTS, a service that periodically synchronizes Okta group membership to Grafana teams.

## Installation

### Prerequisites

- Kubernetes cluster (1.19+)
- Helm 3.x
- Okta authentication (choose one):
  - Okta API token with read access to groups, OR
  - Okta OAuth 2.0 application with `private_key_jwt` authentication
- Grafana API key with admin permissions

### Basic Installation with API Token

```bash
helm install gots ./helm/gots \
  --set okta.domain="your-company.okta.com" \
  --set okta.authMethod="api_token" \
  --set okta.apiToken="your-okta-api-token" \
  --set grafana.url="https://grafana.your-company.com" \
  --set grafana.apiKey="your-grafana-api-key"
```

### Installation with OAuth 2.0 (Recommended for Production)

#### Option 1: Using client_secret

```bash
helm install gots ./helm/gots \
  --set okta.domain="your-company.okta.com" \
  --set okta.authMethod="oauth" \
  --set okta.oauth.clientId="0oa1yr7t8z17ET9CX1d8" \
  --set okta.oauth.clientSecret="your-client-secret" \
  --set grafana.url="https://grafana.your-company.com" \
  --set grafana.apiKey="your-grafana-api-key"
```

#### Option 2: Using private_key_jwt (Most Secure)

First, create a Kubernetes secret with your private key:

```bash
kubectl create secret generic gots-private-key \
  --from-file=private.pem=/path/to/private.pem
```

Then install:

```bash
helm install gots ./helm/gots \
  --set okta.domain="your-company.okta.com" \
  --set okta.authMethod="oauth" \
  --set okta.oauth.clientId="0oa1yr7t8z17ET9CX1d8" \
  --set okta.oauth.tokenEndpointAuthMethod="private_key_jwt" \
  --set okta.oauth.privateKeySecretName="gots-private-key" \
  --set grafana.url="https://grafana.your-company.com" \
  --set grafana.apiKey="your-grafana-api-key"
```

### Installation with Custom Values

Create a `values.yaml` file for **API Token authentication**:

```yaml
okta:
  domain: "your-company.okta.com"
  authMethod: "api_token"
  apiToken: "your-okta-api-token"

grafana:
  url: "https://grafana.your-company.com"
  apiKey: "your-grafana-api-key"

sync:
  intervalSeconds: 3600  # Sync every hour
  dryRun: false
  admin_groups:
    - "Grafana-Admins"
  mappings:
    - okta_group: "Engineering"
      grafana_team: "Engineering"
    - okta_group: "DevOps"
      grafana_team: "DevOps"

resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

Or for **OAuth with private_key_jwt** (recommended):

```yaml
okta:
  domain: "your-company.okta.com"
  authMethod: "oauth"
  oauth:
    clientId: "0oa1yr7t8z17ET9CX1d8"
    tokenEndpointAuthMethod: "private_key_jwt"
    # Reference external secret (recommended)
    privateKeySecretName: "gots-private-key"
    privateKeySecretKey: "private.pem"
    # Or inline private key (not recommended for production)
    # privateKey: |
    #   -----BEGIN PRIVATE KEY-----
    #   MIIEvQIBADANBgkqhkiG9w0BAQEFAASCB...
    #   -----END PRIVATE KEY-----
    scopes:
      - okta.groups.read
      - okta.users.read

grafana:
  url: "https://grafana.your-company.com"
  apiKey: "your-grafana-api-key"

sync:
  intervalSeconds: 3600  # Sync every hour
  dryRun: false
  admin_groups:
    - "Grafana-Admins"
  mappings:
    - okta_group: "Engineering"
      grafana_team: "Engineering"
    - okta_group: "DevOps"
      grafana_team: "DevOps"

resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

Install with custom values:

```bash
helm install gots ./helm/gots -f values.yaml
```

## Configuration

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | GOTS Docker image repository | `cropalato/gots` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `Always` |
| **Okta Configuration** | | |
| `okta.domain` | Okta domain (e.g., company.okta.com) | `""` |
| `okta.authMethod` | Authentication method: `api_token` or `oauth` | `api_token` |
| `okta.apiToken` | Okta API token (for api_token method) | `""` |
| **OAuth Configuration** | | |
| `okta.oauth.clientId` | OAuth client ID | `""` |
| `okta.oauth.tokenEndpointAuthMethod` | OAuth auth method: `client_secret_basic`, `client_secret_post`, or `private_key_jwt` | `client_secret_basic` |
| `okta.oauth.clientSecret` | OAuth client secret (for client_secret_* methods) | `""` |
| `okta.oauth.privateKey` | Private key PEM content (for private_key_jwt) | `""` |
| `okta.oauth.privateKeySecretName` | Name of existing secret containing private key | `""` |
| `okta.oauth.privateKeySecretKey` | Key in the private key secret | `private.pem` |
| `okta.oauth.scopes` | OAuth scopes | `["okta.groups.read", "okta.users.read"]` |
| **Grafana Configuration** | | |
| `grafana.url` | Grafana URL | `""` |
| `grafana.apiKey` | Grafana API key | `""` |
| **Sync Configuration** | | |
| `sync.intervalSeconds` | Sync interval in seconds | `3600` |
| `sync.dryRun` | Enable dry-run mode (no changes applied) | `false` |
| `sync.admin_groups` | Okta groups that grant Grafana admin privileges | `[]` |
| `sync.mappings` | Okta group to Grafana team mappings | `[]` |
| **Resources** | | |
| `resources.limits.cpu` | CPU limit | `200m` |
| `resources.limits.memory` | Memory limit | `256Mi` |
| `resources.requests.cpu` | CPU request | `100m` |
| `resources.requests.memory` | Memory request | `128Mi` |
| **Other** | | |
| `extraEnv` | Additional environment variables for the container | `[]` |

### Extra Environment Variables

You can add custom environment variables to the container using the `extraEnv` parameter:

```yaml
extraEnv:
  - name: LOG_LEVEL
    value: "DEBUG"
  - name: CUSTOM_VAR
    value: "custom-value"
  # You can also reference secrets
  - name: SECRET_VAR
    valueFrom:
      secretKeyRef:
        name: my-secret
        key: my-key
```

### Sync Mappings

Define which Okta groups should sync to which Grafana teams:

```yaml
sync:
  mappings:
    - okta_group: "Engineering-Team"
      grafana_team: "Engineering"
    - okta_group: "Platform-Team"
      grafana_team: "Platform"
    - okta_group: "Data-Science"
      grafana_team: "Data Science"
```

### Admin Groups

Define which Okta groups should grant Grafana admin privileges:

```yaml
sync:
  admin_groups:
    - "Grafana-Admins"
    - "Platform-Team"
```

## Upgrading

```bash
helm upgrade gots ./helm/gots -f values.yaml
```

## Uninstalling

```bash
helm uninstall gots
```

## Dry Run Mode

To test the synchronization without making actual changes:

```bash
helm install gots ./helm/gots \
  --set sync.dryRun=true \
  -f values.yaml
```

Check the logs to see what changes would be made:

```bash
kubectl logs -f deployment/gots
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -l app.kubernetes.io/name=gots
```

### View Logs

```bash
kubectl logs -f deployment/gots
```

### Describe Deployment

```bash
kubectl describe deployment gots
```

### Verify ConfigMap

```bash
kubectl get configmap gots -o yaml
```

### Check Secrets

```bash
kubectl get secret gots
```

## OAuth Setup for Kubernetes

### Creating Private Key Secret

For `private_key_jwt` authentication, you need to create a Kubernetes secret containing your private key:

```bash
# Create secret from private key file
kubectl create secret generic gots-private-key \
  --from-file=private.pem=/path/to/private.pem

# Verify the secret was created
kubectl get secret gots-private-key
```

Then reference it in your values:

```yaml
okta:
  oauth:
    privateKeySecretName: "gots-private-key"
    privateKeySecretKey: "private.pem"
```

### OAuth Setup Checklist

Before deploying with OAuth, ensure you have:

- ✅ Created OAuth application in Okta (API Services App)
- ✅ Configured `private_key_jwt` authentication method
- ✅ Generated public/private key pair in Okta
- ✅ Downloaded private key and created Kubernetes secret
- ✅ Granted OAuth scopes: `okta.groups.read`, `okta.users.read`
- ✅ Assigned admin role: "Read-Only Group Administrator" or "Group Administrator"

See [OKTA_OAUTH_COMPLETE_SETUP.md](../../OKTA_OAUTH_COMPLETE_SETUP.md) for detailed OAuth setup instructions.

## Security Notes

- API tokens and keys are stored in Kubernetes Secrets
- Use RBAC to restrict access to the namespace
- Consider using external secret management (e.g., HashiCorp Vault, AWS Secrets Manager)
- Rotate API tokens and OAuth keys regularly
- Private keys are mounted as read-only volumes with 0400 permissions
- For production, always use `privateKeySecretName` instead of inline `privateKey`

## Support

For issues and questions, please visit: https://github.com/cropalato/gots
