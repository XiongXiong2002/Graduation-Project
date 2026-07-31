import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import HTTPException


load_dotenv()


def get_positive_int_env(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        parsed_value = int(value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error

    if parsed_value <= 0:
        raise RuntimeError(f"{name} must be greater than 0")

    return parsed_value


class AIRateLimiter:
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_times: dict[int, list[datetime]] = defaultdict(list)

    def check(self, user_id: int):
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_seconds)
        self.request_times[user_id] = [time for time in self.request_times[user_id] if time > window_start]

        if len(self.request_times[user_id]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Too many requests, please try again later")

        self.request_times[user_id].append(now)

ai_rate_limiter = AIRateLimiter(
    max_requests=get_positive_int_env("MAX_limit", 5),
    window_seconds=get_positive_int_env("PER_REQUEST_TIME", 60),
)
