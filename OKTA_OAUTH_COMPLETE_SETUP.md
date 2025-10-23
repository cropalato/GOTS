# Complete Okta OAuth Setup Guide for GOTS

This comprehensive guide walks you through setting up OAuth 2.0 authentication with `private_key_jwt` for GOTS, including creating a custom read-only admin role and configuring an API Services application.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Part 1: Create Custom Read-Only Admin Role](#part-1-create-custom-read-only-admin-role)
3. [Part 2: Create OAuth API Services Application](#part-2-create-oauth-api-services-application)
4. [Part 3: Configure GOTS](#part-3-configure-gots)
5. [Part 4: Verification](#part-4-verification)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have:

- **Okta Admin Access**: Super Administrator privileges in your Okta organization
- **GOTS Installed**: GOTS already set up on your system
- **Grafana Credentials**: Grafana API key ready (see main README for setup)

## Part 1: Create Custom Read-Only Admin Role

Creating a custom admin role ensures GOTS has the minimum permissions needed (principle of least privilege).

### Step 1.1: Access Admin Roles

1. **Log in to Okta Admin Console**: https://your-domain.okta.com/admin (e.g., https://ludia.okta.com/admin)

2. **Navigate to Security** → **Administrators** → **Roles**

3. **Click "Create Role"** or "Create custom role" button

### Step 1.2: Configure Role Permissions

1. **Role Name**: `Read-Only Group Administrator`

2. **Description**: `Read-only access to groups and users for GOTS synchronization`

3. **Select Permissions**:

   **Group Permissions:**
   - ✅ **View groups** - Check this box
   - ❌ **Manage groups** - Leave unchecked
   - ❌ **Create groups** - Leave unchecked
   - ❌ **Manage group membership** - Leave unchecked
   - ❌ **Edit group's application assignments** - Leave unchecked

   **User Permissions:**
   - ✅ **View users** - Check this box
   - ✅ **View users' group membership** - Check this box
   - ❌ **Manage users** - Leave unchecked
   - ❌ **Create users** - Leave unchecked
   - ❌ **Manage users' group membership** - Leave unchecked

   **Leave all other permissions unchecked**

4. **Click "Save"** or "Create"

### Step 1.3: Create Resource Set (If Prompted)

Some Okta versions require a resource set:

1. **Resource Set Name**: `All Groups and Users`

2. **Resources**:
   - Select **"All groups"**
   - Select **"All users"**

   Or restrict to specific groups if you only want to sync certain Okta groups.

3. **Click "Save"**

✅ **Checkpoint**: You've created a custom read-only admin role!

---

## Part 2: Create OAuth API Services Application

This section guides you through creating an OAuth application with `private_key_jwt` authentication.

### Step 2.1: Create New API Services App

1. **In Okta Admin Console**, navigate to **Applications** → **Applications**

2. **Click "Create App Integration"**

3. **Sign-in method**: Select **"API Services"**
   - This creates a service app for machine-to-machine (M2M) communication
   - This is NOT a web app or native app

4. **Click "Next"**

5. **App Integration Name**: `GOTS - Grafana Team Sync`
   - Or any descriptive name you prefer

6. **Click "Save"**

✅ **Checkpoint**: Your API Services app is created!

### Step 2.2: Configure Client Authentication Method

1. **In the application page**, click the **"General"** tab

2. **Scroll to "Client Credentials"** section

3. **Click "Edit"** button

4. **Client authentication**:
   - Select **"Public key / Private key"**
   - Do NOT select "Client secret"

5. **Click "Save"** (don't worry about the keys yet, we'll add them next)

### Step 2.3: Generate Public/Private Key Pair

**Recommended**: Let Okta generate the key pair for you (easiest and most secure method).

1. **Scroll to "PUBLIC KEYS"** section in the General tab

2. **Click "Add key"**

3. **Select "Generate new key"**
   - Okta will generate a secure RSA-2048 key pair

4. **Click "Generate"**

5. **Download the Private Key**:
   - ⚠️ **CRITICAL**: Click **"Download Private Key"** immediately
   - The private key is shown **only once** and cannot be retrieved later
   - Save as `private.pem` in your GOTS directory
   - Keep this file secure and never commit it to version control

6. **Note the Key ID (kid)**:
   - The public key will be displayed with a **kid** (Key ID) like: `eadE2YW30tucVX8l61Re-cNXAfeQVxq9U_LJ6SXpW00`
   - Copy this kid - you'll need it later (or you can retrieve it from the private key file)

7. **Click "Done"**

✅ **Checkpoint**: Public/private key pair generated and private key downloaded!

**Security Best Practices:**
- Store `private.pem` in a secure location (not in public git repositories)
- Set restrictive permissions: `chmod 600 private.pem`
- In production, use secrets management (Vault, AWS Secrets Manager, etc.)

### Step 2.4: Disable DPoP (Demonstrating Proof-of-Possession)

DPoP adds additional security but increases complexity. For most use cases, it's not needed.

1. **Still in the General tab**, scroll to **"Proof of Possession"** section

2. **DPoP**: If the option exists, set it to **"Disabled"** or ensure it's not enabled

3. **Click "Save"** if you made changes

✅ **Checkpoint**: DPoP is disabled!

**Note**: Some Okta orgs don't have DPoP configuration visible - that's fine, it's disabled by default.

### Step 2.5: Note Client ID

1. **In the General tab**, find the **"Client Credentials"** section

2. **Copy the Client ID**:
   - It looks like: `0oa1yr7t8z17ET9CX1d8`
   - Save this - you'll need it for GOTS configuration

✅ **Checkpoint**: Client ID copied!

### Step 2.6: Grant OAuth Scopes

OAuth applications need explicit scope grants to access Okta APIs.

1. **Click the "Okta API Scopes" tab**

2. **Click "Grant"** next to these scopes:
   - ✅ **`okta.groups.read`** - Read group information
   - ✅ **`okta.users.read`** - Read user information

3. **Verify the scopes show "Granted" status**

If you don't see these scopes, you may need to:
- Ensure you're using an **API Services App** (not Web App)
- Check with your Okta administrator to enable OAuth for Okta

✅ **Checkpoint**: OAuth scopes granted!

### Step 2.7: Assign Admin Role

**This is critical!** OAuth applications need an admin role to actually use the granted scopes.

1. **Click the "Admin Roles" tab** (or "Assignments" tab in some Okta versions)

2. **Click "Grant"** or "Add Role"

3. **Select the role you created**: `Read-Only Group Administrator`
   - Or select the built-in **"Read-Only Administrator"** if you prefer

4. **Click "Save"** or "Add"

5. **Verify the role shows as assigned**

✅ **Checkpoint**: Admin role assigned!

### Step 2.8: Summary - Application Configuration

Your OAuth application should now have:

- ✅ **Application type**: API Services
- ✅ **Client authentication**: Public key / Private key
- ✅ **Public key**: Registered (generated by Okta)
- ✅ **Private key**: Downloaded as `private.pem`
- ✅ **DPoP**: Disabled
- ✅ **OAuth scopes granted**: `okta.groups.read`, `okta.users.read`
- ✅ **Admin role assigned**: `Read-Only Group Administrator`
- ✅ **Client ID**: Copied and saved

---

## Part 3: Configure GOTS

Now configure GOTS to use OAuth authentication with your new application.

### Step 3.1: Prepare Configuration Files

1. **Navigate to your GOTS directory**:
   ```bash
   cd /path/to/gots
   ```

2. **Ensure you have the private key**:
   ```bash
   ls -l private.pem
   # Should show: -rw------- 1 user user 1704 ... private.pem
   ```

3. **Set secure permissions** (if not already set):
   ```bash
   chmod 600 private.pem
   ```

### Step 3.2: Configure config.yaml

Edit your `config.yaml` file:

```yaml
okta:
  domain: your-company.okta.com  # Replace with your Okta domain (e.g., ludia.okta.com)
  auth_method: oauth  # Use OAuth instead of api_token
  oauth:
    client_id: 0oa1yr7t8z17ET9CX1d8  # Replace with your Client ID from Step 2.5
    token_endpoint_auth_method: private_key_jwt  # Use JWT-based authentication
    private_key_path: private.pem  # Path to the private key file from Step 2.3
    scopes:
      - okta.groups.read  # Scope granted in Step 2.6
      - okta.users.read   # Scope granted in Step 2.6

grafana:
  url: https://grafana.example.com  # Your Grafana URL
  api_key: glsa_YourGrafanaAPIKey   # Your Grafana API key

sync:
  interval_seconds: 300  # Sync every 5 minutes
  dry_run: false         # Set to true for testing, false for actual sync
  mappings:
    - okta_group: "Engineering"      # Okta group name (case-sensitive)
      grafana_team: "Engineers"      # Grafana team name
    - okta_group: "DataScience"
      grafana_team: "Data Scientists"
  admin_groups:  # Optional: Groups for Grafana admin privileges
    - "GrafanaAdmins"
    - "IT-Leadership"

logging:
  level: INFO   # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: text  # json or text

metrics:
  enabled: false  # Set to true if you want Prometheus metrics
  port: 8000
  host: 0.0.0.0
```

### Step 3.3: Alternative - Using Environment Variables

You can also configure via environment variables (create `.env` file):

```bash
# Okta Configuration
OKTA_DOMAIN=your-company.okta.com
OKTA_AUTH_METHOD=oauth
OKTA_CLIENT_ID=0oa1yr7t8z17ET9CX1d8
OKTA_TOKEN_ENDPOINT_AUTH_METHOD=private_key_jwt
OKTA_PRIVATE_KEY_PATH=private.pem
OKTA_SCOPES=okta.groups.read,okta.users.read

# Grafana Configuration
GRAFANA_URL=https://grafana.example.com
GRAFANA_API_KEY=glsa_YourGrafanaAPIKey

# Sync Configuration
SYNC_INTERVAL_SECONDS=300
SYNC_DRY_RUN=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text

# Metrics (optional)
METRICS_ENABLED=false
METRICS_PORT=8000
```

### Step 3.4: Configuration Checklist

Verify your configuration has:

- ✅ **`okta.domain`**: Your Okta domain (without https://)
- ✅ **`okta.auth_method`**: Set to `oauth`
- ✅ **`okta.oauth.client_id`**: Client ID from your OAuth app
- ✅ **`okta.oauth.token_endpoint_auth_method`**: Set to `private_key_jwt`
- ✅ **`okta.oauth.private_key_path`**: Path to `private.pem`
- ✅ **`okta.oauth.scopes`**: Includes `okta.groups.read` and `okta.users.read`
- ✅ **`grafana.url`**: Your Grafana server URL
- ✅ **`grafana.api_key`**: Your Grafana API key
- ✅ **`sync.mappings`**: Your Okta group to Grafana team mappings
- ✅ **`sync.dry_run`**: Set to `true` for first test

---

## Part 4: Verification

Test your OAuth configuration to ensure everything works.

### Step 4.1: Test with Dry-Run Mode

1. **Set dry-run mode** in `config.yaml`:
   ```yaml
   sync:
     dry_run: true
   ```

2. **Run GOTS**:
   ```bash
   # If using CA bundle for SSL
   REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt poetry run python -m src.main

   # Or without CA bundle
   poetry run python -m src.main
   ```

3. **Check for successful authentication**:
   ```
   INFO:src.okta_client:Private key loaded from private.pem
   INFO:src.okta_client:OAuth token acquired successfully, expires in 3600 seconds
   INFO:src.okta_client:Granted scopes: ['okta.groups.read', 'okta.users.read']
   ```

4. **Verify sync preview**:
   ```
   INFO:src.sync_service:Starting sync: Engineering -> Engineers
   INFO:src.okta_client:Found Okta group: Engineering (ID: 00g...)
   INFO:src.okta_client:Found 25 members in group 00g...
   INFO:src.sync_service:Sync completed: +5 users, -2 users, 0 errors
   ```

✅ **Success!** If you see the above logs, OAuth is working correctly!

### Step 4.2: Run Actual Sync

Once dry-run looks good:

1. **Disable dry-run mode**:
   ```yaml
   sync:
     dry_run: false
   ```

2. **Run GOTS**:
   ```bash
   poetry run python -m src.main
   ```

3. **Monitor the logs**:
   ```
   INFO:src.sync_service:Added user john.doe@example.com to team Engineers
   INFO:src.sync_service:Sync completed: +5 users, -0 users, 0 errors
   ```

4. **Verify in Grafana**:
   - Log into Grafana
   - Go to Configuration → Teams
   - Check that team members match Okta group membership

✅ **Complete!** Your OAuth integration is working!

---

## Troubleshooting

### Issue: "Private key file not found"

**Error**: `FileNotFoundError: Private key file not found: private.pem`

**Solution**:
- Ensure `private.pem` is in the correct location
- Check the path in `private_key_path` configuration
- Use absolute path if needed: `/full/path/to/private.pem`

### Issue: "OAuth authentication failed - invalid client credentials"

**Error**: `OktaAuthenticationError: OAuth authentication failed - invalid client credentials`

**Possible causes**:
1. **Wrong Client ID**: Verify `client_id` matches the one in Okta
2. **Public key not registered**: Check the "Public Keys" section in Okta app
3. **Wrong private key**: Ensure you're using the private key that matches the public key in Okta

**Debug steps**:
```bash
# Run with debug logging
LOG_LEVEL=DEBUG poetry run python -m src.main
```

Look for JWT claims in the logs and verify they match your configuration.

### Issue: "The client does not have a JWKSet configured"

**Error**: `"error_description":"The client does not have a JWKSet configured, but the client_assertion requires one."`

**Solution**:
- The public key is not properly registered in Okta
- Go to Applications → Your App → General tab → Public Keys
- Ensure at least one public key is listed
- If not, go back to Step 2.3 and generate keys again

### Issue: "403 Forbidden - You are not authorized"

**Error**: `Okta API error: 403 - {"errorCode":"E0000006","errorSummary":"You are not authorized..."}`

**Causes**:
1. **OAuth scopes not granted**:
   - Go to Applications → Your App → Okta API Scopes
   - Verify `okta.groups.read` and `okta.users.read` show "Granted"

2. **Admin role not assigned** (most common):
   - Go to Applications → Your App → Admin Roles
   - Verify "Read-Only Group Administrator" is assigned
   - If not, see Step 2.7

3. **Scopes in token but grants missing**:
   - Run with `LOG_LEVEL=INFO` and check: `INFO:src.okta_client:Granted scopes: [...]`
   - If scopes are present but still 403, the admin role is missing

**Solution**: Assign the admin role (Step 2.7)

### Issue: "DPoP proof JWT header is missing"

**Error**: `"error":"invalid_dpop_proof","error_description":"The DPoP proof JWT header is missing."`

**Solution**:
- DPoP is enabled in your Okta app
- Go to Applications → Your App → General
- Find "Proof of Possession" or "DPoP" setting
- Disable it
- See Step 2.4

### Issue: Token expires and sync fails

**Symptom**: GOTS works initially but fails after 1 hour

**Cause**: Access token expired

**Solution**:
- This should auto-refresh (it's a bug if it doesn't)
- Check logs for "Acquiring new OAuth token from Okta"
- If not refreshing, restart GOTS as a temporary fix
- Report as a bug if the issue persists

### Issue: "Unsupported auth method"

**Error**: `"reason": "unsupported_auth_method_client_creds"`

**Cause**: Application type is "Public Client" instead of "API Services"

**Solution**:
- Create a new application using Step 2.1
- Ensure you select "API Services" (not Web App or Native App)
- Public clients cannot use `private_key_jwt`

---

## Security Best Practices

1. **Private Key Storage**:
   - Never commit `private.pem` to version control
   - Add to `.gitignore`: `echo "private.pem" >> .gitignore`
   - Use secrets management in production (Vault, AWS Secrets Manager, K8s secrets)

2. **File Permissions**:
   ```bash
   chmod 600 private.pem
   chown gots:gots private.pem  # Set appropriate ownership
   ```

3. **Principle of Least Privilege**:
   - Use custom "Read-Only Group Administrator" role
   - Don't use "Super Administrator" for GOTS

4. **Regular Key Rotation**:
   - Rotate keys every 90-180 days
   - Generate new key pair in Okta
   - Update `private.pem` in GOTS
   - Delete old public key from Okta after migration

5. **Monitor OAuth Access**:
   - Check Okta System Logs regularly
   - Look for "app.oauth2.token.grant" events
   - Alert on authentication failures

---

## Additional Resources

- **Okta OAuth Documentation**: https://developer.okta.com/docs/guides/implement-oauth-for-okta/main/
- **GOTS Documentation**:
  - [OKTA_ADMIN_ROLE_SETUP.md](OKTA_ADMIN_ROLE_SETUP.md) - Admin role details
  - [OKTA_OAUTH_SCOPES.md](OKTA_OAUTH_SCOPES.md) - Scope configuration
  - [OKTA_JWKSET_SETUP.md](OKTA_JWKSET_SETUP.md) - JWKSet details
  - [TROUBLESHOOTING_403.md](TROUBLESHOOTING_403.md) - 403 error guide
- **Main README**: Complete GOTS setup and usage guide

---

## Summary Checklist

Before running GOTS in production, ensure:

**Okta Configuration:**
- ✅ Custom "Read-Only Group Administrator" role created
- ✅ API Services application created
- ✅ Client authentication set to "Public key / Private key"
- ✅ Public/private key pair generated and downloaded
- ✅ DPoP disabled
- ✅ OAuth scopes granted: `okta.groups.read`, `okta.users.read`
- ✅ Admin role assigned to application
- ✅ Client ID noted and saved

**GOTS Configuration:**
- ✅ `private.pem` saved securely with correct permissions
- ✅ `config.yaml` updated with OAuth settings
- ✅ Client ID configured
- ✅ Private key path configured
- ✅ Grafana credentials configured
- ✅ Group mappings defined

**Testing:**
- ✅ Dry-run test completed successfully
- ✅ OAuth authentication verified (check logs)
- ✅ Scopes present in access token
- ✅ Actual sync tested and verified in Grafana

**Security:**
- ✅ Private key file permissions set to 600
- ✅ Private key not committed to version control
- ✅ Using read-only admin role (not Super Admin)

If all items are checked, you're ready for production! 🚀
