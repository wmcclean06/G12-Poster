"""Functions that run inside worker processes.

They live in a .py file rather than the notebook because on Windows each worker starts as a fresh
Python process, and a fresh process can only find functions it can import from a file.
The sequential code in the notebook calls these same functions, so both versions do identical work.
"""
import os
import time

# One maths thread per process, so worker processes don't compete for the same cores
for var in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[var] = "1"

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_info, threadpool_limits

threadpool_limits(limits=1)  # in case the maths library was loaded before the lines above

BOROUGH_HOUR_KEYS = ["PU_borough", "DO_borough", "pickup_hour", "pickup_dow"]
ZONE_PAIR_KEYS = ["PULocationID", "DOLocationID"]
PACE_KEYS = ["PU_borough", "pickup_hour", "pickup_dow"]


# ---- Feature extraction: each table is an independent task ----

def _read_trips(paths, lookup_path, columns):
    """Read only the needed columns of the training files, adding the pickup and drop-off boroughs."""
    trips = pd.concat([pd.read_parquet(p, columns=columns) for p in paths], ignore_index=True)
    for col in ["PULocationID", "DOLocationID"]:
        if col in trips:
            trips[col] = trips[col].astype(int)
    if lookup_path is not None:
        borough = pd.read_csv(lookup_path, keep_default_na=False).set_index("LocationID")["Borough"]
        trips["PU_borough"] = trips["PULocationID"].map(borough)
        if "DOLocationID" in trips:
            trips["DO_borough"] = trips["DOLocationID"].map(borough)
    for col in ["pickup_hour", "pickup_dow"]:
        if col in trips:
            trips[col] = trips[col].astype(int)
    return trips


def borough_hour_table(paths, lookup_path):
    """Total trip minutes and trip count per pickup borough, drop-off borough, hour and day of week."""
    trips = _read_trips(paths, lookup_path,
                        ["PULocationID", "DOLocationID", "pickup_hour", "pickup_dow", "duration_min"])
    return (trips.groupby(BOROUGH_HOUR_KEYS)["duration_min"]
            .agg(duration_sum="sum", count="size").sort_index())


def zone_pair_table(paths, lookup_path=None):
    """Total trip minutes and trip count per pickup zone and drop-off zone."""
    trips = _read_trips(paths, None, ["PULocationID", "DOLocationID", "duration_min"])
    return (trips.groupby(ZONE_PAIR_KEYS)["duration_min"]
            .agg(duration_sum="sum", count="size").sort_index())


def pace_table(paths, lookup_path):
    """Total minutes, total miles and trip count per pickup borough, hour and day of week."""
    trips = _read_trips(paths, lookup_path,
                        ["PULocationID", "pickup_hour", "pickup_dow", "trip_distance", "duration_min"])
    return (trips.groupby(PACE_KEYS)
            .agg(duration_sum=("duration_min", "sum"), distance_sum=("trip_distance", "sum"),
                 count=("duration_min", "size")).sort_index())


FEATURE_FUNCS = {"borough_hour": borough_hour_table, "zone_pair": zone_pair_table, "pace": pace_table}


def feature_task(name, paths, lookup_path):
    """One feature-extraction task: build one table, and report how long it took and which process ran it."""
    start = time.perf_counter()
    table = FEATURE_FUNCS[name](paths, lookup_path)
    return table, time.perf_counter() - start, os.getpid()


# ---- Gradient computation: the same function runs on every shard ----

def partial_gradient(x_path, y_path, start, stop, w, b):
    """Sums for one shard of the training rows: gradient for w, gradient for b, squared error, row count.

    mmap_mode="r" reads only this shard's rows from disk instead of loading the whole file.
    """
    X = np.load(x_path, mmap_mode="r")[start:stop]
    y = np.load(y_path, mmap_mode="r")[start:stop]
    err = X @ w + b - y
    return X.T @ err, err.sum(), err @ err, len(err)


def ping(i):
    """Does nothing. Used to start a pool's processes and to time the cost of sending a task."""
    return i


def blas_threads(i=None):
    """How many threads NumPy's maths library uses in this process (the argument lets pool.map call it)."""
    return max((info["num_threads"] for info in threadpool_info()), default=1)


# ---- Training: shared by the sequential baseline, data parallelism and the search ----

def train_gd(shards, eta, steps, lam=0.0, map_fn=map, tol=None):
    """Batch gradient descent for linear regression. Returns weights, bias and training RMSE after each step.

    map_fn runs partial_gradient on every shard: Python's map for one process, a pool's map for several.
    With tol set, training stops early once the error improves by less than that fraction, or starts to grow.
    """
    n_features = np.load(shards[0][0], mmap_mode="r").shape[1]
    w, b = np.zeros(n_features), 0.0
    history = []
    for _ in range(steps):
        n_shards = len(shards)
        parts = list(map_fn(partial_gradient, *zip(*shards), [w] * n_shards, [b] * n_shards))
        # Add the shard sums in shard order, so the result never depends on which shard finished first
        grad_w = sum(p[0] for p in parts)
        grad_b = sum(p[1] for p in parts)
        sq_err = sum(p[2] for p in parts)
        n = sum(p[3] for p in parts)
        w = w - eta * (grad_w / n + lam * w)
        b = b - eta * grad_b / n
        history.append(np.sqrt(sq_err / n))
        if tol is not None and len(history) > 1:
            if not np.isfinite(history[-1]) or history[-1] > history[0]:
                break  # diverging: the learning rate is too high
            if history[-2] - history[-1] < tol * history[-1]:
                break  # converged
    return w, b, history


def run_trial(trial_id, shards, val_paths, steps, tol, seed):
    """One hyperparameter trial: draw a learning rate and L2 strength, train, and score on the validation month.

    The settings come from a generator seeded with seed + trial_id, so a trial draws the same settings whichever
    worker runs it. seed=None draws different settings every run (used in section 5 to show the problem).
    """
    start = time.perf_counter()
    rng = np.random.default_rng(None if seed is None else seed + trial_id)
    eta = float(10 ** rng.uniform(np.log10(0.02), np.log10(0.6)))
    lam = float(10 ** rng.uniform(-5, -1))
    with np.errstate(over="ignore", invalid="ignore"):
        w, b, history = train_gd(shards, eta, steps, lam=lam, tol=tol)
        trained = time.perf_counter()
        X = np.load(val_paths[0], mmap_mode="r")
        y = np.load(val_paths[1], mmap_mode="r")
        rmse = float(np.sqrt(np.mean((X @ w + b - y) ** 2)))
    end = time.perf_counter()
    if not np.isfinite(history[-1]) or history[-1] > history[0]:
        stopped = "diverged"
    elif len(history) < steps:
        stopped = "converged"
    else:
        stopped = "step limit"
    return {"trial": trial_id, "eta": eta, "lam": lam, "steps": len(history), "stopped": stopped,
            "val_rmse": rmse if np.isfinite(rmse) else float("inf"),
            "seconds": end - start, "train_seconds": trained - start, "score_seconds": end - trained,
            "pid": os.getpid(), "w": w, "b": b}
