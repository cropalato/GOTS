# Okta OAuth Scopes Configuration

## Success! OAuth Authentication is Working ✅

Your `private_key_jwt` authentication is now successful! The next step is to grant the required API scopes.

## Current Issue

You're getting a **403 Forbidden** error:

```json
{
  "errorCode": "E0000006",
  "errorSummary": "Vous n'êtes pas autorisé à exécuter l'action demandée.",
  "errorLink": "E0000006"
}
```

This means the OAuth application is authenticated, but it doesn't have permission to access the Groups API.

## Required Scopes

GOTS requires these OAuth scopes:

- **`okta.groups.read`** - Read group information and list group members
- **`okta.users.read`** - Read user information (email, name, etc.)

## How to Grant Scopes

### Method 1: Via Okta Admin Console (Recommended)

1. **Log in to Okta Admin**: https://ludia.okta.com/admin

2. **Navigate to your OAuth App**:
   - Go to **Applications** > **Applications**
   - Click on your app (Client ID: `0oa1yqsu3mwArPIXN1d8`)

3. **Grant Scopes**:
   - Click the **Okta API Scopes** tab
   - Find and click **Grant** next to:
     - `okta.groups.read`
     - `okta.users.read`

   ![Okta API Scopes Tab Example](https://developer.okta.com/docs/guides/implement-oauth-for-okta/main/static/grant-scopes.png)

4. **Save** the changes

5. **Verify** the scopes are granted (they should show "Granted" status)

### Method 2: Via Okta API

If you need to grant scopes programmatically:

```bash
# Get your OAuth app details
curl -X GET "https://ludia.okta.com/api/v1/apps/0oa1yqsu3mwArPIXN1d8" \
  -H "Authorization: SSWS ${OKTA_ADMIN_API_TOKEN}"

# Grant scopes to the app
curl -X POST "https://ludia.okta.com/api/v1/apps/0oa1yqsu3mwArPIXN1d8/grants" \
  -H "Authorization: SSWS ${OKTA_ADMIN_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "scopeId": "okta.groups.read",
    "issuer": "https://ludia.okta.com"
  }'

curl -X POST "https://ludia.okta.com/api/v1/apps/0oa1yqsu3mwArPIXN1d8/grants" \
  -H "Authorization: SSWS ${OKTA_ADMIN_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "scopeId": "okta.users.read",
    "issuer": "https://ludia.okta.com"
  }'
```

## Verify Configuration

After granting the scopes, verify your GOTS configuration includes them:

### config.yaml:

```yaml
okta:
  domain: ludia.okta.com
  auth_method: oauth
  oauth:
    client_id: 0oa1yqsu3mwArPIXN1d8
    token_endpoint_auth_method: private_key_jwt
    private_key_path: /path/to/private.pem
    scopes:
      - okta.groups.read
      - okta.users.read
```

### Environment variables:

```bash
export OKTA_SCOPES=okta.groups.read,okta.users.read
```

## Test After Granting Scopes

Run GOTS again:

```bash
REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt LOG_LEVEL=INFO poetry run python -m src.main
```

You should now see:

```
INFO:src.okta_client:OAuth token acquired successfully, expires in 3600 seconds
INFO:src.okta_client:Found Okta group: LudiaAD_Coretech (ID: 00g...)
INFO:src.okta_client:Found 25 members in group 00g...
INFO:src.sync_service:Sync completed: +5 users, -2 users, 0 errors
```

## Troubleshooting

### Issue: "Okta API Scopes" tab not visible

**Cause**: Your application might not be an API Services App.

**Solution**:
1. Create a new **API Services App** in Okta:
   - Go to **Applications** > **Applications** > **Create App Integration**
   - Choose **API Services** (not Web App or Native App)
   - Set **Token Endpoint Authentication Method** to **Private Key JWT**
   - Upload your JWKSet
2. Note the new Client ID
3. Update your GOTS configuration with the new Client ID

### Issue: Scopes not showing in the list

**Cause**: You may be using a custom Authorization Server instead of the Org Authorization Server.

**Solution**:
1. Ensure you're using the **Org Authorization Server** (not "default")
2. Token URL should be: `https://ludia.okta.com/oauth2/v1/token` (NOT `/oauth2/default/v1/token`)
3. Verify in your logs:
   ```
   DEBUG:src.okta_client:Token endpoint: https://ludia.okta.com/oauth2/v1/token
   ```

### Issue: Still getting 403 after granting scopes

**Possible causes**:
1. **Scopes not granted**: Double-check the "Okta API Scopes" tab shows "Granted"
2. **Token not refreshed**: The old access token doesn't have the new scopes. Wait 60 minutes or restart GOTS to get a new token.
3. **Wrong scopes in config**: Verify `okta.groups.read` and `okta.users.read` are in your config

## Additional Scopes (Optional)

Depending on your Okta configuration, you may also need:

- `okta.groups.manage` - If you want to create/modify groups (not required for GOTS)
- `okta.users.manage` - If you want to create users in Okta (not required for GOTS)

## OAuth Best Practices

1. **Principle of Least Privilege**: Only grant the scopes you actually need
2. **Regular Audits**: Review granted scopes periodically
3. **Scope Documentation**: Document why each scope is needed
4. **Monitor Usage**: Check Okta System Log for unusual API access patterns

## References

- [Okta OAuth 2.0 Scopes](https://developer.okta.com/docs/guides/implement-oauth-for-okta/main/#scopes-and-supported-endpoints)
- [Grant Scopes to OAuth Apps](https://developer.okta.com/docs/guides/implement-oauth-for-okta/main/#grant-scopes-for-your-app)
- [Okta Groups API](https://developer.okta.com/docs/reference/api/groups/)
