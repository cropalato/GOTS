# GOTS Monitoring & Alerting Guide

Comprehensive guide for monitoring and alerting on GOTS (Grafana-Okta Team Sync) in production.

## Table of Contents

- [Quick Start](#quick-start)
- [Metrics Reference](#metrics-reference)
- [Alert Rules](#alert-rules)
- [Grafana Dashboard](#grafana-dashboard)
- [Troubleshooting Runbooks](#troubleshooting-runbooks)
- [Best Practices](#best-practices)

---

## Quick Start

### 1. Enable Metrics in GOTS

**Via config.yaml:**
```yaml
metrics:
  enabled: true
  port: 8000
  host: 0.0.0.0
```

**Via environment variables:**
```bash
METRICS_ENABLED=true
METRICS_PORT=8000
METRICS_HOST=0.0.0.0
```

### 2. Configure Prometheus Scraping

**ServiceMonitor (if using Prometheus Operator):**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: gots
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: gots
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```

**Prometheus scrape config (traditional):**
```yaml
scrape_configs:
  - job_name: 'gots'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: ['platform']
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: gots
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
        target_label: __address__
        regex: ([^:]+)(?::\d+)?
        replacement: $1:8000
```

### 3. Load Alert Rules

```bash
# Copy alert rules to Prometheus configuration directory
cp prometheus-alerts.yaml /etc/prometheus/rules/

# Update prometheus.yml
rule_files:
  - "/etc/prometheus/rules/prometheus-alerts.yaml"

# Reload Prometheus
curl -X POST http://prometheus:9090/-/reload
```

### 4. Configure AlertManager

```bash
# Copy AlertManager config
cp alertmanager-config-example.yaml /etc/alertmanager/alertmanager.yml

# Update with your Slack/PagerDuty/Email credentials
vim /etc/alertmanager/alertmanager.yml

# Reload AlertManager
curl -X POST http://alertmanager:9093/-/reload
```

---

## Metrics Reference

### Available Metrics

GOTS exports the following Prometheus metrics:

#### `gots_sync_duration_seconds` (Histogram)
Duration of sync operations in seconds.

**Labels:**
- `okta_group`: Name of the Okta group
- `grafana_team`: Name of the Grafana team

**Buckets:** `1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0`

**Example queries:**
```promql
# 95th percentile sync duration
histogram_quantile(0.95, sum(rate(gots_sync_duration_seconds_bucket[5m])) by (le))

# Average sync duration per mapping
rate(gots_sync_duration_seconds_sum[5m]) / rate(gots_sync_duration_seconds_count[5m])

# Slowest mapping
topk(5,
  histogram_quantile(0.95,
    sum(rate(gots_sync_duration_seconds_bucket[5m])) by (le, okta_group, grafana_team)
  )
)
```

#### `gots_users_added_total` (Counter)
Total number of users added to Grafana teams.

**Labels:**
- `okta_group`: Name of the Okta group
- `grafana_team`: Name of the Grafana team

**Example queries:**
```promql
# Users added per minute
rate(gots_users_added_total[5m]) * 60

# Total users added today
increase(gots_users_added_total[24h])

# Most active mapping (by additions)
topk(5, sum(rate(gots_users_added_total[1h])) by (okta_group, grafana_team))
```

#### `gots_users_removed_total` (Counter)
Total number of users removed from Grafana teams.

**Labels:**
- `okta_group`: Name of the Okta group
- `grafana_team`: Name of the Grafana team

**Example queries:**
```promql
# Users removed per minute
rate(gots_users_removed_total[5m]) * 60

# Total churn (adds + removes)
sum(rate(gots_users_added_total[5m]) + rate(gots_users_removed_total[5m]))

# Mappings with most removals
topk(5, sum(rate(gots_users_removed_total[1h])) by (okta_group, grafana_team))
```

#### `gots_sync_errors_total` (Counter)
Total number of sync errors encountered.

**Labels:**
- `okta_group`: Name of the Okta group
- `grafana_team`: Name of the Grafana team

**Example queries:**
```promql
# Error rate
rate(gots_sync_errors_total[5m])

# Errors in last hour
increase(gots_sync_errors_total[1h])

# Mappings with most errors
topk(5, sum(rate(gots_sync_errors_total[15m])) by (okta_group, grafana_team))

# Error percentage
(sum(rate(gots_sync_errors_total[5m])) /
 (sum(rate(gots_users_added_total[5m])) + sum(rate(gots_users_removed_total[5m])) + 0.001)
) * 100
```

#### `gots_last_sync_timestamp` (Gauge)
Unix timestamp of the last sync completion.

**Labels:**
- `okta_group`: Name of the Okta group
- `grafana_team`: Name of the Grafana team

**Example queries:**
```promql
# Time since last sync (seconds)
time() - gots_last_sync_timestamp{}

# Mappings not synced in 30 minutes
(time() - gots_last_sync_timestamp{}) > 1800

# Most recently synced mapping
bottomk(1, time() - gots_last_sync_timestamp{})
```

#### `gots_last_sync_success` (Gauge)
Whether the last sync was successful (1=success, 0=failure).

**Labels:**
- `okta_group`: Name of the Okta group
- `grafana_team`: Name of the Grafana team

**Example queries:**
```promql
# Failed mappings
gots_last_sync_success{} == 0

# Success rate
sum(gots_last_sync_success{}) / count(gots_last_sync_success{}) * 100

# Count of failing mappings
count(gots_last_sync_success{} == 0)
```

---

## Alert Rules

### Alert Severity Levels

| Severity | Meaning | Response Time | Examples |
|----------|---------|---------------|----------|
| **CRITICAL** | Service completely broken or data loss risk | Immediate (page on-call) | App down, no syncs succeeding, all mappings failing |
| **WARNING** | Degraded functionality, needs attention | Within hours (notify team) | High error rate, slow syncs, individual mapping failing |
| **INFO** | Informational, may require investigation | Next business day | Partial failures, no activity, rate limiting |

### Critical Alerts

#### GOTSDown
**Trigger:** Pod not responding to Prometheus scrapes for 2+ minutes
**Impact:** No synchronization occurring
**Action:** Check pod status, logs, and recent deployments

#### GOTSNoSuccessfulSyncs
**Trigger:** No successful syncs in 30+ minutes AND errors occurring
**Impact:** User access is out of sync
**Action:** Check Okta/Grafana API connectivity and credentials

#### GOTSAllSyncsFailing
**Trigger:** Every configured mapping is failing for 10+ minutes
**Impact:** Complete synchronization failure
**Action:** Check system-wide issues (API credentials, network)

#### GOTSFrequentRestarts
**Trigger:** Pod restarting more than once per hour
**Impact:** Interrupted syncs, potential data inconsistency
**Action:** Check for OOMKilled, crashes, or liveness probe issues

### Warning Alerts

#### GOTSHighErrorRate
**Trigger:** Error rate above 20% for 10+ minutes
**Impact:** Partial synchronization failure
**Action:** Identify which mappings are failing and investigate

#### GOTSMappingFailing
**Trigger:** Specific mapping failing for 30+ minutes
**Impact:** One Okta group not syncing to Grafana
**Action:** Verify group/team exists, check permissions

#### GOTSSyncDurationHigh
**Trigger:** 95th percentile sync duration >2 minutes for 15+ minutes
**Impact:** Slow synchronization
**Action:** Check group size, API rate limiting, network latency

#### GOTSHighMemoryUsage / GOTSHighCPUUsage
**Trigger:** Resource usage >85% for 10-15 minutes
**Impact:** Potential OOMKill or throttling
**Action:** Increase limits if justified, investigate leaks

### Info Alerts

#### GOTSPartialSyncFailure
**Trigger:** Individual user operations failing
**Impact:** Some users not synced
**Action:** Review logs for specific user errors

#### GOTSNoSyncActivity
**Trigger:** No user changes in 6+ hours
**Impact:** None (may be normal)
**Action:** Verify expected behavior

---

## Grafana Dashboard

### Key Panels to Include

#### 1. **Sync Success Rate** (Gauge)
```promql
sum(gots_last_sync_success{}) / count(gots_last_sync_success{}) * 100
```
**Thresholds:** Red <80%, Yellow <95%, Green ≥95%

#### 2. **Active Syncs** (Time Series)
```promql
rate(gots_sync_duration_seconds_count[5m]) * 60
```
Shows syncs per minute

#### 3. **User Changes** (Time Series)
```promql
sum(rate(gots_users_added_total[5m]) * 60) by (grafana_team)  # Additions
sum(rate(gots_users_removed_total[5m]) * 60) by (grafana_team)  # Removals
```

#### 4. **Error Rate** (Time Series)
```promql
sum(rate(gots_sync_errors_total[5m])) * 60
```

#### 5. **Sync Duration** (Heatmap)
```promql
sum(rate(gots_sync_duration_seconds_bucket[5m])) by (le)
```

#### 6. **Mapping Status Table**
```promql
gots_last_sync_success{}  # Status column
time() - gots_last_sync_timestamp{}  # Last sync age column
```

#### 7. **Top 5 Active Mappings** (Bar Gauge)
```promql
topk(5,
  sum(rate(gots_users_added_total[1h]) + rate(gots_users_removed_total[1h]))
  by (okta_group, grafana_team)
)
```

### Import Dashboard JSON

```bash
# Import pre-built dashboard
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -d @gots-dashboard.json
```

---

## Troubleshooting Runbooks

### GOTSDown Runbook

**Alert:** Application is completely down

**Checklist:**
1. ✅ Check pod status
   ```bash
   kubectl get pods -n platform -l app=gots
   ```

2. ✅ Check pod logs
   ```bash
   kubectl logs -n platform <pod-name> --tail=100
   ```

3. ✅ Check events
   ```bash
   kubectl describe pod -n platform <pod-name>
   ```

4. ✅ Verify ConfigMap/Secrets exist
   ```bash
   kubectl get configmap -n platform gots-config
   kubectl get secret -n platform gots-secrets
   ```

5. ✅ Check resource usage
   ```bash
   kubectl top pod -n platform <pod-name>
   ```

**Common Causes:**
- **CrashLoopBackOff:** Configuration error, check logs for startup errors
- **ImagePullBackOff:** Image doesn't exist or registry authentication failed
- **OOMKilled:** Increase memory limits
- **Pending:** Node resources exhausted or node selector mismatch

### GOTSNoSuccessfulSyncs Runbook

**Alert:** No successful syncs in 30+ minutes

**Checklist:**
1. ✅ Check if app is running
   ```bash
   kubectl get pods -n platform -l app=gots
   ```

2. ✅ Test Okta API connectivity
   ```bash
   # From within pod
   kubectl exec -n platform <pod-name> -- curl -I \
     -H "Authorization: SSWS $OKTA_API_TOKEN" \
     https://$OKTA_DOMAIN/api/v1/groups
   ```

3. ✅ Test Grafana API connectivity
   ```bash
   # From within pod
   kubectl exec -n platform <pod-name> -- curl -I \
     -H "Authorization: Bearer $GRAFANA_API_KEY" \
     $GRAFANA_URL/api/org
   ```

4. ✅ Check logs for authentication errors
   ```bash
   kubectl logs -n platform <pod-name> | grep -i "401\|403\|authentication\|unauthorized"
   ```

5. ✅ Verify secrets are correctly mounted
   ```bash
   kubectl describe secret -n platform gots-secrets
   kubectl exec -n platform <pod-name> -- env | grep -E "OKTA|GRAFANA"
   ```

**Common Causes:**
- **401 Unauthorized:** API token expired or invalid
- **403 Forbidden:** Insufficient permissions
- **404 Not Found:** Wrong API endpoint or domain
- **Connection refused:** Network policy blocking egress
- **DNS resolution failure:** Service discovery issue

### GOTSHighErrorRate Runbook

**Alert:** Error rate above 20%

**Checklist:**
1. ✅ Identify which mappings are failing
   ```promql
   gots_last_sync_success{} == 0
   ```

2. ✅ Check logs for error patterns
   ```bash
   kubectl logs -n platform <pod-name> | grep -i error | tail -50
   ```

3. ✅ Verify Okta groups exist
   - Log into Okta Admin Console
   - Navigate to Directory → Groups
   - Verify exact group names (case-sensitive!)

4. ✅ Verify Grafana teams
   - Check if teams exist or can be created
   - Verify API key has Admin permissions

5. ✅ Check for rate limiting
   ```bash
   kubectl logs -n platform <pod-name> | grep -i "429\|rate limit"
   ```

**Common Causes:**
- Okta group renamed or deleted
- Grafana team permission issues
- Invalid user email addresses
- API rate limiting

---

## Best Practices

### 1. **Alert Fatigue Prevention**

✅ **DO:**
- Use inhibition rules to suppress redundant alerts
- Set appropriate `for` durations (avoid flapping)
- Use different channels for different severities
- Send INFO alerts to low-priority channels

❌ **DON'T:**
- Alert on every individual error
- Page for non-critical issues
- Send all alerts to the same channel

### 2. **Runbook Discipline**

Every alert should have:
- ✅ Clear description of the problem
- ✅ Impact statement (what's broken for users?)
- ✅ Step-by-step investigation checklist
- ✅ Common causes and solutions
- ✅ Link to detailed runbook

### 3. **Dashboard Design**

Organize dashboards into sections:
1. **Overview:** High-level health (success rate, active syncs)
2. **Performance:** Sync duration, throughput
3. **Errors:** Error rate, failing mappings
4. **Resources:** CPU, memory, restarts
5. **Details:** Per-mapping breakdown

### 4. **Metric Retention**

Recommended retention:
- **High resolution (30s):** 7 days
- **Medium resolution (5m):** 30 days
- **Low resolution (1h):** 1 year

### 5. **Testing Alerts**

Regularly test your alerts:
```bash
# Simulate pod down
kubectl scale deployment gots --replicas=0 -n platform

# Wait for GOTSDown alert
# Verify PagerDuty/Slack notification received

# Restore
kubectl scale deployment gots --replicas=1 -n platform
```

### 6. **Continuous Improvement**

Monthly review:
- Alert accuracy (false positives vs true positives)
- Response times to alerts
- Alert descriptions (are they helpful?)
- Runbook effectiveness
- Adjust thresholds based on actual behavior

---

## Appendix: Example Queries

### Capacity Planning

**Largest Okta groups:**
```promql
# Users added in last 24 hours (approximates group size)
topk(10, increase(gots_users_added_total[24h]))
```

**Busiest time of day:**
```promql
# User changes by hour
sum(rate(gots_users_added_total[1h]) + rate(gots_users_removed_total[1h])) by (hour(timestamp()))
```

### SLO Monitoring

**Sync success SLI (99% target):**
```promql
# Success rate over 30 days
sum(gots_last_sync_success{}) / count(gots_last_sync_success{}) >= 0.99
```

**Sync latency SLI (95% under 30s):**
```promql
# 95th percentile sync duration
histogram_quantile(0.95, sum(rate(gots_sync_duration_seconds_bucket[30d])) by (le)) < 30
```

### Debugging Queries

**Find syncs that never completed:**
```promql
# Mappings with no timestamp
absent(gots_last_sync_timestamp{okta_group="YourGroup"})
```

**Detect sync scheduling issues:**
```promql
# Time between syncs (should be ~interval_seconds)
increase(gots_sync_duration_seconds_count[10m]) < 1
```

**Identify memory leaks:**
```promql
# Memory usage trend (should be stable, not always increasing)
deriv(container_memory_working_set_bytes{pod=~"gots-.*"}[1h])
```

---

## Support

For issues or questions:
- **GitHub Issues:** https://github.com/cropalato/gots/issues
- **Documentation:** https://github.com/cropalato/gots/blob/main/README.md
- **Runbooks:** https://github.com/cropalato/gots/wiki

**Happy Monitoring!** 📊
