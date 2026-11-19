"""Password hashing, JWT tokens, and rate limiting."""

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from jwt import InvalidTokenError

from app.core.config import get_settings


def hash_password(password: str) -> str:
    """Hash a password using scrypt with a random 16-byte salt."""
    salt = secrets.token_hex(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )
    return f"scrypt${salt}${derived.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a plain-text password against a stored scrypt hash."""
    try:
        scheme, salt, hex_digest = stored_hash.split("$", 2)
        if scheme != "scrypt":
            return False
        expected = bytes.fromhex(hex_digest)
        actual = hashlib.scrypt(
            plain_password.encode("utf-8"),
            salt=salt.encode("utf-8"),
            n=16384,
            r=8,
            p=1,
            dklen=32,
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, extra: Optional[dict[str, Any]] = None) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT access token; return None if invalid."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except InvalidTokenError:
        return None


class RateLimiter:
    """Sliding-window rate limiter backed by Redis when configured, else in-memory."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._redis = None
        self._redis_checked = False

    def _get_redis(self):
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        settings = get_settings()
        if settings.REDIS_URL:
            try:
                import redis

                client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1)
                client.ping()
                self._redis = client
            except Exception:
                self._redis = None
        return self._redis

    def check_and_record(self, key: str, max_attempts: int, window_seconds: int) -> tuple[bool, int]:
        """Check whether `key` is within the rate limit and record the attempt.

        Returns `(allowed, retry_after_seconds)`.
        """
        r = self._get_redis()
        if r is not None:
            try:
                pipe = r.pipeline()
                now = time.time()
                window_start = now - window_seconds
                redis_key = f"rl:{key}"
                pipe.zremrangebyscore(redis_key, 0, window_start)
                pipe.zcard(redis_key)
                _, current_count = pipe.execute()
                if current_count >= max_attempts:
                    oldest = r.zrange(redis_key, 0, 0, withscores=True)
                    retry_after = int(max(1, window_seconds - (now - oldest[0][1]))) if oldest else window_seconds
                    return False, retry_after
                r.zadd(redis_key, {f"{now}:{secrets.token_hex(4)}": now})
                r.expire(redis_key, window_seconds)
                return True, 0
            except Exception:
                pass

        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            cutoff = now - window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= max_attempts:
                retry_after = int(max(1, window_seconds - (now - bucket[0])))
                return False, retry_after
            bucket.append(now)
            return True, 0

    def reset(self, key: str) -> None:
        """Clear rate-limit history for a key (e.g., after successful login or tests)."""
        r = self._get_redis()
        if r is not None:
            try:
                r.delete(f"rl:{key}")
            except Exception:
                pass
        with self._lock:
            self._buckets.pop(key, None)


rate_limiter = RateLimiter()
