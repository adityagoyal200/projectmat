import asyncio
import time
from collections.abc import Callable, Coroutine
from typing import Any


class AsyncTtlCache:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._values: dict[str, tuple[float, Any]] = {}
        self._inflight: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Coroutine[object, object, Any]],
    ) -> Any:
        now = time.monotonic()
        cached = self._values.get(key)
        if cached and cached[0] > now:
            return cached[1]

        async with self._lock:
            now = time.monotonic()
            cached = self._values.get(key)
            if cached and cached[0] > now:
                return cached[1]

            inflight = self._inflight.get(key)
            if inflight is None:
                inflight = asyncio.create_task(factory())
                self._inflight[key] = inflight

        try:
            value = await inflight
        finally:
            async with self._lock:
                current = self._inflight.get(key)
                if current is inflight:
                    self._inflight.pop(key, None)

        async with self._lock:
            self._values[key] = (time.monotonic() + self.ttl_seconds, value)

        return value

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            self._values.pop(key, None)
            self._inflight.pop(key, None)
