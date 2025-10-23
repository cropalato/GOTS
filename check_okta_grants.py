#!/usr/bin/env python3
"""
Check Okta OAuth application grants.

This script checks if the OAuth application has the required grants
to access Okta APIs.
"""

import sys
import requests

# Configuration
CLIENT_ID = "0oa1yr7t8z17ET9CX1d8"  # Your OAuth app client ID
OKTA_DOMAIN = "ludia.okta.com"

# You need an Okta admin API token to check grants
# Get this from: Okta Admin Console > Security > API > Tokens > Create Token
ADMIN_API_TOKEN = input("Enter your Okta Admin API Token (or press Enter to skip): ").strip()

if not ADMIN_API_TOKEN:
    print("\n⚠️  No admin API token provided.")
    print("\nTo check grants, you need an Okta admin API token.")
    print("\nSteps to get one:")
    print("1. Go to https://ludia.okta.com/admin")
    print("2. Security > API > Tokens")
    print("3. Create Token")
    print("4. Save the token and run this script again")
    print("\nAlternatively, check via Admin Console:")
    print("1. Go to Applications > Applications")
    print(f"2. Click on app with Client ID: {CLIENT_ID}")
    print("3. Go to 'Okta API Scopes' tab")
    print("4. Verify both scopes show 'Granted' status:")
    print("   - okta.groups.read")
    print("   - okta.users.read")
    sys.exit(0)

# Check grants
url = f"https://{OKTA_DOMAIN}/api/v1/apps/{CLIENT_ID}/grants"
headers = {
    "Authorization": f"SSWS {ADMIN_API_TOKEN}",
    "Accept": "application/json"
}

print(f"\nChecking grants for app {CLIENT_ID}...")
print(f"URL: {url}\n")

try:
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 401:
        print("❌ Authentication failed. Check your admin API token.")
        sys.exit(1)

    if response.status_code == 404:
        print(f"❌ Application {CLIENT_ID} not found.")
        sys.exit(1)

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        sys.exit(1)

    grants = response.json()

    print(f"✅ Successfully retrieved grants!\n")
    print(f"Number of grants: {len(grants)}\n")

    if not grants:
        print("❌ NO GRANTS FOUND!")
        print("\nThis is the problem! The application has no grants.")
        print("\nTo fix this:")
        print("1. Go to https://ludia.okta.com/admin")
        print("2. Applications > Applications")
        print(f"3. Click on app: {CLIENT_ID}")
        print("4. Go to 'Okta API Scopes' tab")
        print("5. Click 'Grant' for:")
        print("   - okta.groups.read")
        print("   - okta.users.read")
    else:
        print("Grants found:\n")
        required_scopes = {"okta.groups.read", "okta.users.read"}
        granted_scopes = set()

        for grant in grants:
            scope_id = grant.get("scopeId", "unknown")
            status = grant.get("status", "unknown")
            issuer = grant.get("issuer", "unknown")
            grant_id = grant.get("id", "unknown")

            status_symbol = "✅" if status == "ACTIVE" else "❌"
            print(f"{status_symbol} Scope: {scope_id}")
            print(f"   Status: {status}")
            print(f"   Issuer: {issuer}")
            print(f"   Grant ID: {grant_id}\n")

            if status == "ACTIVE":
                granted_scopes.add(scope_id)

        missing_scopes = required_scopes - granted_scopes

        if missing_scopes:
            print(f"\n❌ Missing required scopes: {missing_scopes}")
            print("\nYou need to grant these scopes in Okta Admin Console.")
        else:
            print("\n✅ All required scopes are granted!")
            print("\nIf you're still getting 403 errors, try:")
            print("1. Wait a few minutes for Okta to propagate the grants")
            print("2. Get a new access token (restart GOTS)")
            print("3. Check if the application is the correct type (API Services App)")

except requests.RequestException as e:
    print(f"❌ Request failed: {e}")
    sys.exit(1)
