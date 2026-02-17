# Diagnosing Task Types and Choosing the Right Concurrency Model for Celery

## Overview

In Django apps, Celery handles both I/O-bound work (APIs, S3, Postgres, email) and CPU-bound work (PDFs, encoding, ETL). Put both on the same worker pool with the wrong concurrency model, and throughput suffers: CPU-heavy tasks block I/O-heavy ones or the other way around, leading to queue buildup and long tail latencies. Real workflows are often **mixed**—fetch data (I/O), process it (CPU), then write elsewhere (I/O)—so picking a pool can get tricky.

We focus here on the **extremes**: purely I/O-bound and purely CPU-bound tasks. That lets us compare worker pools (prefork, gevent) and concurrency settings without the extra complexity; understanding how each pool behaves at the extremes makes it easier to reason about mixed workloads. You’ll see how to tell what type of work you have, pick a matching pool, and we back it up with benchmarks.

---

## 01 — I/O-bound vs CPU-bound: know your bottleneck

### The problem: one pool for everything

Tasks are either **I/O-bound** or **CPU-bound**. I/O-bound tasks spend most of their time waiting on external resources (APIs, DB, disk)—HTTP calls, DB writes, image downloads. The bottleneck is network or disk, not CPU. CPU-bound tasks do heavy computation (video encoding, number crunching); the bottleneck is processor speed and core count.

If you run both kinds on the same pool with the same concurrency model, you either waste CPU (I/O tasks leave cores idle) or serialize I/O (CPU tasks block workers). Getting the model wrong is one of the fastest ways to turn “it works on my machine” into “why is production so slow?”

### Diagnosing your tasks

- **I/O-bound:** Task runtime drops when the external resource gets faster (e.g. a faster API or DB). Code often uses blocking calls like `requests.get()` or sync DB drivers; workers show long idle periods in Flower or `celery inspect`.
- **CPU-bound:** Runtime stays similar when the resource improves; CPU usage spikes. Code runs tight loops or heavy algorithms; workers stay busy.

Quick check: if removing or mocking the external call makes the task almost instant, it’s I/O-bound. If it stays slow, it’s CPU-bound.

---

## 02 — Worker pools: prefork, gevent, threads

### Matching the pool to the task

| Pool       | Model           | Best for      | GIL / cores |
|-----------|------------------|---------------|-------------|
| **prefork** | Multi-process   | CPU-bound     | Avoids GIL, one process per core |
| **gevent** / **eventlet** | Greenlets (cooperative) | I/O-bound | Single process; concurrency can be high |
| **threads** | OS threads      | Blocking I/O, some C-extensions | GIL limits pure Python CPU |
| **solo**   | Single-threaded | Debugging only | N/A |

- **Prefork:** Default. Fits CPU-bound work; use `--concurrency` around CPU core count and tune from there. Higher concurrency = more memory.
- **Gevent / Eventlet:** Fit I/O-bound work. Greenlets are cheap; you can often use tens or hundreds. They optimize *blocking* I/O (`requests`, sync DB drivers). If your code is already **async** (`asyncio`, `aiohttp`), gevent does *not* run asyncio coroutines—use prefork or threads instead.
- **Rule of thumb:** `gevent`/`eventlet` for blocking I/O tasks only; prefork for CPU-heavy or already-async I/O.

### Example: defining task types in code

```python
# I/O-bound (sync): blocking network call
@celery_app.task
def fetch_external_data(url: str) -> dict:
    return requests.get(url, timeout=10).json()

# I/O-bound (async): non-blocking with aiohttp; use prefork or threads, not gevent
@celery_app.task
def fetch_external_data_async(urls: list[str]) -> list[dict]:
    async def _fetch():
        async with aiohttp.ClientSession() as session:
            tasks = [session.get(u, timeout=aiohttp.ClientTimeout(total=10)) for u in urls]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            return [await r.json() if not isinstance(r, Exception) else {} for r in responses]
    return asyncio.run(_fetch())

# CPU-bound: tight loop, no external wait
@celery_app.task
def heavy_compute(n: int) -> int:
    return sum(range(10**n))
```

Same Celery app, different bottlenecks—so they benefit from different pools and concurrency settings.

---

## 03 — Benchmark setup and results

### Benchmark setup

Two task types, same repo:

- **I/O-bound:** `requests.get("https://httpbin.org/delay/1")` — ~1s wait per task.
- **CPU-bound:** `sum(range(10**7))` — pure CPU, no I/O.

Worker commands:

```bash
# CPU-bound: prefork, 4 processes (e.g. 4 cores)
celery -A celery_app worker --pool=prefork --concurrency=4

# I/O-bound: gevent, many greenlets
celery -A celery_app worker --pool=gevent --concurrency=10
# or higher, e.g. --concurrency=100
```

`-A` points to the Celery app module; `--pool` selects processes vs greenlets vs threads; `--concurrency` sets pool size.

### CPU-bound results

Prefork (sync or async, `concurrency = 4`) finishes in ~45–46s.
Gevent (any concurrency) takes ~175s because greenlets run in a single process and don’t use multiple cores—so CPU-bound work doesn’t scale with gevent.

**Conclusion:** Use **prefork** for CPU-heavy or when your code is async already.



![Celery benchmark - CPU bound](https://i.imgur.com/VSEVvEj.png)

*CPU-bound: prefork (concurrency = 4) vs gevent; prefork wins by a large margin.*

### I/O-bound results

Sync prefork concurrency = 4 is slow (~2623s). Sync gevent concurrency = 4 is better (~954s); sync gevent concurrency = 100 is fastest (~39.5s).
Async prefork concurrency = 4 is competitive (~51.6s)—if your code is already async, prefork can handle I/O-bound work well without switching to gevent.

**Conclusion:** Use **gevent** (or eventlet) with higher concurrency for blocking I/O; if you’re already async, prefork with a few workers can be enough.

![Celery benchmark - I/O bound](https://i.imgur.com/Dr5NfPh.png)

*I/O-bound: prefork vs gevent at different concurrency levels; gevent scales with greenlet count.*

---

## 04 — Takeaways and what to do next

Match the pool to the task: **gevent** for sync I/O-heavy code (APIs, DB, blocking HTTP), **prefork** for CPU-heavy (data processing, encoding, math) or async code. Use **Flower** or `celery inspect` and `top`/`htop` to confirm workers are busy when you expect and idle when they’re waiting on I/O. Avoid over-threading; high gevent concurrency can starve CPU-bound work if mixed in the same deployment.

When in doubt, run a small benchmark with your real task shape—same style as above—and measure. A few minutes of setup can save hours of production debugging.

---

## Links

- **Benchmark repo:** https://github.com/valdife/celery_worker_benchmark
- **Celery docs:** https://docs.celeryq.dev/
- **Flower:** https://flower.readthedocs.io/
- **Gevent:** https://www.gevent.org/
- **Eventlet:** https://eventlet.net/
- **Python GIL:** https://docs.python.org/3/glossary.html#term-global-interpreter-lock
