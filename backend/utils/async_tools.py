import asyncio
from typing import Callable


async def run_blocking(func: Callable, *args, timeout: float = 2.0, **kwargs):
    return await asyncio.wait_for(asyncio.to_thread(func, *args, **kwargs), timeout=timeout)
