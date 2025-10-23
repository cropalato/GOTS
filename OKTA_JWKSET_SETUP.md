# Okta JWKSet Setup Guide for private_key_jwt Authentication

This guide explains how to configure your Okta OAuth application to use `private_key_jwt` authentication with JWKSet.

## Background

When using `private_key_jwt` as the token endpoint authentication method, Okta requires the public key to be registered in **JWKSet (JSON Web Key Set)** format. This allows Okta to verify the JWT assertions signed by your private key.

## Prerequisites

- An Okta OAuth application (API Services App or Web App)
- A generated RSA key pair (private.pem and public.pem)
- Admin access to your Okta organization

## Step 1: Convert Your Public Key to JWKSet Format

Run the provided conversion utility:

```bash
poetry run python convert_public_key_to_jwk.py public.pem
```

This will output:
1. A single JWK (for reference)
2. A JWKSet with the `keys` array (use this in Okta)

**Example output:**

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "gots-key-1",
      "use": "sig",
      "alg": "RS256",
      "n": "1PtXih...",
      "e": "AQAB"
    }
  ]
}
```

## Step 2: Configure JWKSet in Okta

### Option A: Via Okta Admin Console (Recommended)

1. Log in to **Okta Admin Console**: https://your-domain.okta.com/admin

2. Navigate to **Applications** > **Applications**

3. Find and click on your OAuth application

4. Click the **General** tab

5. Scroll to **CLIENT CREDENTIALS** section

6. Find **Public key / Private key** or **JSON Web Key Set** field

7. Select **Use JSON Web Key Set** (or similar option)

8. Paste the entire JWKSet JSON from Step 1

9. Verify **Token Endpoint Authentication Method** is set to **Private Key JWT**

10. Click **Save**

### Option B: Via Okta API

If configuring programmatically:

```bash
curl -X PUT "https://your-domain.okta.com/api/v1/apps/{appId}" \
  -H "Authorization: SSWS ${OKTA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "oauthClient": {
        "jwks": {
          "keys": [
            {
              "kty": "RSA",
              "kid": "gots-key-1",
              "use": "sig",
              "alg": "RS256",
              "n": "YOUR_MODULUS_HERE",
              "e": "AQAB"
            }
          ]
        },
        "token_endpoint_auth_method": "private_key_jwt"
      }
    }
  }'
```

## Step 3: Verify Configuration

After saving the JWKSet in Okta, verify:

1. **Token Endpoint Authentication Method**: Should be `private_key_jwt`
2. **JWKSet**: Should show your registered public key
3. **Client ID**: Note this down for your configuration

## Step 4: Configure GOTS

Update your `config.yaml` or environment variables:

### Using config.yaml:

```yaml
okta:
  domain: your-company.okta.com
  auth_method: oauth
  oauth:
    client_id: 0oa1yqsu3mwArPIXN1d8  # Your OAuth app client ID
    token_endpoint_auth_method: private_key_jwt
    private_key_path: /path/to/private.pem
    scopes:
      - okta.groups.read
      - okta.users.read
```

### Using environment variables:

```bash
export OKTA_DOMAIN=your-company.okta.com
export OKTA_AUTH_METHOD=oauth
export OKTA_CLIENT_ID=0oa1yqsu3mwArPIXN1d8
export OKTA_TOKEN_ENDPOINT_AUTH_METHOD=private_key_jwt
export OKTA_PRIVATE_KEY_PATH=/path/to/private.pem
export OKTA_SCOPES=okta.groups.read,okta.users.read
```

## Step 5: Test Authentication

Run GOTS with debug logging:

```bash
LOG_LEVEL=DEBUG poetry run python -m src.main
```

Look for successful authentication:

```
INFO:src.okta_client:Acquiring new OAuth token from Okta
DEBUG:src.okta_client:Using private_key_jwt authentication
DEBUG:src.okta_client:Token endpoint: https://your-domain.okta.com/oauth2/v1/token
INFO:src.okta_client:OAuth token acquired successfully, expires in 3600 seconds
```

## Troubleshooting

### Error: "The client does not have a JWKSet configured"

**Cause**: Public key not registered in Okta or registered in wrong format.

**Solution**:
- Verify JWKSet is configured in Okta OAuth app
- Ensure you pasted the entire `{"keys": [...]}` structure
- Check that `kid` in code matches `kid` in JWKSet

### Error: "Invalid client credentials"

**Possible causes**:
1. **Kid mismatch**: The `kid` in JWT header doesn't match JWKSet
   - Check `src/okta_client.py` has `kid: "gots-key-1"`
   - Verify JWKSet in Okta has same `kid`

2. **Wrong private key**: Private key doesn't match public key in JWKSet
   - Regenerate both keys if needed
   - Re-convert public key to JWKSet
   - Update JWKSet in Okta

3. **Client ID mismatch**: Config uses wrong client ID
   - Verify `OKTA_CLIENT_ID` matches Okta app

### Error: "JWT signature verification failed"

**Cause**: Public/private key mismatch or wrong algorithm.

**Solution**:
- Ensure you're using the correct key pair
- Verify algorithm is RS256 in both code and JWKSet
- Regenerate keys if necessary

## Key Management Best Practices

1. **Store private keys securely**: Use secrets management (Vault, K8s secrets, etc.)
2. **Rotate keys regularly**: Update JWKSet when rotating keys
3. **Use unique kid**: Use descriptive Key IDs (e.g., `gots-key-2025-01`)
4. **Multiple keys**: JWKSet supports multiple keys for rotation:

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "gots-key-current",
      "use": "sig",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB"
    },
    {
      "kty": "RSA",
      "kid": "gots-key-old",
      "use": "sig",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB"
    }
  ]
}
```

## Additional Resources

- [Okta OAuth 2.0 Documentation](https://developer.okta.com/docs/guides/implement-oauth-for-okta/main/)
- [RFC 7523: JWT Profile for OAuth 2.0 Client Authentication](https://datatracker.ietf.org/doc/html/rfc7523)
- [RFC 7517: JSON Web Key (JWK)](https://datatracker.ietf.org/doc/html/rfc7517)
