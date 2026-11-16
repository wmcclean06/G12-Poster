# G12-Poster

## 0. House Cleaning

- Remember to have git-lfs installed on your machine as we are dealing with large data files
- Don't delete the Original data ever and if you do change it give it a reasonable name.
- Install a parquet loader or plugin so you can view the data naturally, 
  - On IntelliJ, we are using  [Parquet Loader](https://plugins.jetbrains.com/plugin/26684-parquet-loader)
    - You will have to restart your computer after installing
  - On VSCode, we are using [Parquet Loader](https://marketplace.visualstudio.com/items?itemName=AdamViola.parquet-explorer)
- We will be defining all of the variables in this [Variables](Variables.md)

## 1. Data cleaning and preprocessing|Data Parallelism
Our main problem is that we don't have any latitudes or longitudes for drop off or pickup

- Include a tag on anything that is data parallelism, as these cannot be used in the sequential algorithm
- Data cleaning: removing 0, anything over 100 miles, 
  - look at anything at or above 80
  - make a map of all the different boroughs/zones
- We need to figure out the average time between different boroughs
- Split/shard the dataset based on hourly time
  - Then find the averages for each hour between boroughs
  - This will be included in data cleaning and preprocessing
- Use money as a predictor for time? Make sure money is not a direct calculator for time as that would be data leakage
- Figure out a nice number for batching the data


### Cleaned Data

**Columns loaded:** `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `trip_distance`, `PULocationID`, `DOLocationID`

**Derived columns** *(new)*, all calculated from the pickup/dropoff timestamps:

| Column | Description | Range |
|---|---|---|
| `duration_min` | Trip duration in minutes (dropoff − pickup) | — |
| `pickup_hour` | Hour of pickup | 0–23 |
| `pickup_dow` | Day of week of pickup | 0–6 (0 = Monday, 6 = Sunday) |

**Filters** (applied in order, % of the original dataset dropped):

| # | Rule | Reason | Dropped |
|---|---|---|---|
| 1 | Drop `duration_min` ≤ 0 or ≥ 120 | A duration of 0 adds nothing to training; trips over 120 min are highly fluctuating outliers | ~1.33% |
| 2 | Drop `trip_distance` ≤ 0 or > `DISTANCE_THRESHOLD` (currently 40) | 0-distance trips are removed as they may not fully include genuine trips and could be gps issue or incomplete trips | ~3.37% |
| 3 | Drop zone IDs 264 & 265 | Unknown zones give inconsistent data, e.g. zone 1 → 265 can show 0.3 miles on one trip and 68 miles on another | ~0.6% |

**Overall:** ~5.3% of the data dropped, 94.7% remaining.

---

## 2. Comparison of sequential and parallel execution
- Make the sequential algorithm
  - V0: Check that it actually runs on William's machine using the full dataset, if not we will shrink the dataset in half
    - This will be informing the data parallelisation as well
  - V1: Just use the different boroughs for the average
    - Try not to use the averages in a way that will lead to data leakage or getting the correct answer purely from the average
  - V2: Include time
  - V3: Include additional metrics as found
- Make the algorithm parallel
  - Start documenting any 2 sources/examples of non-determinism in the algorithm
- 

---

## 3. Poster

- Talk about points 1 and 3 from the rubric  
  - Maybe use the New York boroughs example as a diagram
  - Include the trip time prediction from the time of day
- Talk about sequential vs parallel
  - Task parallelism
- Speak on the 2 examples of non-determinism

---

## Questions for lab

- Does Manhattan to Queens average time count as a feature for feature extraction?
- 


