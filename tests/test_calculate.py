"""Independent hand-worked 2025 oracles, freshness and deterministic race probes."""

import copy
import importlib.util
import io
import json
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from tests.support import (
    SCRIPTS,
    annual_baseline,
    batch,
    case,
    cli,
    cli_import,
    fixture,
    reviewed_copy,
    temporary,
    wage,
    wage_resolution,
)

# Test support installs the local scripts path before this module is loaded.
calculate = importlib.import_module("calculate")


class CalculateTests(unittest.TestCase):
    def test_hand_worked_baseline_and_due(self):
        expected = fixture()["annual_oracles"]
        with temporary() as parent:
            root, _ = annual_baseline(parent)
            result = case.calculate_case(root, 2025)["estimate"]
            self.assertEqual(Decimal(result["ordinary_tax"]), Decimal("13435.20"))
            self.assertEqual(
                Decimal(result["personal_credit_entitlement"]), Decimal(6534)
            )
            self.assertEqual(Decimal(result["liability"]), Decimal("6901.20"))
            self.assertEqual(result["direction"], expected["baseline"]["direction"])
            self.assertEqual(Decimal(result["balance"]), Decimal("5098.80"))
            self.assertFalse(result["filing_ready"])
            with case.locked(root) as fd:
                self.assertEqual(
                    case.current_result(fd, case.load(root), 2025, case.load_rules()),
                    result,
                )
        with temporary() as parent:
            root = Path(parent) / "case"
            state = case.initialize(root, "fictional-taxpayer", [2025], synthetic=True)
            raw = wage(
                "form_106", "2025-01-01", "2025-12-31", "120000", "5851.20", "due"
            )
            incoming = batch(state, [raw, fixture()["phase2"]["donations"][0]])
            incoming["eligibility"] = [fixture()["phase2"]["profile"]]
            case.import_evidence(root, incoming)
            output = cli("calculate", "--case-root", root, "--tax-year", "2025")
            self.assertEqual(output.returncode, 0, output.stderr)
            result = json.loads(output.stdout)["estimate"]
            self.assertEqual(result["direction"], "estimated_additional_tax")
            self.assertEqual(Decimal(result["liability"]), Decimal("6551.20"))
            self.assertEqual(Decimal(result["balance"]), Decimal(700))
            self.assertEqual(result["tax_year"], 2025)
            self.assertEqual(result["currency"], "ILS")

    def test_conflicting_106_blocks_current_result(self):
        for variant in ("conflicting_106", "withholding_conflict"):
            with self.subTest(variant=variant), temporary() as parent:
                root, state = annual_baseline(parent)
                output = cli("calculate", "--case-root", root, "--tax-year", "2025")
                self.assertEqual(output.returncode, 0, output.stderr)
                original = json.loads(output.stdout)
                old_ref = original["result_reference"]
                old_bytes = (root / old_ref["artifact"]).read_bytes()
                state = case.load(root)
                imported = cli_import(root, state, [fixture()[variant]])
                self.assertEqual(imported.returncode, 0, imported.stderr)
                year = next(
                    v
                    for v in json.loads(imported.stdout)["years"]
                    if v["tax_year"] == 2025
                )
                self.assertIsNone(year["wage_base"])
                self.assertIsNone(year["tax_estimate"])
                state = case.load(root)
                self.assertEqual(state["results"][-1]["status"], "stale")
                self.assertEqual((root / old_ref["artifact"]).read_bytes(), old_bytes)
                blocked = cli("calculate", "--case-root", root, "--tax-year", "2025")
                self.assertNotEqual(blocked.returncode, 0)
                self.assertEqual(
                    json.loads(blocked.stderr)["reason"], "unresolved_income_conflict"
                )
                self.assertEqual(blocked.stdout, "")
                self.assertNotIn('"balance"', (root / "summary.md").read_text())
                selected = next(
                    o
                    for o in state["observations"]
                    if o["issuer"] == "fictional-employer-a"
                    and o["document_type"] == "a99_5"
                )
                resolved = cli_import(
                    root, state, [], [wage_resolution(state, selected)]
                )
                self.assertEqual(resolved.returncode, 0, resolved.stderr)
                fresh = cli("calculate", "--case-root", root, "--tax-year", "2025")
                self.assertEqual(fresh.returncode, 0, fresh.stderr)
                body = json.loads(fresh.stdout)
                self.assertEqual(
                    Decimal(body["estimate"]["balance"]), Decimal("5098.80")
                )
                self.assertNotEqual(
                    body["result_reference"]["input_digest"], old_ref["input_digest"]
                )
                self.assertNotEqual(
                    body["result_reference"]["artifact"], old_ref["artifact"]
                )
                self.assertEqual(case.load(root)["results"][-1]["status"], "current")
                state = case.load(root)
                disputed = reviewed_copy(
                    fixture()["conflicting_106"], business_reference="new-dispute"
                )
                self.assertEqual(cli_import(root, state, [disputed]).returncode, 0)
                self.assertNotEqual(
                    cli(
                        "calculate", "--case-root", root, "--tax-year", "2025"
                    ).returncode,
                    0,
                )

    def test_freshness_metadata_fail_closed(self):
        for variant in (
            "missing",
            "legacy",
            "forged_current",
            "artifact",
            "wrong_case",
            "wrong_year",
            "wrong_scenario",
            "rules",
            "engine",
        ):
            with self.subTest(variant=variant), temporary() as parent:
                root, state = annual_baseline(parent)
                published = case.calculate_case(root, 2025)
                state = case.load(root)
                ref = state["results"][-1]
                pack = case.load_rules()
                if variant == "missing":
                    del ref["freshness_version"]
                elif variant == "legacy":
                    ref["freshness_version"] = 0
                elif variant == "forged_current":
                    state = case.import_evidence(
                        root, batch(state, [fixture()["corroborating"][-1]])
                    )
                    state["results"][-1]["status"] = "current"
                    state["results"][-1].pop("reason", None)
                elif variant == "artifact":
                    with case.locked(root) as fd:
                        content = case.read_private(fd, ref["artifact"])
                        case.atomic_text(fd, ref["artifact"], content + " ")
                elif variant == "wrong_case":
                    with case.locked(root) as fd:
                        artifact = case.parse_json(
                            case.read_private(fd, ref["artifact"])
                        )
                        artifact["case_id"] = "another-case"
                        content = case.canonical(artifact)
                        ref["artifact_sha256"] = case.hashlib.sha256(
                            content
                        ).hexdigest()
                        case.atomic_text(fd, ref["artifact"], content.decode())
                elif variant == "wrong_year":
                    ref["tax_year"] = 2024
                elif variant == "wrong_scenario":
                    ref["scenario"] = "assistance_excluded"
                elif variant == "rules":
                    pack = copy.deepcopy(pack)
                    pack["rules"]["credit_point"]["value"] = "2905"
                with case.locked(root) as fd:
                    case.atomic_text(
                        fd, "checkpoint.json", case.canonical(state).decode()
                    )
                    engine = (
                        "changed-engine" if variant == "engine" else case.ENGINE_VERSION
                    )
                    with (
                        patch.object(case, "ENGINE_VERSION", engine),
                        self.assertRaises(case.CaseError),
                    ):
                        loaded = case.load(root)
                        case.current_result(fd, loaded, 2025, pack)
                self.assertTrue(
                    (root / published["result_reference"]["artifact"]).exists()
                )
        # A new corroborating source invalidates identity, not the independently expected answer.
        with temporary() as parent:
            root, state = annual_baseline(parent)
            first = case.calculate_case(root, 2025)
            state = case.load(root)
            case.import_evidence(root, batch(state, [fixture()["corroborating"][-1]]))
            second = case.calculate_case(root, 2025)
            self.assertNotEqual(
                first["result_reference"]["input_digest"],
                second["result_reference"]["input_digest"],
            )
            self.assertEqual(Decimal(second["estimate"]["balance"]), Decimal("5098.80"))

    def test_evidence_changes_during_calculation(self):
        with temporary() as parent:
            root, state = annual_baseline(parent)
            case.calculate_case(root, 2025)
            state = case.load(root)
            entered, release = threading.Event(), threading.Event()
            original_compute = calculate.compute
            output, errors, exits = io.StringIO(), io.StringIO(), []

            def paused(*args, **kwargs):
                entered.set()
                if not release.wait(10):
                    raise RuntimeError("test barrier timeout")
                return original_compute(*args, **kwargs)

            spec = importlib.util.spec_from_file_location(
                "taxtidy_cli_race", SCRIPTS / "taxtidy.py"
            )
            entry = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(entry)

            def run():
                exits.append(entry.main())

            with (
                patch.object(calculate, "compute", side_effect=paused),
                patch(
                    "sys.argv",
                    [
                        "taxtidy.py",
                        "calculate",
                        "--case-root",
                        str(root),
                        "--tax-year",
                        "2025",
                    ],
                ),
                redirect_stdout(output),
                redirect_stderr(errors),
            ):
                worker = threading.Thread(target=run)
                worker.start()
                try:
                    self.assertTrue(entered.wait(10), "snapshot barrier not reached")
                    case.import_evidence(
                        root, batch(state, [fixture()["conflicting_106"]])
                    )
                finally:
                    release.set()
                    worker.join(10)
                self.assertFalse(worker.is_alive())
            self.assertEqual(exits, [1])
            self.assertEqual(output.getvalue(), "")
            self.assertEqual(
                json.loads(errors.getvalue())["reason"], "calculation_inputs_changed"
            )
            self.assertEqual(len(case.load(root)["results"]), 1)
            self.assertEqual(case.load(root)["results"][0]["status"], "stale")
            self.assertNotIn('"balance"', (root / "summary.md").read_text())
            retry = cli("calculate", "--case-root", root, "--tax-year", "2025")
            self.assertNotEqual(retry.returncode, 0)
            self.assertEqual(retry.stdout, "")

    def test_coverage_money_and_payment_guards(self):
        for invalid in ("NaN", "Infinity", "1e3", "-1", True, 1.0, "0.001"):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(calculate.CalculationError),
            ):
                calculate.number(invalid)
        for variant in (
            "missing_withholding",
            "foreign",
            "pension",
            "year",
            "high_income",
        ):
            with self.subTest(variant=variant), temporary() as parent:
                root, state = annual_baseline(parent)
                if variant in {"foreign", "pension"}:
                    field = (
                        "foreign_facts"
                        if variant == "foreign"
                        else "pension_or_insurance_contributions"
                    )
                    profile = copy.deepcopy(fixture()["phase2"]["profile"])
                    profile["facts"][field] = True
                    profile["supersedes"] = [case.digest(state["eligibility"][0])]
                    profile = reviewed_copy(profile)
                    incoming = batch(state, [])
                    incoming["eligibility"] = [profile]
                    case.import_evidence(root, incoming)
                elif variant in {"missing_withholding", "high_income"}:
                    raw = reviewed_copy(
                        fixture()["baseline"][0],
                        issuer="fictional-employer-c",
                        business_reference="unsupported",
                    )
                    if variant == "missing_withholding":
                        raw["withholding"] = {
                            "value_state": "unknown",
                            "currency": "ILS",
                            "tax_year": 2025,
                        }
                    else:
                        raw["amount"]["amount"] = "721560"
                    case.import_evidence(root, batch(state, [reviewed_copy(raw)]))
                with self.assertRaises(case.CaseError):
                    case.calculate_case(root, 2024 if variant == "year" else 2025)
                self.assertNotIn('"balance"', (root / "summary.md").read_text())
        with temporary() as parent:
            root, state = annual_baseline(parent)
            one = fixture()["phase2"]["advance"]
            two = reviewed_copy(one, business_reference="second-view")
            case.import_evidence(root, batch(state, [one, two]))
            result = case.calculate_case(root, 2025)["estimate"]
            self.assertEqual(Decimal(result["advance_tax_payments"]), Decimal(500))
            self.assertEqual(Decimal(result["balance"]), Decimal("5598.80"))

    def test_donation_threshold_cap_and_unknown_dates(self):
        for value, eligible, credit, carry in (
            ("207", "0", "0", "0"),
            ("208", "208", "72.80", "0"),
            ("40000", "36000", "6901.20", "4000"),
        ):
            with self.subTest(value=value), temporary() as parent:
                root, state = annual_baseline(parent)
                raw = copy.deepcopy(fixture()["phase2"]["donations"][0])
                raw["amount"]["amount"] = value
                raw["details"]["payroll_applied_credit"]["amount"] = "0"
                case.import_evidence(root, batch(state, [reviewed_copy(raw)]))
                result = case.calculate_case(root, 2025)["estimate"]
                self.assertEqual(
                    Decimal(result["eligible_donation"]), Decimal(eligible)
                )
                self.assertEqual(Decimal(result["donation_credit"]), Decimal(credit))
                self.assertEqual(
                    Decimal(result["potential_donation_carryforward"]), Decimal(carry)
                )
        with temporary() as parent:
            root, state = annual_baseline(parent)
            raw = reviewed_copy(fixture()["phase2"]["donations"][0], event_date=None)
            case.import_evidence(root, batch(state, [raw]))
            with self.assertRaisesRegex(
                case.CaseError, "unverified_donation_eligibility"
            ):
                case.calculate_case(root, 2025)

    def test_cli_donation_and_direct_reserve_date_guards(self):
        for kind, source, flag, reason in (
            (
                "donation",
                fixture()["phase2"]["donations"][0],
                "settled_same_year",
                "unverified_donation_eligibility",
            ),
            (
                "reserve",
                fixture()["phase2"]["reserve"][1],
                "same_year_receipt_and_service",
                "unsupported_reserve_program_or_allocation",
            ),
        ):
            for event, settlement, attested in (
                ("2024-12-31", "2025-01-02", True),
                ("2026-01-01", "2025-12-31", True),
                ("2025-01-02", "2024-12-31", True),
                ("2025-12-31", "2026-01-01", True),
                ("2024-12-31", "2024-12-31", True),
                ("2026-01-01", "2026-01-01", True),
                (None, "2025-06-01", True),
                ("2025-06-01", None, True),
                (None, None, True),
                ("2025-06-01", "2025-06-01", False),
            ):
                with (
                    self.subTest(
                        kind=kind, event=event, settlement=settlement, attested=attested
                    ),
                    temporary() as parent,
                ):
                    root, _ = annual_baseline(parent)
                    initial = cli(
                        "calculate", "--case-root", root, "--tax-year", "2025"
                    )
                    self.assertEqual(initial.returncode, 0, initial.stderr)
                    old = json.loads(initial.stdout)["result_reference"]
                    old_bytes = (root / old["artifact"]).read_bytes()
                    raw = copy.deepcopy(source)
                    raw.update(event_date=event, settlement_date=settlement)
                    raw["details"][flag] = attested
                    if kind == "donation":
                        raw["details"].update(
                            approval_from="2024-01-01", approval_to="2026-12-31"
                        )
                    imported = cli_import(root, case.load(root), [reviewed_copy(raw)])
                    self.assertEqual(imported.returncode, 0, imported.stderr)
                    state = case.load(root)
                    self.assertEqual(state["results"][-1]["status"], "stale")
                    checkpoint = (root / "checkpoint.json").read_bytes()
                    blocked = cli(
                        "calculate", "--case-root", root, "--tax-year", "2025"
                    )
                    self.assertEqual(blocked.returncode, 1)
                    self.assertEqual(blocked.stdout, "")
                    self.assertEqual(
                        json.loads(blocked.stderr), {"ok": False, "reason": reason}
                    )
                    self.assertEqual(
                        (root / "checkpoint.json").read_bytes(), checkpoint
                    )
                    self.assertEqual((root / old["artifact"]).read_bytes(), old_bytes)
                    self.assertEqual(len(list((root / "calculations").iterdir())), 1)
                    self.assertTrue(
                        all(r["status"] == "stale" for r in case.load(root)["results"])
                    )
                    self.assertEqual(
                        (root / "summary.md").read_text(),
                        "Recalculation required. Previous estimates are unavailable.\n",
                    )

    def test_cli_same_year_date_boundaries_remain_supported(self):
        for source, liability, refund in (
            (fixture()["phase2"]["donations"][0], "6551.20", "5448.80"),
            (fixture()["phase2"]["reserve"][1], "8858", "5142"),
        ):
            with self.subTest(kind=source["kind"]), temporary() as parent:
                root, state = annual_baseline(parent)
                raw = reviewed_copy(
                    source, event_date="2025-01-01", settlement_date="2025-12-31"
                )
                self.assertEqual(raw["issue_date"], "2026-02-01")
                imported = cli_import(root, state, [raw])
                self.assertEqual(imported.returncode, 0, imported.stderr)
                output = cli("calculate", "--case-root", root, "--tax-year", "2025")
                self.assertEqual(output.returncode, 0, output.stderr)
                result = json.loads(output.stdout)["estimate"]
                self.assertEqual(result["status"], "estimated")
                self.assertEqual(result["tax_year"], 2025)
                self.assertEqual(result["currency"], "ILS")
                self.assertEqual(result["direction"], "estimated_refund")
                self.assertEqual(Decimal(result["liability"]), Decimal(liability))
                self.assertEqual(Decimal(result["balance"]), Decimal(refund))

    def test_pre_date_fix_engine_results_are_not_current(self):
        with temporary() as parent:
            root, _ = annual_baseline(parent)
            legacy_pack = case.load_rules()
            legacy_pack["engine_version"] = "0.2.0"
            with (
                patch.object(case, "ENGINE_VERSION", "0.2.0"),
                patch.object(calculate, "ENGINE_VERSION", "0.2.0"),
                patch.object(case, "load_rules", return_value=legacy_pack),
            ):
                legacy = case.calculate_case(root, 2025)
            state = case.load(root)
            self.assertEqual(state["results"][-1]["status"], "current")
            with (
                case.locked(root) as fd,
                self.assertRaisesRegex(case.CaseError, "stale_calculation"),
            ):
                case.current_result(fd, state, 2025, case.load_rules())
            fresh = cli("calculate", "--case-root", root, "--tax-year", "2025")
            self.assertEqual(fresh.returncode, 0, fresh.stderr)
            result = json.loads(fresh.stdout)
            self.assertEqual(result["result_reference"]["engine_version"], "0.2.1")
            self.assertNotEqual(
                result["result_reference"]["input_digest"],
                legacy["result_reference"]["input_digest"],
            )
            self.assertEqual(Decimal(result["estimate"]["balance"]), Decimal("5098.80"))
            self.assertEqual(case.load(root)["results"][0]["status"], "stale")

    def test_securities_prior_offset_and_unsupported_facts(self):
        for invalid in (False, True):
            with self.subTest(invalid=invalid), temporary() as parent:
                root, state = annual_baseline(parent)
                raw = copy.deepcopy(fixture()["phase2"]["banks"][0])
                raw["details"]["realized_loss"]["amount"] = "5000"
                raw["details"]["prior_offset"]["amount"] = "2000"
                if invalid:
                    raw["details"]["foreign_tax"]["amount"] = "1"
                case.import_evidence(root, batch(state, [reviewed_copy(raw)]))
                if invalid:
                    with self.assertRaisesRegex(
                        case.CaseError, "unsupported_securities_facts"
                    ):
                        case.calculate_case(root, 2025)
                else:
                    result = case.calculate_case(root, 2025)["estimate"]
                    self.assertEqual(Decimal(result["income"]["gains"]), Decimal(6000))
                    self.assertEqual(Decimal(result["income"]["losses"]), Decimal(3000))
                    self.assertEqual(
                        Decimal(result["remaining_realized_gain"]), Decimal(3000)
                    )
                    self.assertEqual(Decimal(result["liability"]), Decimal("7651.20"))

    def test_calculation_directory_is_private_and_no_follow(self):
        with temporary() as parent:
            root, _ = annual_baseline(parent)
            public = case.calculate_case(root, 2025)
            self.assertEqual((root / "calculations").stat().st_mode & 0o777, 0o700)
            self.assertEqual(
                (root / public["result_reference"]["artifact"]).stat().st_mode & 0o777,
                0o600,
            )
        with temporary() as parent:
            root, _ = annual_baseline(parent)
            destination = Path(parent) / "other"
            destination.mkdir(mode=0o700)
            (root / "calculations").symlink_to(destination, target_is_directory=True)
            with self.assertRaises(OSError):
                case.calculate_case(root, 2025)
            self.assertEqual(list(destination.iterdir()), [])
            self.assertEqual(case.load(root)["results"], [])


if __name__ == "__main__":
    unittest.main()
