from __future__ import annotations

import unittest

from law_firm_digital_twin.models import Arm, Route
from law_firm_digital_twin.simulation import run_all_routes, run_walking_skeleton


class WalkingSkeletonTests(unittest.TestCase):
    def test_replay_is_hash_stable(self) -> None:
        first = run_all_routes("alpha")
        second = run_all_routes("alpha")
        self.assertEqual(first["bundle_hash"], second["bundle_hash"])

    def test_all_routes_close_and_reconcile(self) -> None:
        result = run_all_routes("alpha")
        self.assertEqual(len(result["runs"]), 8)
        for run in result["runs"]:
            self.assertTrue(run["closed"])
            self.assertEqual(run["finance_errors"], [])
            self.assertTrue(run["synthetic_non_predictive"])

    def test_oracle_access_is_blocked(self) -> None:
        run = run_walking_skeleton("alpha", Arm.AI_FIRST, Route.TRIAL_APPEAL)
        self.assertTrue(run["oracle_blocked"])
        self.assertEqual(run["human_gate_bypasses"], 0)

    def test_deadlines_are_derived_from_placeholder_rule_pack(self) -> None:
        run = run_walking_skeleton("alpha", Arm.TRADITIONAL, Route.EARLY_SETTLEMENT)
        self.assertEqual(run["deadlines"]["response_due"], 21)
        self.assertEqual(run["deadlines"]["initial_disclosures_due"], 30)
        self.assertEqual(run["deadlines"]["discovery_cutoff"], 180)
        self.assertEqual(run["matter"]["rule_pack"]["jurisdiction_label"], "DATA_FIRST_PENDING")

    def test_arms_receive_same_world_under_same_seed(self) -> None:
        traditional = run_walking_skeleton("alpha", Arm.TRADITIONAL, Route.DISPOSITIVE)
        ai_first = run_walking_skeleton("alpha", Arm.AI_FIRST, Route.DISPOSITIVE)
        self.assertEqual(traditional["matter"]["hidden_truth_hash"], ai_first["matter"]["hidden_truth_hash"])
        self.assertEqual(traditional["matter"]["operating_record_hash"], ai_first["matter"]["operating_record_hash"])


if __name__ == "__main__":
    unittest.main()

