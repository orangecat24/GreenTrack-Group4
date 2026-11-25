"""Exercise the four public tools using Person 3 synthetic gold data."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from assistant.models import ToolInputError
from assistant.tools import FixtureExecutor, HourlyExecutor, QueryTools

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "person3"
FIXTURE = FIXTURE_DIR / "gold_hourly.json"
DAY = {
    "household_id": "household-1",
    "start": "2009-06-01T00:00:00Z",
    "end": "2009-06-02T00:00:00Z",
}


class ToolTests(unittest.TestCase):
    """Verify public results, coverage and validation through QueryTools.run."""

    def setUp(self):
        """Use the unchanged P3 01 fixture through the local executor."""
        self.tools = QueryTools(FixtureExecutor(FIXTURE))
        self.expected = json.loads((FIXTURE_DIR / "gold_daily_expected.json").read_text())

    def test_totals_match_daily_gold_and_coverage(self):
        """Check independently calculated energy, coverage, units and provenance."""
        result = self.tools.run("consumption_totals", **DAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["unit"], "kWh")
        self.assertEqual(result["data"], {"observed_kwh": 9.75})
        self.assertEqual(result["coverage"], self.expected["coverage"])
        self.assertEqual(result["provenance"], {
            "source": "synthetic_fixture", "source_id": "gold_hourly.json",
        })

    def test_patterns_distinguish_partial_null_absent_zero_and_spike(self):
        """Check the hourly grid and read the observed peak from the series."""
        hours = self.tools.run("hourly_patterns", **DAY)["data"]["hours"]
        self.assertEqual(len(hours), 24)
        self.assertEqual(
            [(hour["bucket_status"], hour["observed_kwh"], hour["minutes_with_data"])
             for hour in hours[1:6]],
            [("partial", 0.75, 30), ("all_null", None, 0), ("absent", None, 0),
             ("complete", 0.0, 60), ("complete", 7.5, 60)],
        )
        peak = max((hour for hour in hours if hour["observed_kwh"] is not None),
                   key=lambda hour: hour["observed_kwh"])
        self.assertEqual(peak["period_start"], self.expected["daily_peak"][0]["peak_hour_start"])
        self.assertEqual(peak["observed_kwh"], self.expected["daily_peak"][0]["peak_hour_kwh"])

    def test_comparison_reports_missing_weekend(self):
        """Exclude partial and missing hours and include the measured zero."""
        result = self.tools.run("weekday_weekend", **DAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["weekday"], {
            "mean_kwh_per_complete_hour": 3.0,
            "eligible_hours": 3,
            "coverage": self.expected["coverage"],
        })
        weekend = result["data"]["weekend"]
        self.assertIsNone(weekend["mean_kwh_per_complete_hour"])
        self.assertEqual(weekend["eligible_hours"], 0)
        self.assertEqual(weekend["coverage"]["expected_minutes"], 0)

    def test_comparison_normalizes_unequal_coverage(self):
        """Add one complete Saturday hour and compare using each group's count."""
        payload = json.loads(FIXTURE.read_text())
        saturday = dict(payload["hourly_consumption"][0])
        saturday.update(period_start="2009-06-06T00:00:00Z", energy_kwh=4, other_kwh=2.8)
        payload["hourly_consumption"].append(saturday)
        args = {**DAY, "end": "2009-06-08T00:00:00Z"}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic_comparison.json"
            path.write_text(json.dumps(payload))
            result = QueryTools(FixtureExecutor(path)).run("weekday_weekend", **args)
        weekday, weekend = result["data"]["weekday"], result["data"]["weekend"]
        self.assertEqual((weekday["eligible_hours"], weekend["eligible_hours"]), (3, 1))
        self.assertEqual((weekday["mean_kwh_per_complete_hour"],
                          weekend["mean_kwh_per_complete_hour"]), (3.0, 4.0))
        self.assertEqual(weekend["coverage"]["expected_minutes"], 2880)
        self.assertEqual(weekend["coverage"]["measured_minutes"], 60)

    def test_breakdown_matches_expected_gold_totals(self):
        """Check sums for the three sub-meters and the gold residual."""
        result = self.tools.run("submetering_breakdown", **DAY)
        self.assertEqual(result["status"], "ok")
        for name, total in self.expected["daily_consumption"][0].items():
            if name not in ("kitchen_kwh", "laundry_kwh", "heater_ac_kwh", "other_kwh"):
                continue
            with self.subTest(name=name):
                self.assertAlmostEqual(result["data"][name]["observed_kwh"], total)
                self.assertEqual(result["data"][name]["hours_with_values"], 4)

    def test_breakdown_preserves_nulls_and_signed_residual(self):
        """Keep each column's availability even if another meter is missing."""
        payload = json.loads(FIXTURE.read_text())
        row = payload["hourly_consumption"][0]
        row.update(kitchen_kwh=2, laundry_kwh=None, heater_ac_kwh=0, other_kwh=None)
        corrected = payload["hourly_consumption"][1]
        corrected.update(kitchen_kwh=1, laundry_kwh=0, heater_ac_kwh=0, other_kwh=-0.25)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic_corrected.json"
            path.write_text(json.dumps(payload))
            tools = QueryTools(FixtureExecutor(path))
            first = tools.run(
                "submetering_breakdown", **{**DAY, "end": "2009-06-01T01:00:00Z"}
            )
            result = tools.run(
                "submetering_breakdown", **{**DAY, "end": "2009-06-01T02:00:00Z"}
            )
        self.assertEqual(first["data"]["laundry_kwh"], {"observed_kwh": None, "hours_with_values": 0})
        self.assertEqual(first["data"]["other_kwh"], {"observed_kwh": None, "hours_with_values": 0})
        self.assertEqual(result["data"]["heater_ac_kwh"], {"observed_kwh": 0.0, "hours_with_values": 2})
        self.assertEqual(result["data"]["other_kwh"], {"observed_kwh": -0.25, "hours_with_values": 1})

    def test_offsets_and_half_open_filter(self):
        """Include the normalized start and exclude the normalized end."""
        result = self.tools.run("consumption_totals", household_id="household-1",
                                start="2009-06-01T00:30:00-00:30", end="2009-06-01T04:00+02:00")
        self.assertEqual(result["start"], "2009-06-01T01:00:00Z")
        self.assertEqual(result["end"], "2009-06-01T02:00:00Z")
        self.assertEqual(result["coverage"]["partial_hours"], 1)
        self.assertEqual(result["data"], {"observed_kwh": 0.75})

    def test_no_data_differs_from_zero(self):
        """Report an empty observation independently of a complete zero."""
        cases = [(2, "no_data", None), (3, "no_data", None), (4, "ok", 0.0)]
        for hour, status, expected in cases:
            with self.subTest(hour=hour):
                result = self.tools.run(
                    "consumption_totals", household_id="household-1",
                    start=f"2009-06-01T{hour:02}:00:00Z", end=f"2009-06-01T{hour+1:02}:00:00Z",
                )
                self.assertEqual(result["status"], status)
                self.assertEqual(result["data"], {"observed_kwh": expected})
                self.assertEqual(result["coverage"]["expected_minutes"], 60)

    def test_invalid_arguments_fail_before_reading(self):
        """Block unknown scope, invalid windows and caller-provided SQL."""
        executor = Mock(spec=HourlyExecutor)
        tools = QueryTools(executor)
        for field, value in (
            ("household_id", "household-2"), ("household_id", "household-01"),
            ("household_id", "household-" + "1" * 60), ("household_id", "household-1' OR '1'='1"),
            ("start", "2009-06-01"), ("start", "2009-06-01T00:00:00"),
            ("start", "2009-02-30T00:00:00Z"), ("start", "2009-06-01T00:15:00Z"),
            ("start", "2009-06-01T00:00:00+00:60"), ("end", DAY["start"]),
            ("end", "2009-05-31T00:00:00Z"), ("end", "2009-07-02T01:00:00Z"),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(ToolInputError):
                tools.run("consumption_totals", **{**DAY, field: value})
        with self.assertRaises(ToolInputError):
            tools.run("DELETE FROM hourly_consumption", **DAY)
        with self.assertRaises(TypeError):
            tools.run("consumption_totals", **DAY, table="daily_consumption")
        executor.fetch_hours.assert_not_called()

    def test_exact_maximum_window(self):
        """Accept a 31-day window and bound the returned time grid to 744 rows."""
        result = self.tools.run("hourly_patterns", **{**DAY, "end": "2009-07-02T00:00:00Z"})
        self.assertEqual(len(result["data"]["hours"]), 744)
