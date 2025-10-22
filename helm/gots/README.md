# GOTS Helm Chart

Grafana-Okta Team Sync (GOTS) - A Helm chart for deploying the GOTS service to Kubernetes.

## Overview

This Helm chart deploys GOTS, a service that periodically synchronizes Okta group membership to Grafana teams.

## Installation

### Prerequisites

- Kubernetes cluster (1.19+)
- Helm 3.x
- Okta API token with read access to groups
- Grafana API key with admin permissions

### Basic Installation

```bash
helm install gots ./helm/gots \
  --set okta.domain="your-company.okta.com" \
  --set okta.apiToken="your-okta-api-token" \
  --set grafana.url="https://grafana.your-company.com" \
  --set grafana.apiKey="your-grafana-api-key"
```

### Installation with Custom Values

Create a `values.yaml` file:

```yaml
okta:
  domain: "your-company.okta.com"
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
| `okta.domain` | Okta domain (e.g., company.okta.com) | `""` |
| `okta.apiToken` | Okta API token | `""` |
| `grafana.url` | Grafana URL | `""` |
| `grafana.apiKey` | Grafana API key | `""` |
| `sync.intervalSeconds` | Sync interval in seconds | `3600` |
| `sync.dryRun` | Enable dry-run mode (no changes applied) | `false` |
| `sync.admin_groups` | Okta groups that grant Grafana admin privileges | `[]` |
| `sync.mappings` | Okta group to Grafana team mappings | `[]` |
| `resources.limits.cpu` | CPU limit | `200m` |
| `resources.limits.memory` | Memory limit | `256Mi` |
| `resources.requests.cpu` | CPU request | `100m` |
| `resources.requests.memory` | Memory request | `128Mi` |
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

## Security Notes

- API tokens and keys are stored in Kubernetes Secrets
- Use RBAC to restrict access to the namespace
- Consider using external secret management (e.g., HashiCorp Vault, AWS Secrets Manager)
- Rotate API tokens regularly

## Support

For issues and questions, please visit: https://github.com/cropalato/gots
