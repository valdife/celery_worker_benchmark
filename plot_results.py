"""Load benchmark JSONs from results/ and plot total time by run."""
from pathlib import Path
import json

import pandas as pd
import matplotlib.pyplot as plt


def load_results(results_dir: Path) -> pd.DataFrame:
    rows = []
    for p in sorted(results_dir.glob("benchmark_*.json")):
        with open(p) as f:
            d = json.load(f)
        r = d["results"]
        rows.append({
            "task_type": d["task_type"],
            "num_tasks": d["num_tasks"],
            "pool_type": d["pool_type"],
            "concurrency": d["concurrency"],
            "total_time": r["total_time"],
            "throughput": d["num_tasks"] / r["total_time"],
        })
    return pd.DataFrame(rows)


def plot_bound_type(df: pd.DataFrame, bound_type: str, results_dir: Path) -> None:
    sub = (
        df[df["bound_type"] == bound_type]
        .sort_values("total_time", ascending=False)
        .reset_index(drop=True)
    )
    if sub.empty:
        return
    # label: sync/async + pool + concurrency, e.g. "sync prefork c4"
    sub["approach"] = sub["task_type"].str.rsplit("_", n=1).str[1]
    sub["label"] = (
        sub["approach"]
        + "\n"
        + sub["pool_type"]
        + " c"
        + sub["concurrency"].astype(str)
    )
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = sub["pool_type"].map({"prefork": "C0", "gevent": "C1"})
    ax.bar(range(len(sub)), sub["total_time"], color=colors)
    ax.set_xticks(range(len(sub)))
    ax.set_xticklabels(sub["label"], rotation=30, ha="right")
    ax.set_ylabel("Total time (s)")
    ymax = sub["total_time"].max()
    ymin = sub["total_time"].min() or 1
    if ymax / ymin > 10:
        ax.set_yscale("log")
        ax.set_ylim(top=ymax * 2.8)
    else:
        ax.set_ylim(top=ymax * 1.2)
    ax.set_title(f"Celery benchmark – {bound_type.replace('_', ' ')}")
    ax.legend(
        [plt.Rectangle((0, 0), 1, 1, fc="C0"), plt.Rectangle((0, 0), 1, 1, fc="C1")],
        ["prefork", "gevent"],
        loc="upper right",
    )
    for i, (_, row) in enumerate(sub.iterrows()):
        ax.annotate(
            f"{row['total_time']:.1f}s",
            (i, row["total_time"]),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=8,
            clip_on=False,
        )
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out = results_dir / f"benchmark_{bound_type}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out}")


def main() -> None:
    base = Path(__file__).resolve().parent
    results_dir = base / "results"
    df = load_results(results_dir)
    df["bound_type"] = df["task_type"].str.rsplit("_", n=1).str[0]
    df = df.sort_values(["bound_type", "task_type", "pool_type", "concurrency"]).reset_index(drop=True)

    for bound_type in ["cpu_bound", "io_bound"]:
        plot_bound_type(df, bound_type, results_dir)


if __name__ == "__main__":
    main()
