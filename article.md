### How to diagnose task types and choose the right concurrency model for optimal Celery workflows.

**Why this matters**

In a Django app, Celery might handle both I/O-bound work (APIs, S3, Postgres, email) and CPU-bound work (PDFs, media encoding, ETL). If both share the same worker pool, the wrong choice can tank throughput: CPU-heavy tasks block I/O-heavy ones or the other way around, causing queue buildup and long tail latencies. The goal is to quickly tell what type of work you have and pick a pool that matches.

**I/O-bound vs CPU-bound**

Tasks are either I/O-bound or CPU-bound. I/O-bound tasks spend most of their time waiting on external resources (APIs, DB, disk); examples are HTTP calls, DB writes, image downloads. The bottleneck is network or disk, not CPU. CPU-bound tasks do heavy computation (video encoding, math); the bottleneck is processor speed and core count.

**Diagnosing your tasks**

If task runtime drops when the external resource gets faster (e.g. a faster API), it’s I/O-bound. If runtime stays similar but CPU usage spikes, it’s CPU-bound. I/O-bound code often uses blocking calls like `requests.get()` or DB drivers; CPU-bound code runs loops or heavy algorithms. Tools like Flower or `celery inspect` help: I/O tasks show long idle periods, CPU tasks keep workers busy.

**Worker pools**

Prefork (multi-process, default) fits CPU-bound work and avoids the GIL but uses more memory. Gevent and Eventlet use cooperative greenlets and fit I/O-bound work; they don’t help pure CPU work. Threads can work for blocking I/O and some C-extension workloads; pure Python CPU work still hits the GIL. Solo is single-threaded and for debugging only.

For CPU-bound on prefork, start with concurrency around the number of CPU cores and tune from there. For I/O-bound on gevent/eventlet, you can often use much higher concurrency (tens or hundreds), since greenlets are cheap and most time is waiting. Note: gevent/eventlet optimize blocking I/O (e.g. `requests`, sync DB drivers). If your code is already async (asyncio, `aiohttp`), stick to prefork (or threads)—gevent does not run asyncio coroutines, so it won’t help. Use gevent/eventlet for blocking I/O tasks only.

**Benchmark setup**

Example tasks: an I/O-bound task that calls `requests.get("https://httpbin.org/delay/1")`, and a CPU-bound task that runs a tight loop (e.g. `sum(range(10**7))`). Workers: `celery -A celery_app worker --pool=prefork --concurrency=4` for prefork; `celery -A celery_app worker --pool=gevent --concurrency=10` for gevent. `-A` points to the Celery app module, `--pool` selects processes/greenlets/threads, `--concurrency` sets pool size.

**Takeaways**

Match the pool to the task: gevent for I/O-heavy (APIs, DB), prefork for CPU-heavy (data processing, math). Monitor with `top`/`htop` and Flower. Avoid over-threading; high gevent concurrency can starve CPU-bound work.

**Links**

Benchmark repo: https://github.com/valdife/celery_worker_benchmark
Celery docs: https://docs.celeryq.dev/
Flower: https://flower.readthedocs.io/
Gevent: https://www.gevent.org/
Eventlet: https://eventlet.net/
Python GIL: https://docs.python.org/3/glossary.html#term-global-interpreter-lock
