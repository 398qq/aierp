"""Shared ERP auth helper for standalone scripts.

Usage:
    from lib.erp_auth import get_erp_creds
    USERNAME, PASSWORD = get_erp_creds()
"""

import os
import sys


def get_erp_creds() -> tuple[str, str]:
    """Read ERP login credentials from environment variables.

    Returns (username, password).
    Exits with a fatal error message if AIERP_LOGIN_PASSWORD is not set.
    """
    username = os.getenv("AIERP_LOGIN_USERNAME", "admin")
    password = os.environ.get("AIERP_LOGIN_PASSWORD")
    if not password:
        print(
            "FATAL: AIERP_LOGIN_PASSWORD environment variable is required",
            file=sys.stderr,
        )
        sys.exit(1)
    return username, password
