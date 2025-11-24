import time
import asyncio
import math
import requests
import aiohttp
from celery_app import celery_app

CPU_INTENSIVE_ITERATIONS = 1000000
NUM_HTTP_REQUESTS = 20
HTTP_TIMEOUT = 2


def _cpu_intensive_work(n: int) -> float:
    result = 0
    for i in range(n):
        result += math.sqrt(i) * math.sin(i) * math.cos(i)
    return result


@celery_app.task(name="tasks.cpu_bound_sync")
def cpu_bound_sync_task(n: int = CPU_INTENSIVE_ITERATIONS) -> float:
    start_time = time.time()
    data = []
    for i in range(10):
        processed = _cpu_intensive_work(n // 10)
        data.append(processed)

    result = sum(data) / len(data)
    end_time = time.time()
    return end_time - start_time


@celery_app.task(name="tasks.cpu_bound_async")
def cpu_bound_async_task(n: int = CPU_INTENSIVE_ITERATIONS) -> float:
    async def _cpu_intensive():
        data = []
        for i in range(10):
            processed = _cpu_intensive_work(n // 10)
            data.append(processed)
            await asyncio.sleep(0)
        return sum(data) / len(data)

    start_time = time.time()
    asyncio.run(_cpu_intensive())
    end_time = time.time()
    return end_time - start_time


@celery_app.task(name="tasks.io_bound_sync")
def io_bound_sync_task(num_requests: int = NUM_HTTP_REQUESTS) -> float:
    start_time = time.time()

    for i in range(num_requests):
        try:
            response = requests.get(
                "https://httpbin.org/delay/1",
                timeout=HTTP_TIMEOUT
            )
            response.raise_for_status()
        except Exception:
            pass

    end_time = time.time()
    return end_time - start_time


@celery_app.task(name="tasks.io_bound_async")
def io_bound_async_task(num_requests: int = NUM_HTTP_REQUESTS) -> float:
    async def _io_intensive():
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_requests):
                task = session.get(
                    "https://httpbin.org/delay/1",
                    timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for response in responses:
                if isinstance(response, aiohttp.ClientResponse):
                    response.close()

    start_time = time.time()
    asyncio.run(_io_intensive())
    end_time = time.time()
    return end_time - start_time
