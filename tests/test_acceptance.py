"""Nine synthetic acceptance cases and a report from these same executed tests."""

import argparse
import copy
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

from tests.support import (
    annual_baseline,
    baseline,
    batch,
    case,
    cli,
    fixture,
    observe,
    reviewed_copy,
    temporary,
)
from tests.test_workflow import (
    deadline_due_case,
    dividend_link,
    record,
    selected_year,
    view,
)


class AcceptanceTests(unittest.TestCase):
    def test_01_wage_overlap(self):
        data = fixture()
        for reverse in (False, True):
            with self.subTest(reverse=reverse), temporary() as parent:
                root, state = baseline(parent)
                before = next(
                    y for y in case.wage_summary(state) if y["tax_year"] == 2025
                )
                self.assertEqual(before["wage_base"], data["expected"]["wage_base"])
                observations = (
                    list(reversed(data["corroborating"]))
                    if reverse
                    else data["corroborating"]
                )
                for obs in observations:
                    state = case.import_evidence(root, batch(state, [obs]))
                    self.assertEqual(
                        next(
                            y for y in case.wage_summary(state) if y["tax_year"] == 2025
                        )["wage_base"],
                        "120000",
                    )
                state = case.load(root)
                self.assertEqual(len(state["economic_items"]), 2)
                self.assertEqual(len(state["observations"]), 5)
                self.assertTrue(
                    all(r["status"] == "resolved" for r in state["requirements"])
                )
                observe(
                    self,
                    "overlap-reversed-" + str(reverse),
                    {"wages": data["baseline"], "corroboration": observations},
                    {"wage_base": "120000", "items": 2, "observations": 5},
                    {
                        "wage_summary": case.wage_summary(state),
                        "items": len(state["economic_items"]),
                        "observations": len(state["observations"]),
                        "revision": state["revision"],
                    },
                )
                repeated = case.import_evidence(
                    root, batch(state, data["corroborating"])
                )
                self.assertEqual(repeated, state)
                state = case.import_evidence(
                    root, batch(state, [data["conflicting_106"]])
                )
                self.assertTrue(state["conflicts"])
                self.assertEqual(
                    next(
                        i
                        for i in state["economic_items"]
                        if i["issuer"] == "fictional-employer-a"
                    )["amount"]["amount"],
                    "80000",
                )
                self.assertIsNone(
                    next(y for y in case.wage_summary(state) if y["tax_year"] == 2025)[
                        "wage_base"
                    ]
                )

                observe(
                    self,
                    "conflicting-106-" + str(reverse),
                    data["conflicting_106"],
                    {"wage_base": None, "conflict_required": True},
                    {
                        "wage_summary": case.wage_summary(state),
                        "conflicts": state["conflicts"],
                        "revision": state["revision"],
                    },
                )

    def test_02_banks(self):
        balances = []
        for extra_withholding in ("2000", "2500"):
            with self.subTest(withholding=extra_withholding), temporary() as parent:
                root = Path(parent) / "case"
                state = case.initialize(
                    root, "fictional-taxpayer", [2025], synthetic=True
                )
                banks = copy.deepcopy(fixture()["phase2"]["banks"])
                banks[0]["withholding"]["amount"] = extra_withholding
                banks[0] = reviewed_copy(banks[0])
                incoming = batch(state, banks)
                incoming["eligibility"] = [fixture()["phase2"]["profile"]]
                case.import_evidence(root, incoming)
                result = case.calculate_case(root, 2025)["estimate"]
                self.assertEqual(
                    Decimal(result["remaining_realized_gain"]), Decimal(3000)
                )
                self.assertEqual(
                    Decimal(result["capital_tax_before_credits"]), Decimal(750)
                )
                self.assertEqual(Decimal(result["liability"]), Decimal(0))
                self.assertEqual(Decimal(result["balance"]), Decimal(extra_withholding))
                self.assertEqual(result["direction"], "estimated_refund")
                observe(
                    self,
                    "withholding-" + extra_withholding,
                    banks,
                    {
                        "remaining_gain": "3000",
                        "capital_tax_before_credits": "750",
                        "liability": "0",
                        "balance": extra_withholding,
                    },
                    result,
                )
                balances.append(Decimal(result["balance"]))
        self.assertEqual(balances[1] - balances[0], Decimal(500))

    def test_03_donation_duplicates_and_payroll(self):
        with temporary() as parent:
            root, state = annual_baseline(parent)
            donations = fixture()["phase2"]["donations"]
            state = case.import_evidence(root, batch(state, donations[:1]))
            first = case.calculate_case(root, 2025)["estimate"]
            state = case.load(root)
            case.import_evidence(root, batch(state, donations[1:]))
            result = case.calculate_case(root, 2025)["estimate"]
            for value in (first, result):
                self.assertEqual(Decimal(value["income"]["donations"]), Decimal(1000))
                self.assertEqual(
                    Decimal(value["income"]["payroll_donation_credit"]), Decimal(350)
                )
                self.assertEqual(Decimal(value["donation_credit"]), Decimal(350))
                self.assertEqual(Decimal(value["israeli_tax_withheld"]), Decimal(12000))
                self.assertEqual(Decimal(value["liability"]), Decimal("6551.20"))
                self.assertEqual(Decimal(value["balance"]), Decimal("5448.80"))
            items = [
                i for i in case.load(root)["economic_items"] if i["kind"] == "donation"
            ]
            self.assertEqual(len(items), 1)
            self.assertEqual(len(items[0]["observations"]), 3)

            observe(
                self,
                "one-versus-three-sources",
                donations,
                {
                    "donation": "1000",
                    "credit": "350",
                    "liability": "6551.20",
                    "refund": "5448.80",
                },
                {"one_source": first, "three_sources": result, "items": items},
            )

    def test_05_reserve_and_assistance_scenarios(self):
        with temporary() as parent:
            root, state = annual_baseline(parent)
            case.import_evidence(root, batch(state, fixture()["phase2"]["reserve"]))
            with self.assertRaisesRegex(
                case.CaseError, "unresolved_assistance_program"
            ):
                case.calculate_case(root, 2025)
            estimates = {}
            for scenario, liability, refund, ordinary in (
                ("assistance_excluded", "8858", "5142", "130000"),
                ("assistance_taxable", "9258", "4742", "132000"),
            ):
                result = case.calculate_case(root, 2025, scenario)["estimate"]
                self.assertEqual(result["status"], "scenario_estimate")
                self.assertIsNotNone(result["scenario_condition"])
                self.assertEqual(Decimal(result["income"]["wages"]), Decimal(120000))
                self.assertEqual(
                    Decimal(result["income"]["employer_reserve_in_wages"]),
                    Decimal(10000),
                )
                self.assertEqual(
                    Decimal(result["income"]["direct_reserve"]), Decimal(10000)
                )
                self.assertEqual(
                    Decimal(result["taxable_ordinary_income"]), Decimal(ordinary)
                )
                self.assertEqual(
                    Decimal(result["israeli_tax_withheld"]), Decimal(14000)
                )
                self.assertEqual(Decimal(result["liability"]), Decimal(liability))
                self.assertEqual(Decimal(result["balance"]), Decimal(refund))
                self.assertEqual(result["direction"], "estimated_refund")
                observe(
                    self,
                    scenario,
                    fixture()["phase2"]["reserve"],
                    {
                        "liability": liability,
                        "refund": refund,
                        "ordinary_income": ordinary,
                    },
                    result,
                )
                estimates[scenario] = Decimal(result["liability"])
            self.assertEqual(
                estimates["assistance_taxable"] - estimates["assistance_excluded"],
                Decimal(400),
            )

    def test_04_equity_events(self):
        with temporary() as parent:
            root, _ = annual_baseline(parent)
            case.calculate_case(root, 2025)
            for event in fixture()["phase3"]["equity"]:
                output = record(root, event)
                self.assertEqual(output.returncode, 0, output.stderr)
            row = selected_year(json.loads(view(root).stdout))
            self.assertIsNone(row["estimate"])
            events = row["equity"]["events"]
            self.assertEqual(len(events), 4)
            self.assertEqual(
                sum(e["status"] == "unmatched_dividend" for e in events), 2
            )
            self.assertTrue(
                any(e["status"] == "vesting_does_not_prove_sale" for e in events)
            )
            self.assertTrue(
                any(e["status"] == "payroll_component_already_in_wages" for e in events)
            )
            self.assertTrue(
                all(e["wage_component_counted_again"] is False for e in events)
            )
            self.assertEqual(
                next(
                    y
                    for y in case.wage_summary(case.load(root))
                    if y["tax_year"] == 2025
                )["wage_base"],
                "120000",
            )
            self.assertTrue(
                any("net cash" in q["question"] for q in row["equity"]["questions"])
            )
            observe(
                self,
                "unresolved-equity",
                fixture()["phase3"]["equity"],
                {"estimate": None, "events": 4, "unmatched_dividends": 2},
                row,
            )
            dividends = []
            for event in case.workflow_records(case.load(root), "equity", 2025):
                if event["details"]["event_type"] != "dividend":
                    continue
                corrected = copy.deepcopy(event)
                corrected["details"]["destination"] = "fictional-net-cash-account"
                corrected = reviewed_copy(corrected, supersedes=[case.digest(event)])
                dividends.append(corrected)
                self.assertEqual(record(root, corrected).returncode, 0)
            row = selected_year(json.loads(view(root, "resume").stdout))
            self.assertEqual(
                sum(
                    e["status"] == "unmatched_dividend" for e in row["equity"]["events"]
                ),
                2,
            )
            proof = dividend_link(dividends)
            self.assertEqual(record(root, proof).returncode, 0)
            row = selected_year(json.loads(view(root, "resume").stdout))
            matched = [
                e for e in row["equity"]["events"] if e["event_type"] == "dividend"
            ]
            self.assertEqual(len(matched), 2)
            self.assertTrue(
                all(
                    e["status"] == "matched_dividend_one_event"
                    and e["match_evidence"] == [case.digest(proof)]
                    for e in matched
                )
            )
            self.assertTrue(
                all(
                    q["event"] not in {case.digest(e) for e in dividends}
                    for q in row["equity"]["questions"]
                )
            )
            self.assertIsNone(row["estimate"])
            self.assertFalse(row["equity"]["complete_annual_calculation"])
            separate = []
            for original in dividends:
                event = copy.deepcopy(original)
                event.pop("supersedes", None)
                event["details"]["gross"]["amount"] = "200"
                event["details"]["account"] += "-distinct-payment"
                event = reviewed_copy(event, reference=event["reference"] + "-distinct")
                separate.append(event)
                self.assertEqual(record(root, event).returncode, 0)
            conflicting = dividend_link(separate, "same-payment-disjoint-claim")
            self.assertEqual(record(root, conflicting).returncode, 0)
            row = selected_year(json.loads(view(root, "resume").stdout))
            all_dividends = [
                e for e in row["equity"]["events"] if e["event_type"] == "dividend"
            ]
            self.assertEqual(len(all_dividends), 4)
            self.assertTrue(
                all(
                    e["status"] == "unmatched_dividend" and not e["match_evidence"]
                    for e in all_dividends
                )
            )
            self.assertTrue(
                {case.digest(e) for e in dividends + separate}.issubset(
                    {q["event"] for q in row["equity"]["questions"]}
                )
            )
            corrected = copy.deepcopy(conflicting)
            corrected["details"]["payment_reference"] = "separate-payment-reference"
            corrected = reviewed_copy(
                corrected,
                reference="institution-corrected-disjoint-claim",
                supersedes=[case.digest(conflicting)],
            )
            self.assertEqual(record(root, corrected).returncode, 0)
            row = selected_year(json.loads(view(root, "resume").stdout))
            self.assertEqual(
                sum(
                    e["status"] == "matched_dividend_one_event"
                    for e in row["equity"]["events"]
                ),
                4,
            )
            self.assertIsNone(row["estimate"])

            observe(
                self,
                "source-backed-link-correction",
                corrected,
                {"matched_dividends": 4, "estimate": None},
                row,
            )

    def test_06_deadline_and_due(self):
        with temporary() as parent:
            root = deadline_due_case(parent)
            output = record(root, fixture()["phase3"]["deadline"])
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertEqual(
                json.loads(
                    cli("calculate", "--case-root", root, "--tax-year", "2025").stdout
                )["estimate"]["direction"],
                "estimated_additional_tax",
            )
            output = view(root)
            self.assertEqual(output.returncode, 0, output.stderr)
            public = json.loads(output.stdout)
            self.assertEqual(public["years"][0]["tax_year"], 2020)
            urgent = public["years"][0]["deadlines"][0]
            self.assertEqual(urgent["effective_deadline"], "2026-12-31")
            self.assertEqual(urgent["category"], "refund_claim")
            self.assertEqual(
                urgent["source_url"], "https://www.gov.il/he/service/itc135"
            )
            due = selected_year(public)["estimate"]
            self.assertEqual(Decimal(due["balance"]), Decimal(700))
            self.assertEqual(due["tax_year"], 2025)
            self.assertEqual(due["currency"], "ILS")

            observe(
                self,
                "urgent-year-and-independent-due",
                fixture()["phase3"]["deadline"],
                {
                    "first_year": 2020,
                    "refund_deadline": "2026-12-31",
                    "due_2025": "700",
                },
                public,
            )

    def test_07_protected_signed_and_hebrew_scan(self):
        from tests.test_pdf import exercise_acceptance

        with temporary() as parent:
            result = exercise_acceptance(self, parent)
            observe(
                self,
                "protected-signed-hebrew-scan",
                {"source_hashes": result["source_hashes"], "synthetic": True},
                {
                    "wages": "80000",
                    "withholding": "8000",
                    "adjustment": "-450",
                    "empty": "blank",
                    "wrong_password": "incorrect_pdf_password",
                    "signature": "present_unvalidated",
                    "scan_ready": False,
                },
                {
                    key: result[key]
                    for key in ("wrong", "correct", "signed", "scan", "signature")
                },
            )
        from tests.test_pdf import PDFTests

        for method in (
            "test_corruption_rotation_mixed_batch_and_limits",
            "test_actual_comparison_and_worker_timeouts",
            "test_paths_authorization_and_concealed_cli",
        ):
            suite = unittest.TestSuite([PDFTests(method)])
            result = unittest.TestResult()
            result.failfast = True
            suite.run(result)
            observe(
                self,
                method,
                {"source": "tests/test_pdf.py::PDFTests." + method},
                {"tests_run": 1, "failures": 0, "errors": 0, "skipped": 0},
                {
                    "tests_run": result.testsRun,
                    "failures": len(result.failures),
                    "errors": len(result.errors),
                    "skipped": len(result.skipped),
                },
            )
            self.assertTrue(result.wasSuccessful() and not result.skipped, method)
            self.assertEqual(result.testsRun, 1)

    def test_08_upload_draft(self):
        with temporary() as parent:
            root, _ = annual_baseline(parent)
            for name in ("draft", "rejected", "accepted"):
                output = record(root, fixture()["phase3"][name])
                self.assertEqual(output.returncode, 0, output.stderr)
            row = selected_year(json.loads(view(root, "resume").stdout))
            self.assertEqual(row["filing"]["state"], "draft")
            self.assertEqual(
                {
                    (e["filename"], e["tax_year"], e["status"])
                    for e in row["filing"]["attachments"]
                },
                {
                    ("bank-2025-original.pdf", 2025, "rejected"),
                    ("bank-2025-corrected.pdf", 2025, "accepted"),
                },
            )
            self.assertTrue(
                all(
                    e["draft_version"] == "draft-1" and e["form"] == "135"
                    for e in row["filing"]["attachments"]
                )
            )

            observe(
                self,
                "upload-retry-draft",
                {k: fixture()["phase3"][k] for k in ("draft", "rejected", "accepted")},
                {"filing_state": "draft", "acknowledgment": None},
                row,
            )

    def test_09_resume_languages(self):
        for language in ("ru", "ar"):
            with self.subTest(language=language), temporary() as parent:
                root, _ = annual_baseline(parent)
                original = case.calculate_case(root, 2025)
                state = case.load(root)
                path = root.parent / "new-record.json"
                path.write_text(
                    json.dumps(batch(state, [fixture()["conflicting_106"]]))
                )
                path.chmod(0o600)
                output = cli(
                    "resume",
                    "--case-root",
                    root,
                    "--language",
                    language,
                    "--input",
                    path,
                    "--as-of",
                    "2026-11-19",
                )
                self.assertEqual(output.returncode, 0, output.stderr)
                public = json.loads(output.stdout)
                row = selected_year(public)
                self.assertEqual(public["preferred_language"], language)
                self.assertFalse(public["mailbox_connected"])
                self.assertIsNone(row["estimate"])
                self.assertIsNone(row["result_reference"])
                self.assertIn("unresolved_income_conflict", row["reasons"])
                self.assertEqual(row["next_control_he"], "להגשת הבקשה")
                table = next(y for y in public["year_table"] if y["tax_year"] == 2025)
                self.assertEqual(table["next_control_he"], "להגשת הבקשה")
                self.assertEqual(table["control_scope"], row["control_scope"])
                self.assertIn("route eligibility", table["control_scope"])
                unsupported = selected_year(public, 2024)
                self.assertIn("unsupported_tax_year", unsupported["reasons"])
                self.assertNotIn(
                    "recalculat",
                    json.dumps(unsupported["next_evidence"]).lower(),
                )
                self.assertEqual(row["next_evidence"][0]["document_he"], "טופס 106")
                self.assertTrue(
                    all(
                        r["status"] == "resolved"
                        for r in case.load(root)["requirements"]
                    )
                )

                observe(
                    self,
                    "resume-" + language,
                    {
                        "new_evidence": fixture()["conflicting_106"],
                        "mailbox": False,
                        "prior_result": original,
                    },
                    {
                        "estimate": None,
                        "reason": "unresolved_income_conflict",
                        "next_control_he": "להגשת הבקשה",
                    },
                    public,
                )


def report(path):
    names = unittest.defaultTestLoader.getTestCaseNames(AcceptanceTests)
    rows = []
    stopped = False
    for number, name in enumerate(names, 1):
        test = AcceptanceTests(name)
        result = unittest.TestResult()
        result.failfast = True
        if not stopped:
            test.run(result)
            passed = (
                result.testsRun == 1
                and result.wasSuccessful()
                and not result.skipped
                and not result.expectedFailures
                and bool(getattr(test, "observations", []))
            )
            status = "PASS" if passed else "FAIL"
            stopped = not passed
        else:
            status = "NOT_RUN"
        rows.append(
            {
                "number": number,
                "test": name,
                "status": status,
                "observations": getattr(test, "observations", []),
                "failures": [
                    str(error) for _, error in result.failures + result.errors
                ],
                "skipped": [str(reason) for _, reason in result.skipped],
            }
        )
    passed = len(rows) == 9 and all(row["status"] == "PASS" for row in rows)
    document = {
        "synthetic_only": True,
        "overall": "PASS" if passed else "FAIL",
        "cases": rows,
        "visual_review": "Prior phase-4 attempt7 full-page review retained in pdf-review.md; this automated run does not claim a new human visual review.",
        "conversational_trials": "CLI language projections here; actual conversations in language-review.md and phase5 forward-test.md.",
    }
    path = Path(path)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    with path.with_suffix(".md").open("x", encoding="utf-8") as stream:
        stream.write(
            "# Synthetic acceptance report\n\nOverall: " + document["overall"] + "\n\n"
        )
        for row in rows:
            stream.write(
                f"## {row['number']} — {row['test']}: {row['status']}\n\n```json\n"
            )
            stream.write(json.dumps(row, ensure_ascii=False, indent=2) + "\n```\n\n")
        stream.write(
            document["visual_review"]
            + "\n\n"
            + document["conversational_trials"]
            + "\n"
        )
    print("Nine-case acceptance report: " + document["overall"])
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args, remaining = parser.parse_known_args()
    if args.report:
        if remaining:
            parser.error("unexpected arguments with --report")
        raise SystemExit(report(args.report))
    unittest.main(argv=[sys.argv[0], *remaining], failfast=True)
