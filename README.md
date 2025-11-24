# Celery Worker Pool Benchmark

A benchmarking tool to compare Celery worker pool types (prefork vs gevent) with different concurrency settings against CPU-bound and I/O-bound tasks.

## Features

- Configurable Celery worker pool type (prefork/gevent)
- Configurable worker concurrency
- CPU-bound and I/O-bound task benchmarks
- Both sync and async task implementations
- Environment-based configuration
- Docker Compose setup for easy testing

## Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Configure your settings in `.env`:
```
CELERY_POOL_TYPE=prefork
CELERY_CONCURRENCY=4
NUM_TASKS=10
TASK_TYPE=cpu_bound_sync
REDIS_URL=redis://localhost:6379/0
```

## Usage

1. Start the services:
```bash
docker-compose up -d
```

2. Wait for services to be ready, then run the benchmark:
```bash
python main.py
```

## Configuration

### Environment Variables

- `CELERY_POOL_TYPE`: Worker pool type (`prefork` or `gevent`)
- `CELERY_CONCURRENCY`: Number of concurrent workers
- `NUM_TASKS`: Number of tasks to execute in the benchmark
- `TASK_TYPE`: Type of task to benchmark:
  - `cpu_bound_sync`: CPU-intensive synchronous task
  - `cpu_bound_async`: CPU-intensive asynchronous task
  - `io_bound_sync`: I/O-bound synchronous task
  - `io_bound_async`: I/O-bound asynchronous task
- `REDIS_URL`: Redis connection URL

## Task Types

### CPU-bound Tasks
- Perform intensive mathematical calculations
- Test worker pool performance under CPU load

### I/O-bound Tasks
- Simulate I/O operations with delays
- Test worker pool performance under I/O wait

## Results

The benchmark reports:
- Total execution time
- Average task execution time
- Minimum task execution time
- Maximum task execution time

