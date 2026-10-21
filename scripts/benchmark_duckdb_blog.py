#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb==1.4.5",
#   "pandas==3.0.6",
#   "polars==2.0.0",
#   "dask[dataframe]==2026.8.0",
#   "pyarrow==26.0.0",
# ]
# ///
"""Generate a Parquet demo and compare equivalent local aggregations on Unix.

Use --generate-only with just DuckDB installed. The full benchmark additionally
requires pandas, Polars, Dask DataFrame, and PyArrow. Existing data is never
overwritten; use --reuse to benchmark a previously generated directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import resource
import subprocess
import sys
import time


ENGINES = ("duckdb", "pandas", "polars", "dask")
QUERY = """
    SELECT country, SUM(amount_cents) / 100.0 AS revenue
    FROM read_parquet('events/*.parquet')
    WHERE event_time >= TIMESTAMP '2026-09-01'
      AND event_time <  TIMESTAMP '2026-10-01'
      AND event_type = 'purchase'
    GROUP BY country
    ORDER BY revenue DESC, country
    LIMIT 10
"""
COLUMNS = ["event_time", "country", "event_type", "amount_cents"]
FILTERS = [
    ("event_time", ">=", dt.datetime(2026, 9, 1)),
    ("event_time", "<", dt.datetime(2026, 10, 1)),
    ("event_type", "==", "purchase"),
]


def same_result(left: list, right: list) -> bool:
    return len(left) == len(right) and all(
        a[0] == b[0] and math.isclose(a[1], b[1], rel_tol=1e-12, abs_tol=1e-8)
        for a, b in zip(left, right)
    )


def generate(directory: Path, rows: int, threads: int) -> None:
    import duckdb

    directory.mkdir(parents=True, exist_ok=False)
    with duckdb.connect(config={"threads": threads}) as con:
        for part in range(4):
            start, end = rows * part // 4, rows * (part + 1) // 4
            con.execute(
                f"""
                COPY (
                    SELECT
                        TIMESTAMP '2026-08-01'
                            + (hash(i) % 92)::INTEGER * INTERVAL 1 DAY AS event_time,
                        'C' || lpad((hash(i + 3) % 30)::VARCHAR, 2, '0') AS country,
                        CASE WHEN hash(i + 2) % 4 = 0
                             THEN 'purchase' ELSE 'view' END AS event_type,
                        (100 + hash(i + 1) % 100000)::BIGINT AS amount_cents,
                        md5(i::VARCHAR) AS unused_payload
                    FROM range({start}, {end}) AS t(i)
                ) TO ? (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 122880)
                """,
                [str(directory / f"part-{part}.parquet")],
            )


def worker(engine: str, directory: Path, threads: int) -> dict:
    paths = sorted(str(path) for path in directory.glob("*.parquet"))
    connection = None
    if engine == "duckdb":
        import duckdb

        connection = duckdb.connect(config={"threads": threads, "memory_limit": "4GB"})
        sql = QUERY.replace("'events/*.parquet'", "?")

        def run():
            return connection.execute(sql, [paths]).fetchall()

    elif engine == "polars":
        import polars as pl

        def run():
            result = (
                pl.scan_parquet(paths)
                .filter(
                    (pl.col("event_time") >= dt.datetime(2026, 9, 1))
                    & (pl.col("event_time") < dt.datetime(2026, 10, 1))
                    & (pl.col("event_type") == "purchase")
                )
                .group_by("country")
                .agg((pl.col("amount_cents").sum() / 100.0).alias("revenue"))
                .sort(["revenue", "country"], descending=[True, False])
                .head(10)
                .collect(engine="streaming")
            )
            return result.rows()

    else:
        import pyarrow as pa

        pa.set_cpu_count(threads)
        pa.set_io_thread_count(threads)
        if engine == "pandas":
            import pandas as pd

            def load():
                return pd.read_parquet(paths, columns=COLUMNS, filters=FILTERS)

        else:
            import dask
            import dask.dataframe as dd

            dask.config.set(scheduler="threads", num_workers=threads)

            def load():
                return dd.read_parquet(
                    str(directory), columns=COLUMNS, filters=FILTERS, filesystem="arrow"
                )

        def run():
            grouped = load().groupby("country")["amount_cents"].sum()
            if engine == "dask":
                grouped = grouped.compute()
            result = (grouped / 100.0).rename("revenue").reset_index()
            result = result.sort_values(
                ["revenue", "country"], ascending=[False, True]
            ).head(10)
            return list(result.itertuples(index=False, name=None))

    timings = []
    results = []
    try:
        for _ in range(2):
            start = time.perf_counter()
            results.append(run())
            timings.append(time.perf_counter() - start)
    finally:
        if connection is not None:
            connection.close()
    if not same_result(results[0], results[1]):
        raise AssertionError(f"{engine}: repeated runs produced different results")
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = rss if sys.platform == "darwin" else rss * 1024
    return {
        "engine": engine,
        "version": importlib.metadata.version(engine),
        "first_seconds": timings[0],
        "repeat_seconds": timings[1],
        "peak_rss_mib": rss_bytes / 1024**2,
        "result": results[0],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("events"))
    parser.add_argument("--rows", type=int, default=5_000_000)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--engine", choices=ENGINES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.rows < 4 or args.threads < 1:
        parser.error("--rows must be at least 4 and --threads must be positive")
    directory = args.directory.resolve()
    if args.engine:
        print(json.dumps(worker(args.engine, directory, args.threads)))
        return
    if not args.reuse:
        generate(directory, args.rows, args.threads)
    if args.generate_only:
        print(f"Demo ready in {directory}; run the article example from its parent.")
        return

    environment = dict(os.environ)
    for key in ("POLARS_MAX_THREADS", "OMP_NUM_THREADS", "ARROW_NUM_THREADS"):
        environment[key] = str(args.threads)
    environment["OPENBLAS_NUM_THREADS"] = "1"
    environment["MKL_NUM_THREADS"] = "1"
    order = list(ENGINES)
    random.Random(42).shuffle(order)
    measurements = []
    for engine in order:
        completed = subprocess.run(
            [
                sys.executable, str(Path(__file__).resolve()),
                "--engine", engine, "--directory", str(directory),
                "--threads", str(args.threads),
            ],
            env=environment, capture_output=True, text=True,
        )
        if completed.returncode:
            raise RuntimeError(f"{engine} worker failed:\n{completed.stderr}")
        measurement = json.loads(completed.stdout)
        if measurements and not same_result(
            measurement["result"], measurements[0]["result"]
        ):
            raise AssertionError(f"{engine}: result differs from the other engines")
        measurements.append(measurement)

    import duckdb

    paths = sorted(str(path) for path in directory.glob("*.parquet"))
    with duckdb.connect(config={"threads": args.threads}) as con:
        rows = con.execute("SELECT count(*) FROM read_parquet(?)", [paths]).fetchone()[0]
        page_bytes = con.execute(
            "SELECT sum(total_uncompressed_size) FROM parquet_metadata(?)", [paths]
        ).fetchone()[0]
        profile = con.execute(
            "EXPLAIN ANALYZE " + QUERY.replace("'events/*.parquet'", "?"), [paths]
        ).fetchone()[1]
    cpu = platform.processor()
    if sys.platform == "darwin":
        cpu = subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
        ).strip()
    report = {
        "python": platform.python_version(),
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "ram_gib": os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024**3,
        "threads_requested": args.threads,
        "rows": rows,
        "parquet_bytes": sum(Path(path).stat().st_size for path in paths),
        "uncompressed_parquet_page_bytes": page_bytes,
        "pyarrow_version": importlib.metadata.version("pyarrow"),
        "execution_order": order,
        "measurements": measurements,
        "duckdb_profile": profile,
        "method": (
            "One fresh process per engine; two read/filter/group/sort/materialize runs "
            "after imports; no OS cache flush. RSS is lifetime peak including imports. "
            "Four files, null-free synthetic rows, low-cardinality aggregation. "
            "pandas/PyArrow and Dask receive column selections and scan filters; "
            "Polars uses lazy streaming; Dask uses Arrow filesystem and local threads. "
            "Not a spill test. "
            "Sorted results compared with relative tolerance 1e-12, absolute 1e-8 "
            "for final floating-point currency conversion."
        ),
    }
    serialized = json.dumps(report, indent=2)
    if args.report:
        args.report.write_text(serialized + "\n")
    print(serialized)


if __name__ == "__main__":
    main()
