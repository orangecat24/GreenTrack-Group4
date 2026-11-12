"""
Create the small test fixture for the GreenTrack pipeline, and the
expected hourly results that the real Glue jobs must reproduce.

It writes two files:
    fixtures/raw_sample.csv       -> 130 real rows + 1 fake duplicate row
    fixtures/expected_hourly.csv  -> the correct hourly answer for that sample

The sample is 21 December 2006, 10:00 to 12:09:
    10:00-10:59  complete hour (60 minutes) + a fake duplicate of 10:30
    11:00-11:59  real missing minutes at 11:23 and 11:24 ("?")
    12:00-12:09  only 10 minutes -> an incomplete hour

This script uses plain Python only (no pandas, no Spark), so it is an
independent check of the Glue jobs.

Run it from the repository root:
    python data/make_fixture.py
"""

RAW_FILE = r"C:\Users\Slim 7 pro\OneDrive\Desktop\household_power_consumption.csv"
SAMPLE_FILE = "fixtures/raw_sample.csv"
EXPECTED_FILE = "fixtures/expected_hourly.csv"

SAMPLE_DATE = "21/12/2006"
FIRST_TIME = "10:00:00"
LAST_TIME = "12:09:00"
DUPLICATE_TIME = "10:30:00"


# ---------------------------------------------------------------
# Part 1: copy the chosen rows from the raw file into the fixture
# ---------------------------------------------------------------
header = None
sample_lines = []

with open(RAW_FILE, "r", encoding="utf-8") as raw:
    for line_number, line in enumerate(raw):
        line = line.rstrip("\n")
        if line_number == 0:
            header = line
            continue

        parts = line.split(";")
        date = parts[0]
        time = parts[1]

        # Times like "10:05:00" compare correctly as text.
        if date == SAMPLE_DATE and FIRST_TIME <= time <= LAST_TIME:
            sample_lines.append(line)

        # The file is in time order, so stop once we are past our sample.
        if date == SAMPLE_DATE and time > LAST_TIME:
            break

# Add one fake duplicate: an exact copy of the 10:30 row, placed at the end.
for line in sample_lines:
    if line.split(";")[1] == DUPLICATE_TIME:
        sample_lines.append(line)
        break

with open(SAMPLE_FILE, "w", encoding="utf-8", newline="\n") as sample:
    sample.write(header + "\n")
    for line in sample_lines:
        sample.write(line + "\n")

print("Wrote", SAMPLE_FILE, "with", len(sample_lines), "data rows")


# ---------------------------------------------------------------
# Part 2: calculate the expected hourly results by hand-style rules
# (the same rules as contracts/data.md)
# ---------------------------------------------------------------

# Step A: remove duplicates -> keep one row per minute.
rows_by_minute = {}
for line in sample_lines:
    parts = line.split(";")
    minute_key = parts[1]
    rows_by_minute[minute_key] = parts

# Step B: add up each hour.
hours = {}
for minute_key in sorted(rows_by_minute):
    parts = rows_by_minute[minute_key]
    hour = minute_key[0:2]  # "10", "11" or "12"

    if hour not in hours:
        hours[hour] = {
            "energy_kwh": 0.0,
            "kitchen_kwh": 0.0,
            "laundry_kwh": 0.0,
            "heater_ac_kwh": 0.0,
            "minutes_with_data": 0,
        }

    power_text = parts[2]
    if power_text == "?":
        # Missing minute: skip it. It is NOT counted as zero usage.
        continue

    power_kw = float(power_text)
    kitchen_wh = float(parts[6])
    laundry_wh = float(parts[7])
    heater_ac_wh = float(parts[8])

    hours[hour]["energy_kwh"] += power_kw / 60       # power -> energy
    hours[hour]["kitchen_kwh"] += kitchen_wh / 1000  # Wh -> kWh
    hours[hour]["laundry_kwh"] += laundry_wh / 1000
    hours[hour]["heater_ac_kwh"] += heater_ac_wh / 1000
    hours[hour]["minutes_with_data"] += 1

# Step C: write the expected results.
with open(EXPECTED_FILE, "w", encoding="utf-8", newline="\n") as expected:
    expected.write(
        "household_id,period_start,energy_kwh,kitchen_kwh,laundry_kwh,"
        "heater_ac_kwh,other_kwh,minutes_with_data,is_complete\n"
    )
    for hour in sorted(hours):
        totals = hours[hour]
        other_kwh = (
            totals["energy_kwh"]
            - totals["kitchen_kwh"]
            - totals["laundry_kwh"]
            - totals["heater_ac_kwh"]
        )
        is_complete = totals["minutes_with_data"] == 60
        period_start = "2006-12-21 " + hour + ":00:00"

        expected.write(
            "household-1,"
            + period_start + ","
            + f"{totals['energy_kwh']:.6f},"
            + f"{totals['kitchen_kwh']:.6f},"
            + f"{totals['laundry_kwh']:.6f},"
            + f"{totals['heater_ac_kwh']:.6f},"
            + f"{other_kwh:.6f},"
            + str(totals["minutes_with_data"]) + ","
            + str(is_complete).lower() + "\n"
        )

print("Wrote", EXPECTED_FILE)
print()
print("Expected hourly results:")
with open(EXPECTED_FILE, "r", encoding="utf-8") as expected:
    print(expected.read())