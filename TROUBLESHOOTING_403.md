# Troubleshooting 403 Forbidden with OAuth

## Issue

OAuth authentication is successful and the access token contains the correct scopes, but API calls return 403 Forbidden:

```
INFO:src.okta_client:Granted scopes: ['okta.groups.read', 'okta.users.read']
ERROR:src.okta_client:Okta API error: 403 - {"errorCode":"E0000006","errorSummary":"Vous n'êtes pas autorisé à exécuter l'action demandée."}
```

## Root Cause

When using **OAuth for Okta** (Org Authorization Server), having the scopes in the token is not sufficient. The application also needs **explicit admin consent/grant** in Okta.

## Solution Options

### Option 1: Grant Admin Consent (Recommended for Production)

1. **Via Okta Admin Console**:
   - Go to https://ludia.okta.com/admin
   - Navigate to **Applications** > **Applications**
   - Click on your OAuth app (Client ID: `0oa1yqsu3mwArPIXN1d8`)
   - Click **Okta API Scopes** tab
   - Ensure both scopes show "Granted" status:
     - ✅ `okta.groups.read` - Granted
     - ✅ `okta.users.read` - Granted

2. **Check Application Type**:
   - Ensure the application is an **API Services App** (not Web App)
   - API Services Apps have different permission models

3. **Verify Grant Status**:
   ```bash
   # List all grants for the application
   curl -X GET "https://ludia.okta.com/api/v1/apps/0oa1yqsu3mwArPIXN1d8/grants" \
     -H "Authorization: SSWS ${OKTA_ADMIN_API_TOKEN}"
   ```

   Expected output:
   ```json
   [
     {
       "id": "grant_id_1",
       "status": "ACTIVE",
       "scopeId": "okta.groups.read",
       "issuer": "https://ludia.okta.com"
     },
     {
       "id": "grant_id_2",
       "status": "ACTIVE",
       "scopeId": "okta.users.read",
       "issuer": "https://ludia.okta.com"
     }
   ]
   ```

4. **If grants are missing**, create them:
   ```bash
   # Grant okta.groups.read
   curl -X POST "https://ludia.okta.com/api/v1/apps/0oa1yqsu3mwArPIXN1d8/grants" \
     -H "Authorization: SSWS ${OKTA_ADMIN_API_TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{
       "scopeId": "okta.groups.read",
       "issuer": "https://ludia.okta.com"
     }'

   # Grant okta.users.read
   curl -X POST "https://ludia.okta.com/api/v1/apps/0oa1yqsu3mwArPIXN1d8/grants" \
     -H "Authorization: SSWS ${OKTA_ADMIN_API_TOKEN}" \
     -H "Content-Type": application/json" \
     -d '{
       "scopeId": "okta.users.read",
       "issuer": "https://ludia.okta.com"
     }'
   ```

### Option 2: Use API Token (Quick Test)

To verify the rest of the application works, temporarily switch back to API token authentication:

1. **Update config.yaml**:
   ```yaml
   okta:
     domain: ludia.okta.com
     auth_method: api_token
     api_token: 00_R1MwlXY3X2YyHaXzXPSfw9tBcO7zuEaAA-_dUMc
   ```

2. **Run GOTS**:
   ```bash
   REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt poetry run python -m src.main
   ```

3. **If this works**, it confirms the issue is with OAuth admin consent, not your code

### Option 3: Check Application Settings

The OAuth application might need specific settings:

1. **Application Type**: Must be **API Services App** or **Service App**
   - Go to application settings in Okta Admin Console
   - Check "Application type"
   - If it's "Web" or "Native", you may need to create a new API Services App

2. **Grant Type**: Should include **Client Credentials**
   - Check "Grant Types" section
   - Ensure "Client Credentials" is enabled

3. **Token Endpoint Auth Method**: Should be **Private Key JWT**
   - Already configured ✅

## Understanding OAuth for Okta Permissions

OAuth for Okta uses a **two-layer permission model**:

1. **Scope in Token** (✅ You have this):
   - The access token contains `okta.groups.read` and `okta.users.read`
   - This proves the token was issued with these scopes

2. **Application Grant** (❓ Might be missing):
   - The application must have an explicit **grant** from an admin
   - Grants authorize the application to use specific scopes
   - Even if the scope is in the token, without a grant, API calls fail with 403

## Verification Steps

Run these checks:

### 1. Verify Token Has Scopes
```bash
# Already confirmed ✅
INFO:src.okta_client:Granted scopes: ['okta.groups.read', 'okta.users.read']
```

### 2. Verify Application Has Grants
```bash
curl -X GET "https://ludia.okta.com/api/v1/apps/0oa1yqsu3mwArPIXN1d8/grants" \
  -H "Authorization: SSWS YOUR_ADMIN_API_TOKEN"
```

### 3. Check Application Type
```bash
curl -X GET "https://ludia.okta.com/api/v1/apps/0oa1yqsu3mwArPIXN1d8" \
  -H "Authorization: SSWS YOUR_ADMIN_API_TOKEN" \
  | jq '.signOnMode, .credentials.oauthClient.token_endpoint_auth_method'
```

Expected: `"OPENID_CONNECT"` and `"private_key_jwt"`

## Common Issues

### Issue: Application is a Web App, not API Services App

**Symptoms**:
- Can't find "Okta API Scopes" tab
- 403 errors even with scopes in token

**Solution**:
Create a new **API Services App**:
1. Go to **Applications** > **Create App Integration**
2. Choose **API Services**
3. Set **Token Endpoint Authentication Method** to **Private Key JWT**
4. Register your JWKSet (use the Okta-generated one)
5. Grant scopes: `okta.groups.read`, `okta.users.read`
6. Update GOTS config with new Client ID

### Issue: Grants exist but are INACTIVE

**Symptoms**:
- Grants show in API but status is "INACTIVE"

**Solution**:
```bash
# Revoke old grant
curl -X DELETE "https://ludia.okta.com/api/v1/apps/0oa1yqsu3mwArPIXN1d8/grants/GRANT_ID" \
  -H "Authorization: SSWS YOUR_ADMIN_API_TOKEN"

# Create new grant
curl -X POST "https://ludia.okta.com/api/v1/apps/0oa1yqsu3mwArPIXN1d8/grants" \
  -H "Authorization: SSWS YOUR_ADMIN_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scopeId": "okta.groups.read", "issuer": "https://ludia.okta.com"}'
```

## References

- [Okta OAuth for Okta Guide](https://developer.okta.com/docs/guides/implement-oauth-for-okta/main/)
- [Okta Application Grants API](https://developer.okta.com/docs/reference/api/apps/#application-oauth-2-0-scope-consent-grant-object)
- [OAuth Error Code E0000006](https://developer.okta.com/docs/reference/error-codes/#E0000006)
