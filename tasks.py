import time
import asyncio
import math
from celery_app import celery_app

CPU_INTENSIVE_ITERATIONS = 1000000
IO_DELAY_SECONDS = 1


@celery_app.task(name="tasks.cpu_bound_sync")
def cpu_bound_sync_task(n: int = CPU_INTENSIVE_ITERATIONS) -> float:
    start_time = time.time()
    result = 0
    for i in range(n):
        result += math.sqrt(i) * math.sin(i)
    end_time = time.time()
    return end_time - start_time


@celery_app.task(name="tasks.cpu_bound_async")
def cpu_bound_async_task(n: int = CPU_INTENSIVE_ITERATIONS) -> float:
    async def _cpu_intensive():
        result = 0
        for i in range(n):
            result += math.sqrt(i) * math.sin(i)
        await asyncio.sleep(0)
        return result

    start_time = time.time()
    asyncio.run(_cpu_intensive())
    end_time = time.time()
    return end_time - start_time


@celery_app.task(name="tasks.io_bound_sync")
def io_bound_sync_task(delay: float = IO_DELAY_SECONDS) -> float:
    start_time = time.time()
    time.sleep(delay)
    end_time = time.time()
    return end_time - start_time


@celery_app.task(name="tasks.io_bound_async")
def io_bound_async_task(delay: float = IO_DELAY_SECONDS) -> float:
    async def _io_intensive():
        await asyncio.sleep(delay)

    start_time = time.time()
    asyncio.run(_io_intensive())
    end_time = time.time()
    return end_time - start_time

