#!/usr/bin/env python3
"""Convert RSA public key PEM file to JWK format for Okta."""

import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import base64


def int_to_base64url(value: int) -> str:
    """Convert integer to base64url-encoded string."""
    # Convert to bytes, padding to ensure correct length
    value_bytes = value.to_bytes((value.bit_length() + 7) // 8, byteorder='big')
    # Base64url encode (no padding)
    return base64.urlsafe_b64encode(value_bytes).decode('utf-8').rstrip('=')


def convert_pem_to_jwk(public_key_path: str, kid: str = "gots-key-1") -> dict:
    """
    Convert RSA public key PEM to JWK format.

    Args:
        public_key_path: Path to public key PEM file
        kid: Key ID to use in JWK (default: gots-key-1)

    Returns:
        Dictionary containing JWK representation
    """
    # Read public key from PEM file
    with open(public_key_path, 'rb') as f:
        public_key = serialization.load_pem_public_key(
            f.read(),
            backend=default_backend()
        )

    # Ensure it's an RSA key
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("Only RSA keys are supported")

    # Get public numbers
    public_numbers = public_key.public_numbers()

    # Create JWK
    jwk = {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": int_to_base64url(public_numbers.n),
        "e": int_to_base64url(public_numbers.e),
    }

    return jwk


def create_jwks(public_key_path: str, kid: str = "gots-key-1") -> dict:
    """
    Create a JWKSet with a single public key.

    Args:
        public_key_path: Path to public key PEM file
        kid: Key ID to use in JWK

    Returns:
        Dictionary containing JWKSet (with keys array)
    """
    jwk = convert_pem_to_jwk(public_key_path, kid)
    return {"keys": [jwk]}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_public_key_to_jwk.py <public_key.pem> [kid]")
        print("\nExample:")
        print("  python convert_public_key_to_jwk.py public.pem")
        print("  python convert_public_key_to_jwk.py public.pem my-key-id")
        sys.exit(1)

    public_key_file = sys.argv[1]
    key_id = sys.argv[2] if len(sys.argv) > 2 else "gots-key-1"

    if not Path(public_key_file).exists():
        print(f"Error: File not found: {public_key_file}")
        sys.exit(1)

    try:
        # Generate single JWK
        jwk = convert_pem_to_jwk(public_key_file, key_id)
        print("\n=== Single JWK (for reference) ===")
        print(json.dumps(jwk, indent=2))

        # Generate JWKSet
        jwks = create_jwks(public_key_file, key_id)
        print("\n=== JWKSet (use this in Okta) ===")
        print(json.dumps(jwks, indent=2))

        print("\n=== Instructions ===")
        print("1. Copy the JWKSet JSON above (the one with 'keys' array)")
        print("2. Go to Okta Admin Console > Applications > Your OAuth App")
        print("3. Edit the application settings")
        print("4. Find 'Client Credentials' or 'JWKSet' section")
        print("5. Paste the JWKSet JSON")
        print("6. Save the application")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
