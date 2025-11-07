#!/usr/bin/env python3
"""
Secure token generator for API authentication and webhook secrets.

This script generates cryptographically secure random tokens
for use in API_TOKEN and WEBHOOK_SECRET environment variables.

Usage:
    python scripts/generate_token.py
    python scripts/generate_token.py --length 64
    python scripts/generate_token.py --type webhook
    python scripts/generate_token.py --both
"""

import argparse
import secrets
import string


def generate_token(length: int = 32, charset: str = "all") -> str:
    """Generate a cryptographically secure random token.

    Args:
        length: Length of the token (minimum 16)
        charset: Character set to use ('all', 'alphanumeric', 'hex')

    Returns:
        Secure random token string

    Raises:
        ValueError: If length is too short
    """
    if length < 16:
        raise ValueError("Token length must be at least 16 characters")

    if charset == "hex":
        # Generate hex token (0-9, a-f)
        return secrets.token_hex(length // 2)
    elif charset == "alphanumeric":
        # Generate alphanumeric token (a-z, A-Z, 0-9)
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))
    else:  # 'all'
        # Generate token with letters, digits, and safe punctuation
        alphabet = string.ascii_letters + string.digits + "-_"
        return "".join(secrets.choice(alphabet) for _ in range(length))


def main():
    """Main entry point for token generator."""
    parser = argparse.ArgumentParser(
        description="Generate secure tokens for API authentication and webhooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate API token (32 characters)
  python scripts/generate_token.py --type api

  # Generate webhook secret (64 characters)
  python scripts/generate_token.py --type webhook

  # Generate both tokens
  python scripts/generate_token.py --both

  # Generate custom length token
  python scripts/generate_token.py --length 128

  # Generate hex token
  python scripts/generate_token.py --charset hex

Recommended configuration:
  - API_TOKEN: 32-64 characters (all charset)
  - WEBHOOK_SECRET: 32-64 characters (all charset)
        """,
    )

    parser.add_argument(
        "--length",
        type=int,
        default=None,
        help="Token length in characters (default: 32 for API, 64 for webhook)",
    )

    parser.add_argument(
        "--type",
        choices=["api", "webhook"],
        default=None,
        help="Type of token to generate",
    )

    parser.add_argument(
        "--both",
        action="store_true",
        help="Generate both API token and webhook secret",
    )

    parser.add_argument(
        "--charset",
        choices=["all", "alphanumeric", "hex"],
        default="all",
        help="Character set to use (default: all)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Output only the token (for scripting)",
    )

    args = parser.parse_args()

    # Determine what to generate
    if args.both:
        # Generate both tokens
        api_length = args.length if args.length else 32
        webhook_length = args.length if args.length else 64

        api_token = generate_token(api_length, args.charset)
        webhook_secret = generate_token(webhook_length, args.charset)

        if args.quiet:
            print(api_token)
            print(webhook_secret)
        else:
            print("=" * 70)
            print("SECURE TOKEN GENERATION")
            print("=" * 70)
            print()
            print("API Token (add to .env as API_TOKEN):")
            print(f"  {api_token}")
            print()
            print("Webhook Secret (add to .env as WEBHOOK_SECRET):")
            print(f"  {webhook_secret}")
            print()
            print("=" * 70)
            print("IMPORTANT:")
            print("  1. Copy these tokens to your .env file")
            print("  2. Never commit these tokens to version control")
            print("  3. Keep these tokens secret and secure")
            print("  4. Regenerate tokens if compromised")
            print("=" * 70)

    elif args.type:
        # Generate specific token type
        if args.type == "api":
            length = args.length if args.length else 32
            token = generate_token(length, args.charset)
            label = "API_TOKEN"
        else:  # webhook
            length = args.length if args.length else 64
            token = generate_token(length, args.charset)
            label = "WEBHOOK_SECRET"

        if args.quiet:
            print(token)
        else:
            print("=" * 70)
            print(f"{label} Generation")
            print("=" * 70)
            print()
            print(f"Generated {label} ({length} characters):")
            print(f"  {token}")
            print()
            print("Add to your .env file:")
            print(f"  {label}={token}")
            print()
            print("=" * 70)

    else:
        # Default: generate generic token
        length = args.length if args.length else 32
        token = generate_token(length, args.charset)

        if args.quiet:
            print(token)
        else:
            print("=" * 70)
            print(f"Secure Token ({length} characters):")
            print(f"  {token}")
            print("=" * 70)


if __name__ == "__main__":
    main()
