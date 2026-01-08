import os
import time
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from celery.result import AsyncResult
from celery_app import celery_app
import tasks

load_dotenv()

NUM_TASKS = int(os.getenv("NUM_TASKS", "10"))
TASK_TYPE = os.getenv("TASK_TYPE", "cpu_bound_sync")
CELERY_POOL_TYPE = os.getenv("CELERY_POOL_TYPE", "prefork")
CELERY_CONCURRENCY = os.getenv("CELERY_CONCURRENCY", "4")


def run_benchmark(task_name: str, num_tasks: int) -> dict[str, float]:
    print(f"Running benchmark: {task_name} with {num_tasks} tasks")

    start_time = time.time()
    results: list[AsyncResult] = []

    for _ in range(num_tasks):
        result = celery_app.send_task(task_name)
        results.append(result)

    print(f"All {num_tasks} tasks submitted, waiting for completion...")

    task_times: list[float] = []
    for i, result in enumerate(results):
        result.get(timeout=300)
        if result.successful():
            task_time = result.result
            if isinstance(task_time, (int, float)):
                task_times.append(task_time)
        print(f"Task {i+1}/{num_tasks} completed")

    end_time = time.time()
    total_time = end_time - start_time

    return {
        "total_time": total_time,
        "average_task_time": sum(task_times) / len(task_times) if task_times else 0,
        "min_task_time": min(task_times) if task_times else 0,
        "max_task_time": max(task_times) if task_times else 0,
    }


def save_results(
    benchmark_results: dict[str, float],
    task_type: str,
    num_tasks: int,
    pool_type: str,
    concurrency: str,
    output_dir: str = "results"
) -> str:
    """Save benchmark results to a JSON file."""
    # Create results directory if it doesn't exist
    results_path = Path(output_dir)
    results_path.mkdir(exist_ok=True)

    # Create filename with pool type and concurrency
    filename = f"benchmark_{task_type}_{num_tasks}tasks_{pool_type}_c{concurrency}.json"
    filepath = results_path / filename

    # Prepare data to save
    data = {
        "timestamp": datetime.now().isoformat(),
        "task_type": task_type,
        "num_tasks": num_tasks,
        "pool_type": pool_type,
        "concurrency": int(concurrency),
        "results": benchmark_results,
    }

    # Write to file
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    return str(filepath)


def main():
    task_mapping = {
        "cpu_bound_sync": "tasks.cpu_bound_sync",
        "cpu_bound_async": "tasks.cpu_bound_async",
        "io_bound_sync": "tasks.io_bound_sync",
        "io_bound_async": "tasks.io_bound_async",
    }

    task_name = task_mapping.get(TASK_TYPE)
    if not task_name:
        print(f"Unknown task type: {TASK_TYPE}")
        print(f"Available types: {list(task_mapping.keys())}")
        return

    print("=" * 60)
    print(f"Celery Worker Pool Benchmark")
    print("=" * 60)
    print(f"Task Type: {TASK_TYPE}")
    print(f"Number of Tasks: {NUM_TASKS}")
    print(f"Pool Type: {CELERY_POOL_TYPE}")
    print(f"Concurrency: {CELERY_CONCURRENCY}")
    print("=" * 60)

    benchmark_results = run_benchmark(task_name, NUM_TASKS)

    print("\n" + "=" * 60)
    print("Benchmark Results:")
    print("=" * 60)
    print(f"Total Time: {benchmark_results['total_time']:.4f} seconds")
    print(f"Average Task Time: {benchmark_results['average_task_time']:.4f} seconds")
    print(f"Min Task Time: {benchmark_results['min_task_time']:.4f} seconds")
    print(f"Max Task Time: {benchmark_results['max_task_time']:.4f} seconds")
    print("=" * 60)

    # Save results to file
    saved_path = save_results(
        benchmark_results, TASK_TYPE, NUM_TASKS, CELERY_POOL_TYPE, CELERY_CONCURRENCY
    )
    print(f"\nResults saved to: {saved_path}")


if __name__ == "__main__":
    main()
