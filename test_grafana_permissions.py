#!/usr/bin/env python3
"""Test script to verify Grafana API permissions."""
import sys
import requests


def test_grafana_permissions(base_url: str, api_key: str) -> None:
    """Test all required Grafana API endpoints."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    tests = [
        {
            "name": "Health Check",
            "endpoint": "/api/health",
            "method": "GET",
            "required": True,
            "permission": "none (public)",
        },
        {
            "name": "Teams Search",
            "endpoint": "/api/teams/search",
            "method": "GET",
            "required": True,
            "permission": "teams:read",
        },
        {
            "name": "User Lookup",
            "endpoint": "/api/users/lookup?loginOrEmail=admin",
            "method": "GET",
            "required": True,
            "permission": "users:read",
        },
        {
            "name": "Admin - List Users",
            "endpoint": "/api/org/users",
            "method": "GET",
            "required": False,
            "permission": "org.users:read",
        },
        {
            "name": "Service Account Info",
            "endpoint": "/api/serviceaccounts/search?orgId=1",
            "method": "GET",
            "required": False,
            "permission": "serviceaccounts:read",
        },
    ]

    print(f"\n{'='*80}")
    print(f"Testing Grafana API Permissions")
    print(f"URL: {base_url}")
    print(f"{'='*80}\n")

    passed = 0
    failed = 0

    for test in tests:
        endpoint = test["endpoint"]
        url = f"{base_url}{endpoint}"

        try:
            if test["method"] == "GET":
                response = requests.get(url, headers=headers, timeout=10, verify=True)
            else:
                response = requests.post(url, headers=headers, timeout=10, verify=True)

            if response.status_code in (200, 201):
                status = "✓ PASS"
                passed += 1
                color = "\033[92m"  # Green
            elif response.status_code == 404:
                status = "⚠ WARN (404 - endpoint or resource not found)"
                if test["required"]:
                    failed += 1
                color = "\033[93m"  # Yellow
            elif response.status_code in (401, 403):
                status = "✗ FAIL (Permission Denied)"
                if test["required"]:
                    failed += 1
                color = "\033[91m"  # Red
                try:
                    error_msg = response.json().get("message", "")
                    if error_msg:
                        status += f"\n      Message: {error_msg}"
                except Exception:
                    pass
            else:
                status = f"? UNKNOWN (HTTP {response.status_code})"
                if test["required"]:
                    failed += 1
                color = "\033[93m"  # Yellow

        except requests.exceptions.SSLError as e:
            status = f"✗ SSL ERROR: {e}"
            if test["required"]:
                failed += 1
            color = "\033[91m"  # Red
        except Exception as e:
            status = f"✗ ERROR: {e}"
            if test["required"]:
                failed += 1
            color = "\033[91m"  # Red

        reset = "\033[0m"
        required_marker = "[REQUIRED]" if test["required"] else "[OPTIONAL]"

        print(f"{color}{status}{reset}")
        print(f"  Test: {test['name']} {required_marker}")
        print(f"  Endpoint: {endpoint}")
        print(f"  Permission: {test['permission']}")
        print()

    print(f"{'='*80}")
    print(f"Summary: {passed} passed, {failed} failed (required)")
    print(f"{'='*80}\n")

    if failed > 0:
        print("\033[91m✗ FAILED: Service account is missing required permissions\033[0m")
        print("\nTo fix:")
        print("1. Go to Grafana UI → Administration → Service Accounts")
        print("2. Find your service account")
        print("3. Check the 'Permissions' tab and ensure it has:")
        print("   - users:read")
        print("   - users:write (for creating users)")
        print("   - teams:read")
        print("   - teams:write (for adding members)")
        sys.exit(1)
    else:
        print("\033[92m✓ SUCCESS: All required permissions are granted\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    import yaml

    # Load from config.yaml
    with open("/home/rmelo/git/cropalato/gots/config.yaml") as f:
        config = yaml.safe_load(f)

    base_url = config["grafana"]["url"].rstrip("/")
    api_key = config["grafana"]["api_key"]

    test_grafana_permissions(base_url, api_key)
