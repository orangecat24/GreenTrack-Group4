"""
Explore the raw UCI household power file and print the facts we need
for contracts/data.md (size, missing values, time range, duplicates, gaps,
value ranges, and a daylight-saving check).

Run it from the repository root:
    python data/explore_raw_file.py

The raw file is NOT in the repository (it is too big). Change RAW_FILE
below if your copy is somewhere else.
"""

import pandas as pd

RAW_FILE = r"C:\Users\Slim 7 pro\OneDrive\Desktop\household_power_consumption.csv"

NUMBER_COLUMNS = [
    "Global_active_power",
    "Global_reactive_power",
    "Voltage",
    "Global_intensity",
    "Sub_metering_1",
    "Sub_metering_2",
    "Sub_metering_3",
]

print("Reading the file (this can take 20-30 seconds)...")

# sep=";"        -> values are separated by semicolons, not commas
# na_values="?"  -> every "?" becomes a missing value (NaN), never 0
# Date and Time are read as plain text so pandas does not guess their format
data = pd.read_csv(
    RAW_FILE,
    sep=";",
    na_values=["?"],
    dtype={"Date": str, "Time": str},
    low_memory=False,
)

print()
print("1) Size")
print("   Rows:", len(data))
print("   Columns:", list(data.columns))

print()
print("2) Missing values per column")
for column in data.columns:
    missing = int(data[column].isna().sum())
    percent = missing / len(data) * 100
    print(f"   {column}: {missing} missing ({percent:.2f} %)")

# Join Date and Time into one real timestamp. Date is day/month/year.
data["timestamp"] = pd.to_datetime(
    data["Date"] + " " + data["Time"],
    format="%d/%m/%Y %H:%M:%S",
)

print()
print("3) Time range")
first_time = data["timestamp"].min()
last_time = data["timestamp"].max()
print("   First reading:", first_time)
print("   Last reading: ", last_time)

print()
print("4) Duplicate timestamps")
duplicate_count = int(data["timestamp"].duplicated().sum())
print("   Rows whose timestamp already appeared earlier:", duplicate_count)

print()
print("5) Gaps (minutes that have no row at all)")
expected_rows = int((last_time - first_time) / pd.Timedelta(minutes=1)) + 1
print("   Rows expected (one per minute):", expected_rows)
unique_minutes = int(data["timestamp"].nunique())
print("   Different minutes in the file: ", unique_minutes)
print("   Minutes with no row:           ", expected_rows - unique_minutes)

print()
print("6) Value ranges (missing values are ignored)")
for column in NUMBER_COLUMNS:
    smallest = data[column].min()
    largest = data[column].max()
    average = data[column].mean()
    print(f"   {column}: min {smallest}, max {largest}, average {average:.3f}")

print()
print("7) First 3 minutes where Global_active_power is missing")
missing_rows = data[data["Global_active_power"].isna()]
for timestamp in missing_rows["timestamp"].head(3):
    print("  ", timestamp)

print()
print("8) Daylight-saving check (France moved clocks 02:00 -> 03:00 on 25 March 2007)")
# If the times were French local clock time, 02:00-02:59 on that day
# would not exist. Counting rows in that hour tells us how time was recorded.
start = pd.Timestamp("2007-03-25 02:00:00")
end = pd.Timestamp("2007-03-25 03:00:00")
rows_in_hour = data[(data["timestamp"] >= start) & (data["timestamp"] < end)]
print("   Rows between 02:00 and 03:00 on 2007-03-25:", len(rows_in_hour))

print()
print("Done.")