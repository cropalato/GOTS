# Okta Admin Role Setup for OAuth Applications

## Critical Requirement: Admin Role Assignment

When using OAuth for Okta (OAuth 2.0 with the Org Authorization Server), **scopes alone are NOT sufficient**. The OAuth application also needs an **admin role** assigned to it.

## The Problem

Even with correct OAuth configuration:
- ✅ Authentication successful
- ✅ Access token contains the required scopes (`okta.groups.read`, `okta.users.read`)
- ✅ Scopes are granted to the application

You may still get **403 Forbidden** errors when accessing Okta APIs:

```json
{
  "errorCode": "E0000006",
  "errorSummary": "You are not authorized to perform the requested action"
}
```

## The Solution: Assign an Admin Role

OAuth applications need an **admin role** to actually use the granted scopes.

### Required Admin Role

For GOTS (reading groups and users), assign one of these roles:

- **Group Administrator** (Recommended) ✅
  - Can read all groups and group members
  - Can manage group memberships
  - Minimal permissions for the task

- **Read-Only Administrator**
  - Can read all Okta resources
  - Cannot modify anything
  - Use this if you want even more restricted access

- **Super Administrator** (Not recommended)
  - Full access to everything
  - Too many permissions for GOTS

## How to Assign Admin Role to OAuth Application

### Method 1: Via Okta Admin Console

1. **Go to Okta Admin Console**: https://your-domain.okta.com/admin

2. **Navigate to the Application**:
   - Go to **Applications** > **Applications**
   - Click on your OAuth application

3. **Assign Admin Role**:
   - Click the **Admin Roles** tab (or **Assignments** tab)
   - Click **Add Role** or **Grant**
   - Select **Group Administrator**
   - Click **Save**

### Method 2: Via Okta API

```bash
# Get the application's client ID
CLIENT_ID="0oa1yr7t8z17ET9CX1d8"

# Grant Group Administrator role
curl -X POST "https://your-domain.okta.com/api/v1/apps/${CLIENT_ID}/grants" \
  -H "Authorization: SSWS ${OKTA_ADMIN_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "scopeId": "okta.groups.read",
    "issuer": "https://your-domain.okta.com"
  }'
```

**Note**: The exact API endpoint for assigning admin roles may vary. Consult Okta's API documentation for the current method.

## Complete OAuth Setup Checklist

For OAuth for Okta to work, you need **ALL** of these:

### 1. ✅ Application Configuration
- [ ] Application type: **API Services App**
- [ ] Token endpoint auth method: **Private Key JWT**
- [ ] JWKSet configured with your public key
- [ ] Grant type: **Client Credentials** enabled

### 2. ✅ Scope Configuration
- [ ] Scopes granted in Okta:
  - [ ] `okta.groups.read`
  - [ ] `okta.users.read`
- [ ] Scopes appear in access token

### 3. ✅ Admin Role Assignment (Critical!)
- [ ] **Group Administrator** role assigned to the application
- [ ] Or another appropriate admin role

### 4. ✅ GOTS Configuration
```yaml
okta:
  domain: your-company.okta.com
  auth_method: oauth
  oauth:
    client_id: YOUR_CLIENT_ID
    token_endpoint_auth_method: private_key_jwt
    private_key_path: /path/to/private.pem
    scopes:
      - okta.groups.read
      - okta.users.read
```

## Verification

After assigning the admin role, test GOTS:

```bash
REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt LOG_LEVEL=INFO poetry run python -m src.main
```

Expected output:
```
INFO:src.okta_client:OAuth token acquired successfully, expires in 3600 seconds
INFO:src.okta_client:Granted scopes: ['okta.groups.read', 'okta.users.read']
INFO:src.okta_client:Found Okta group: YourGroup (ID: 00g...)
INFO:src.sync_service:Sync completed: +5 users, -0 users, 0 errors
```

## Why This is Required

Okta's OAuth for Okta uses a **three-layer permission model**:

1. **Scopes in token** - What the token claims it can do
2. **Application grants** - What scopes are allowed for the app
3. **Admin role** - What the app is actually authorized to access ⭐ **This was missing!**

All three layers must be properly configured for OAuth to work.

## Security Considerations

### Principle of Least Privilege

- ✅ **Good**: Assign **Group Administrator** role (minimal permissions needed)
- ❌ **Bad**: Assign **Super Administrator** role (excessive permissions)

### Admin Role Permissions

**Group Administrator** can:
- ✅ Read all groups
- ✅ Read group members
- ✅ Add/remove group members
- ✅ Create/delete groups
- ❌ Access other Okta resources (users, apps, policies, etc.)

**Read-Only Administrator** can:
- ✅ Read all Okta resources
- ❌ Modify anything

Choose the role that fits your security requirements.

## Troubleshooting

### Issue: Still getting 403 after assigning role

**Possible causes**:
1. **Role not propagated**: Wait a few minutes and try again
2. **Token not refreshed**: Restart GOTS to get a new token with updated permissions
3. **Wrong role**: Ensure you assigned Group Administrator, not a custom role without group permissions

### Issue: Can't find "Admin Roles" tab

**Cause**: You might not have Super Admin permissions.

**Solution**: Ask a Super Admin to assign the role to the OAuth application.

### Issue: Role assignment not available for app type

**Cause**: Application might be a Public Client instead of Service App.

**Solution**: Create a new **API Services App** (Service Apps support admin role assignment).

## References

- [Okta OAuth for Okta Guide](https://developer.okta.com/docs/guides/implement-oauth-for-okta/main/)
- [Okta Administrator Roles](https://help.okta.com/en-us/Content/Topics/Security/administrators-admin-comparison.htm)
- [OAuth 2.0 Best Practices](https://developer.okta.com/docs/guides/oauth-best-practices/)
