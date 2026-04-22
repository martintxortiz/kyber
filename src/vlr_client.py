from __future__ import annotations

import time
import urllib.error
import urllib.request


class VLRClient:
    def __init__(self, max_requests_per_minute: int, retry_count: int, retry_backoff_seconds: int) -> None:
        self.max_requests_per_minute = max_requests_per_minute
        self.retry_count = retry_count
        self.retry_backoff_seconds = retry_backoff_seconds
        self._minimum_interval = 60.0 / max_requests_per_minute
        self._last_request_at = 0.0
        self._headers = {
            "User-Agent": "valorant-vct-predictor-phase1/1.0",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._minimum_interval:
            time.sleep(self._minimum_interval - elapsed)

    def fetch(self, url: str, timeout_seconds: int = 30) -> str:
        last_error: Exception | None = None
        total_attempts = self.retry_count + 1

        for attempt in range(1, total_attempts + 1):
            self._throttle()
            request = urllib.request.Request(url, headers=self._headers)
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    self._last_request_at = time.monotonic()
                    charset = response.headers.get_content_charset("utf-8")
                    return response.read().decode(charset, errors="replace")
            except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as exc:
                self._last_request_at = time.monotonic()
                last_error = exc
                if attempt >= total_attempts:
                    break
                time.sleep(self.retry_backoff_seconds * attempt)

        raise RuntimeError(f"Request failed for {url}: {last_error}")
