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
The main problem we are trying to solve is a regression model for figuring out the trip duration

- Include a tag on anything that is data parallelism, as these cannot be used in the sequential algorithm
- Data cleaning:  
  - Decisions made:
  - Any trips above 90 minutes and at or below 0 minutes have been removed as most of these were outliers which shouldn't be included
  - Any trips over 40 miles have been excluded as they are again outliers which shouldn't be included
  - Finally, we have dropped the zones of 264 and 265 as they are unknow and New York county while we want to just capture
    Taxi data for inside of New York
  - What is left to do:
  - Give evidence for the minutes and distance so make a Python script showing why it's ok to remove them
  - make a map of all the different boroughs/zones
- We need to figure out the average time between different boroughs
- Split/shard the dataset based on hourly time
  - Then find the averages for each hour between boroughs
  - This will be included in data cleaning and preprocessing
- Use money as a predictor for time? Make sure money is not a direct calculator for time as that would be data leakage
- Figure out a nice number for batching the data


### Cleaned Data

The cleaning is in section 1 of [Trip_Duration.ipynb](Trip_Duration.ipynb). Evidence for the duration and distance cut-offs is in
[Evidence/Distance&Duration.ipynb](Evidence/Distance&Duration.ipynb).

**Columns loaded:** `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `trip_distance`, `PULocationID`, `DOLocationID`, `VendorID`, `RatecodeID`, `payment_type`, `fare_amount`.
The other 11 columns are never read.

**Filters** (applied in order; numbers are for all four months, 14,908,446 raw rows):

| # | Rule | Reason | Dropped |
|---|---|---|---|
| 0 | Pickup outside the file's month | Spill-over records (some even from 2001 and 2008). Removed while reading the file | 54 |
| 1 | Drop `duration_min` ≤ 0 or > 90 | 0 or negative is impossible; over 90 min is mostly meters left running (99% of trips are under 72 min) | 249,410 (1.67%) |
| 2 | Drop `trip_distance` ≤ 0 or > 40 | 0-distance trips are not genuine journeys (GPS issue or incomplete trip); over 40 removes meter errors like 269,097 miles | 462,584 (3.10%) |
| 3 | Drop zone IDs 264 & 265 | Unknown zones give inconsistent data, e.g. zone 1 → 265 can show 0.3 miles on one trip and 68 miles on another | 82,876 (0.56%) |
| 4 | Average speed < 1 or > 65 mph | Meter errors that pass rules 1 and 2 on their own, e.g. 30 miles in 2 minutes. 65 mph is the top NY speed limit | 91,897 (0.62%) |
| 5 | `fare_amount` ≤ 0 | Refunds, disputes and voided trips. Most negative fares reverse another record of the same trip | 98,000 (0.66%) |
| 6 | Duplicate trip (same vendor, times, zones, distance) | Same trip recorded twice. Removes 0 because rule 5 already removes the reversal copies | 0 |

**Overall:** 984,821 rows dropped (6.61%), 13,923,625 remaining (93.39%). Full per-month table: `CleanedData/cleaning_report.csv`.

**Flex Fare nulls** (`payment_type` = 0, about a quarter of trips): these rows have empty `passenger_count`, `RatecodeID`, `store_and_fwd_flag`,
`congestion_surcharge` and `Airport_fee`. The notebook checks the null counts match the Flex Fare count exactly. We keep the rows,
set `RatecodeID` nulls to 99 ("unknown") and add an `is_flex_fare` column. The other null columns are never loaded.

**Columns saved** to `CleanedData/yellow_tripdata_2026-<Mon>_Cleaned.parquet`, one file per month:

| Column | Description |
|---|---|
| `tpep_pickup_datetime` | Pickup time |
| `pickup_hour` | Hour of pickup, 0–23 |
| `pickup_dow` | Day of week of pickup, 0 = Monday, 6 = Sunday |
| `PULocationID`, `DOLocationID` | Pickup / drop-off zone, stored as a category (1–263) |
| `trip_distance` | Miles |
| `RatecodeID` | Rate code, stored as a category; nulls set to 99 |
| `is_flex_fare` | True for Flex Fare trips |
| `duration_min` | **Target:** drop-off minus pickup, in minutes |

Read them with `read_clean()` or `load_split()` from the notebook so the categories are restored.

**Leakage:** the drop-off time, fare and payment type are used for cleaning only and are not saved. Money is not used as a predictor.

**Split by time, not at random:** train = January + February, validation = March, test = April.

---

## 2. Comparison of sequential and parallel execution
- Make the sequential algorithm: This is done we need to move onto V0,
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