import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder


SHARDS = 12   # number of batches the data is cut into
WORKERS = 3   # number of worker processes
SAMPLE = 1.0  # fraction of rows to use: 1.0 = all data, 0.05 = quick 5% test


path_to_data = Path(__file__).resolve().parent.parent / "CleanedData" / "yellow_tripdata_2026_Combined_Cleaned.parquet"

FEATURES = [
    "trip_distance",
    "PULocationID",
    "DOLocationID",
    "pickup_hour",
    "pickup_dow",
]

numeric = ["trip_distance"]
categorical = ["PULocationID", "DOLocationID", "pickup_hour", "pickup_dow"]

def make_shards(data, n_shards):
    bounds = np.linspace(0, data.shape[0], n_shards + 1, dtype=int)  # shape[0] = rows (len() fails on sparse)
    return [data[a:b] for a, b in zip(bounds[:-1], bounds[1:])]


def start_worker(_):
    time.sleep(0.5)
    return os.getpid()


def extract_feature(column, train_col, test_col):
    if column in numeric:  # "passthrough" in the notebook
        return sp.csr_matrix(train_col.to_numpy(np.float64)), sp.csr_matrix(test_col.to_numpy(np.float64))
    # categorical -> one-hot, learned from the training rows only (same as the notebook)
    encoder = OneHotEncoder(handle_unknown="ignore").fit(train_col)
    return encoder.transform(train_col), encoder.transform(test_col)


def build_features_parallel(X_train, X_test, executor):
    futures = [executor.submit(extract_feature, col, X_train[[col]], X_test[[col]]) for col in FEATURES]
    results = [f.result() for f in futures]  # collected in FEATURES order -> fixed column order
    X_train_encoded = sp.hstack([train for train, _ in results], format="csr")
    X_test_encoded = sp.hstack([test for _, test in results], format="csr")
    return X_train_encoded, X_test_encoded


def predict_shard(model, X_shard):
    return model.predict(X_shard)


def main():
    timings = {}
    print(f"shards={SHARDS}  workers={WORKERS}  sample={SAMPLE}  cpu_count={os.cpu_count()}")

    start = time.perf_counter()
    dataframe_clean = pd.read_parquet(path_to_data, columns=FEATURES + ["duration_min"])
    if SAMPLE < 1:
        dataframe_clean = dataframe_clean.sample(frac=SAMPLE, random_state=0).sort_index()
    timings["load"] = time.perf_counter() - start
    print(f"Loaded {len(dataframe_clean):,} rows")

    X = dataframe_clean[FEATURES]
    y = dataframe_clean["duration_min"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=44)

    start = time.perf_counter()
    executor = ProcessPoolExecutor(max_workers=WORKERS)
    worker_ids = set(executor.map(start_worker, range(WORKERS)))
    timings["start workers"] = time.perf_counter() - start
    print(f"Workers running: {len(worker_ids)}")

    try:
        start = time.perf_counter()
        X_train_encoded, X_test_encoded = build_features_parallel(X_train, X_test, executor)
        timings["feature extraction (parallel)"] = time.perf_counter() - start
        print(f"Features: {X_train_encoded.shape[1]} columns")

        start = time.perf_counter()
        model = LinearRegression(n_jobs=3).fit(X_train_encoded, y_train)
        timings["model.fit"] = time.perf_counter() - start

        start = time.perf_counter()
        y_pred = model.predict(X_test_encoded)
        timings["model.predict"] = time.perf_counter() - start
    finally:
        executor.shutdown()

    rmse = root_mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"Root Mean Squared Error: {rmse:.2f} minutes")
    print(f"R-squared ($R^2$): {r2:.2f}")

    print("\n=== TIMINGS ===")
    for label, seconds in timings.items():
        print(f"  {label:<30} {seconds:7.2f} s")
    print(f"  {'total':<30} {sum(timings.values()):7.2f} s")


if __name__ == "__main__":
    main()
