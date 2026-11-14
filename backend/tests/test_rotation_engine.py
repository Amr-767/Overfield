"""Pure rotation-engine tests; every crop/season value is a synthetic fixture."""

from __future__ import annotations

import unittest

from apps.agronomy.rotation import assess_rotation_inputs


class RotationAssessmentTests(unittest.TestCase):
    def assess(self, **overrides):
        values = {
            "region_code": "EG-GH",
            "crop_history": [],
            "calendar": None,
            "crop_profiles": [],
            "environmental_inputs": [],
            "planning_seasons": 2,
        }
        values.update(overrides)
        return assess_rotation_inputs(**values)

    def test_empty_history_and_empty_catalog_return_honest_insufficient_evidence(self):
        result = self.assess()
        self.assertEqual(result.status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result.options, ())
        missing = {item["name"] for item in result.missing}
        self.assertIn("crop_history", missing)
        self.assertIn("regional_crop_calendar", missing)
        self.assertIn("eligible_crop_profiles", missing)

    def test_incomplete_history_and_crop_names_without_codes_are_not_guessed(self):
        result = self.assess(crop_history=[{"season": "Season 1", "crop": "Uncatalogued name", "crop_code": None}])
        missing = {item["name"] for item in result.missing}
        self.assertIn("crop_history_crop_codes", missing)
        self.assertIn("baseline_horizon", missing)

    def test_conflicting_history_season_labels_are_flagged(self):
        result = self.assess(crop_history=[
            {"season": "Winter", "crop": "A", "crop_code": "A"},
            {"season": "winter", "crop": "B", "crop_code": "B"},
        ])
        self.assertIn("crop_history_conflicts", {item["name"] for item in result.missing})

    def test_missing_stale_and_incompatible_environmental_evidence_is_not_used_as_suitability(self):
        result = self.assess(environmental_inputs=[
            {"date": "2020-01-01", "value": "22", "parameter": "T2M", "unit": "C", "source": "NASA_POWER", "freshness": "STALE"},
            {"date": "2020-01-01", "value": None, "parameter": "PRECTOTCORR", "unit": "mm/day", "source": "NASA_POWER", "quality": "MISSING"},
            {"date": "2020-01-02", "value": "7", "parameter": "RH2M", "source": "NASA_POWER"},
        ])
        self.assertEqual(result.options, ())
        self.assertIn("environmental_provenance", {item["name"] for item in result.missing})
        self.assertEqual(len(result.environmental_inputs), 2)

    def test_unapproved_or_unreferenced_hard_rule_cannot_exclude_candidates(self):
        result = self.assess(documented_constraints=[
            {"id": "unsafe", "approved": True, "rule_type": "FORBID_ADJACENT_CROP", "crop_code": "A"},
            {"id": "unapproved", "approved": False, "evidence_id": "ev", "source": "manual"},
        ])
        self.assertEqual(result.constraints, ())
        self.assertEqual(len(result.rejected_alternatives), 1)
        self.assertIn("lacks a traceable source", result.rejected_alternatives[0]["reason"])

    def test_candidate_missing_profile_or_dates_is_rejected_with_reason(self):
        result = self.assess(
            crop_profiles=[{"crop_code": "A", "characteristics": []}],
            candidate_rotations=[{"id": "fixture", "seasons": [
                {"season_code": "S1", "crop_code": "A", "start_date": "2026-01-01", "end_date": "2026-06-30", "evidence_ids": ["ev-1"]},
                {"season_code": "S2", "crop_code": "B", "evidence_ids": ["ev-2"]},
            ]}],
            planning_seasons=2,
        )
        self.assertEqual(result.status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result.options, ())
        self.assertTrue(any("No eligible source-backed profile" in item["reason"] for item in result.rejected_alternatives))

    def test_evidence_backed_candidate_is_explainable_and_never_scored(self):
        result = self.assess(
            crop_history=[
                {"season": "S-1", "crop": "B", "crop_code": "B"},
                {"season": "S0", "crop": "A", "crop_code": "A"},
            ],
            calendar={"seasons": [{"season_code": "S1", "evidence_ids": ["calendar-ev"]}]},
            crop_profiles=[{"crop_code": code, "characteristics": [
                {"trait": "example_trait", "value": "unknown", "unit": None,
                 "source": "fixture-dataset", "dataset_version": "fixture-v1",
                 "geographic_applicability": "GENERAL"}
            ]} for code in ("A", "B")],
            environmental_inputs=[{"date": "2026-01-01", "value": "20", "parameter": "T2M", "unit": "C", "source": "NASA_POWER"}],
            candidate_rotations=[{"id": "fixture-candidate", "seasons": [
                {"season_code": "S1", "allowed_crop_codes": ["A"], "start_date": "2026-01-01", "end_date": "2026-06-30", "crop_code": "A", "evidence_ids": ["ev-1"]},
                {"season_code": "S2", "allowed_crop_codes": ["B"], "start_date": "2026-07-01", "end_date": "2026-12-31", "crop_code": "B", "evidence_ids": ["ev-2"]},
            ]}],
            planning_seasons=2,
        )
        self.assertEqual(result.status, "OPTIONS_AVAILABLE")
        candidate = next(option for option in result.options if option["option_id"] == "fixture-candidate")
        self.assertGreaterEqual(len(result.options), 1)
        self.assertIsNone(candidate["score"])
        self.assertEqual(candidate["evidence"], ["ev-1", "ev-2"])

    def test_approved_rule_with_traceable_evidence_excludes_incompatible_sequence(self):
        result = self.assess(
            crop_profiles=[{"crop_code": "A", "characteristics": []}],
            documented_constraints=[{"id": "rule-1", "approved": True, "source": "reviewed rulebook", "evidence_id": "rule-ev", "rule_type": "FORBID_ADJACENT_CROP", "crop_code": "A"}],
            candidate_rotations=[{"id": "fixture", "seasons": [
                {"season_code": "S1", "allowed_crop_codes": ["A"], "start_date": "2026-01-01", "end_date": "2026-06-30", "crop_code": "A", "evidence_ids": ["ev-1"]},
                {"season_code": "S2", "allowed_crop_codes": ["A"], "start_date": "2026-07-01", "end_date": "2026-12-31", "crop_code": "A", "evidence_ids": ["ev-2"]},
            ]}],
            planning_seasons=2,
        )
        self.assertEqual(result.options, ())
        self.assertEqual(len(result.rejected_alternatives), 1)
        self.assertIn("rule-ev", result.rejected_alternatives[0]["reason"])


if __name__ == "__main__":
    unittest.main()
