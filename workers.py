"""Functions that run inside worker processes.

They live in a .py file rather than the notebook because on Windows each worker starts as a fresh
Python process, and a fresh process can only find functions it can import from a file.
The sequential code in the notebook calls these same functions, so both versions do identical work.
"""
import os

# One maths thread per process, so worker processes don't compete for the same cores
for var in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[var] = "1"

import numpy as np
import pandas as pd

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


# ---- Gradient computation: the same function runs on every shard ----

def partial_gradient(x_path, y_path, start, stop, w, b):
    """Sums for one shard of the training rows: gradient for w, gradient for b, squared error, row count.

    mmap_mode="r" reads only this shard's rows from disk instead of loading the whole file.
    """
    X = np.load(x_path, mmap_mode="r")[start:stop]
    y = np.load(y_path, mmap_mode="r")[start:stop]
    err = X @ w + b - y
    return X.T @ err, err.sum(), err @ err, len(err)
