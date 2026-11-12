\# GreenTrack data contract (v1, draft)



Owner: Person 1. Changes only through a reviewed pull request that all three members approve.



\## 1. Source file



\- UCI "Individual household electric power consumption", one household near Paris.

\- 2,075,259 rows, one per minute, from 2006-12-16 17:24 to 2010-11-26 21:02.

\- Separator `;`. Date format `d/m/yyyy`, time format `hh:mm:ss`.

\- Missing values are written as `?`. 25,979 rows (1.25 %) are missing,

&#x20; and when a row is missing, ALL seven value columns are `?` together.

\- The original file has no duplicate timestamps and no skipped minutes.



| Source column | Meaning | Unit |

|---|---|---|

| Date | Day of the reading | d/m/yyyy |

| Time | Minute of the reading | hh:mm:ss |

| Global\_active\_power | Average power used in that minute | kW |

| Global\_reactive\_power | Average reactive power in that minute | kW |

| Voltage | Average voltage | V |

| Global\_intensity | Average current | A |

| Sub\_metering\_1 | Kitchen energy in that minute | Wh |

| Sub\_metering\_2 | Laundry energy in that minute | Wh |

| Sub\_metering\_3 | Water heater and air conditioning energy in that minute | Wh |



\## 2. Household and time rules



\- `household\_id` is always `household-1` (the dataset has one household; we do not invent others).

\- Timestamps are kept exactly as in the file (no time zone conversion).

&#x20; The clock has no daylight saving: the hour 02:00-03:00 on 2007-03-25 exists

&#x20; and no times repeat in October.

\- Convention (to be agreed by the team): we treat this clock as UTC everywhere

&#x20; (Glue, Athena, API, models). It is NOT a real conversion.

\- Time windows are start inclusive, end exclusive: `\[start, end)`.

\- An hour is identified by its start time, for example `2009-06-01 13:00:00` covers 13:00-13:59.



\## 3. Energy calculation (the most important rule)



\- `Global\_active\_power` is POWER (kW), not energy.

&#x20; Energy of one minute in kWh = `Global\_active\_power / 60`.

&#x20; Example: 4.216 kW for one minute = 4.216 / 60 = 0.0703 kWh.

\- Sub-metering columns are already ENERGY (Wh). In kWh: `Sub\_metering\_x / 1000`.

\- Energy not measured by the three sub-meters (lights, other devices), in Wh per minute:

&#x20; `Global\_active\_power \* 1000 / 60 - Sub\_metering\_1 - Sub\_metering\_2 - Sub\_metering\_3`.



\## 4. Missing data rules



\- `?` becomes null. A null is NEVER turned into 0.

\- Hourly and daily totals add up only the minutes that have values,

&#x20; and always report how many minutes were present (`minutes\_with\_data`).

\- An hour is complete when `minutes\_with\_data = 60`, a day when it is 1440.

\- If an hour has no minutes with data, its energy values are null (not 0).

\- The API and the models must check the `is\_complete` flag before treating a value as a full hour or day.



\## 5. Layers



\### Bronze (`bronze.raw\_readings`)

All original columns as text, exactly as received, plus:

\- `source\_file` (string): name of the uploaded file

\- `load\_ts` (timestamp): when the pipeline loaded it



\### Silver (`silver.readings`, Apache Iceberg, partitioned by `year`, `month`)



| Column | Type | Notes |

|---|---|---|

| household\_id | string | always `household-1` |

| reading\_ts | timestamp | Date + Time joined |

| global\_active\_power\_kw | double | null if `?` |

| global\_reactive\_power\_kw | double | null if `?` |

| voltage\_v | double | null if `?` |

| global\_intensity\_a | double | null if `?` |

| sub\_metering\_1\_wh | double | kitchen |

| sub\_metering\_2\_wh | double | laundry |

| sub\_metering\_3\_wh | double | water heater and AC |

| year | int | partition |

| month | int | partition |

| source\_file | string | from bronze |

| load\_ts | timestamp | from bronze |



Duplicate rule: one row per `reading\_ts`. If the same minute arrives again in a later file,

the row with the newest `load\_ts` wins (replaces the old one).



\### Gold



\*\*`gold.hourly\_consumption`\*\* and \*\*`gold.daily\_consumption`\*\* (same columns, different period)



| Column | Type | Notes |

|---|---|---|

| household\_id | string | |

| period\_start | timestamp | start of the hour or day |

| energy\_kwh | double | sum of power / 60 over present minutes |

| kitchen\_kwh | double | Sub\_metering\_1 / 1000 |

| laundry\_kwh | double | Sub\_metering\_2 / 1000 |

| heater\_ac\_kwh | double | Sub\_metering\_3 / 1000 |

| other\_kwh | double | energy\_kwh minus the three sub-meters |

| minutes\_with\_data | int | 0-60 (hour) or 0-1440 (day) |

| is\_complete | boolean | true if all minutes present |

| year, month | int | partitions |



The four `\*\_kwh` breakdown columns are the sub-metering breakdown.



\*\*`gold.daily\_peak`\*\*



| Column | Type | Notes |

|---|---|---|

| household\_id | string | |

| day | date | |

| peak\_hour\_start | timestamp | hour with the highest energy\_kwh that day |

| peak\_hour\_kwh | double | energy of that hour |

| max\_minute\_power\_kw | double | highest single-minute power that day |

| year, month | int | partitions |



\## 6. Data quality rules (silver)



| Rule | Threshold | Why |

|---|---|---|

| reading\_ts is unique | 0 duplicates | duplicate rule worked |

| reading\_ts is not null | 0 nulls | every row must have a time |

| global\_active\_power\_kw null rate | at most 5 % per file | the full file has 1.25 % |

| global\_active\_power\_kw range | 0 to 12 kW | observed 0.076 to 11.122 |

| voltage\_v range | 200 to 260 V | observed 223.2 to 254.15 |

| sub\_metering\_x\_wh range | 0 to 100 Wh | observed max 88 |



\## 7. Demo period



Proposed: 2009-06-01 to 2009-06-08 (the week Person 2's mock data already uses).

To confirm after checking it has good coverage in gold.

