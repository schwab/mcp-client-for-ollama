"""Nextcloud authentication provider using OCS API."""

import requests
from datetime import datetime, timedelta
from typing import Optional, Dict
from flask import Request


class NextcloudAuthProvider:
    """Authenticates users via Nextcloud OCS API.

    Uses HTTP Basic Auth credentials to validate against Nextcloud's
    OCS API endpoint. Caches validation results to reduce API calls.
    """

    def __init__(self, nextcloud_url: str, cache_ttl_minutes: int = 5):
        """Initialize the Nextcloud auth provider.

        Args:
            nextcloud_url: Base URL of Nextcloud instance (e.g., https://nextcloud.example.com)
            cache_ttl_minutes: How long to cache validation results (default: 5 minutes)
        """
        self.nextcloud_url = nextcloud_url.rstrip('/')
        self.ocs_endpoint = f"{self.nextcloud_url}/ocs/v1.php/cloud/user"
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)

        # Cache: {(username, password): (validated_username, expiry_time)}
        self.auth_cache: Dict[tuple, tuple] = {}

    def validate_credentials(self, username: str, password: str) -> Optional[str]:
        """Validate credentials against Nextcloud OCS API.

        Args:
            username: Nextcloud username
            password: Nextcloud password or app password

        Returns:
            Validated username if credentials are valid, None otherwise
        """
        # Check cache first
        cache_key = (username, password)
        if cache_key in self.auth_cache:
            cached_user, expiry = self.auth_cache[cache_key]
            if datetime.now() < expiry:
                return cached_user
            else:
                # Expired entry, remove it
                del self.auth_cache[cache_key]

        # Call Nextcloud OCS API to validate credentials
        try:
            response = requests.get(
                self.ocs_endpoint,
                auth=(username, password),
                headers={'OCS-APIRequest': 'true'},
                timeout=10
            )

            if response.status_code == 200:
                # Parse OCS response
                data = response.json()
                if 'ocs' in data and 'data' in data['ocs']:
                    validated_username = data['ocs']['data'].get('id')
                    if validated_username:
                        # Cache the successful validation
                        expiry = datetime.now() + self.cache_ttl
                        self.auth_cache[cache_key] = (validated_username, expiry)
                        return validated_username

            return None

        except requests.RequestException as e:
            print(f"Nextcloud auth error: {e}")
            return None

    def get_current_user(self, request: Request) -> Optional[str]:
        """Extract and validate user from request Authorization header.

        Args:
            request: Flask request object

        Returns:
            Validated username if authentication succeeds, None otherwise
        """
        auth = request.authorization
        if not auth or not auth.username or not auth.password:
            return None

        return self.validate_credentials(auth.username, auth.password)

    def clear_cache(self):
        """Clear the authentication cache."""
        self.auth_cache.clear()

    def cleanup_expired_cache(self):
        """Remove expired entries from the cache."""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expiry) in self.auth_cache.items()
            if now >= expiry
        ]
        for key in expired_keys:
            del self.auth_cache[key]
