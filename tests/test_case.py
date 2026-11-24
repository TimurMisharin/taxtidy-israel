"""Phase-1 invariants with synthetic source text and private cases."""

import calendar
import copy
import json
import os
import shutil
import stat
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support import (
    SCRIPTS,
    baseline,
    batch,
    case,
    cli,
    fixture,
    store_probe,
    temporary,
    wage,
)


class CaseTests(unittest.TestCase):
    def test_freshness_projection(self):
        vector = fixture()["canonical_vector"]
        self.assertEqual(case.canonical(vector["value"]), vector["utf8"].encode())
        self.assertEqual(case.digest(vector["value"]), vector["sha256"])
        with temporary() as parent:
            root, state = baseline(parent)

            def fingerprint(s):
                return case.input_digest(
                    s, s["taxpayer_id"], 2025, "0" * 64, case.ENGINE_VERSION
                )

            expected = fingerprint(state)
            alternate = copy.deepcopy(state)
            alternate["observations"].reverse()
            alternate["economic_items"].reverse()
            # Reconcile sorts derived records; equivalent import order is invariant.
            case.reconcile(alternate)
            self.assertEqual(expected, fingerprint(alternate))
            alternate["preferred_language"] = "ru"
            alternate["revision"] += 1
            alternate["events"] = [{"display_only": "draft saved"}]
            self.assertEqual(expected, fingerprint(alternate))
            replay = batch(state, state["observations"])
            for o in replay["observations"]:
                o["amount"]["amount"] += ".00"
            repeated = case.import_evidence(root, replay)
            self.assertEqual(state["revision"], repeated["revision"])
            self.assertEqual(expected, fingerprint(repeated))
            for field in ("amount", "withholding", "classification", "provenance"):
                changed = copy.deepcopy(state)
                o = changed["observations"][0]
                if field in {"amount", "withholding"}:
                    o[field]["amount"] = "12345"
                elif field == "classification":
                    o[field] = "unresolved"
                else:
                    o[field] = "user_statement"
                case.reconcile(changed)
                self.assertNotEqual(expected, fingerprint(changed), field)
            for status in ("unknown", "blank"):
                changed = copy.deepcopy(state)
                changed["observations"][0]["amount"] = {
                    "value_state": status,
                    "currency": "ILS",
                    "tax_year": 2025,
                }
                case.reconcile(changed)
                self.assertNotEqual(expected, fingerprint(changed))
            changed = copy.deepcopy(state)
            changed["eligibility"] = [
                {
                    "owner": state["taxpayer_id"],
                    "tax_year": 2025,
                    "ownership": "unresolved",
                }
            ]
            self.assertNotEqual(expected, fingerprint(changed))
            self.assertNotEqual(
                expected,
                case.input_digest(
                    state, state["taxpayer_id"], 2025, "1" * 64, case.ENGINE_VERSION
                ),
            )
            self.assertNotEqual(
                expected,
                case.input_digest(
                    state, state["taxpayer_id"], 2025, "0" * 64, "changed-engine"
                ),
            )

    def test_conflicting_106_invalidates(self):
        for variant in ("conflicting_106", "withholding_conflict"):
            with self.subTest(variant=variant), temporary() as parent:
                root, state = baseline(parent)
                state = store_probe(root, state)
                old_digest = next(
                    r["input_digest"] for r in state["results"] if r["tax_year"] == 2025
                )
                state = case.import_evidence(root, batch(state, [fixture()[variant]]))
                reopened = case.load(root)
                self.assertEqual(state, reopened)
                self.assertTrue(state["conflicts"])
                a = next(
                    i
                    for i in state["economic_items"]
                    if i["issuer"] == "fictional-employer-a"
                )
                self.assertEqual(a["amount"]["amount"], "80000")
                self.assertEqual(len(a["observations"]), 2)
                self.assertEqual(len(state["economic_items"]), 2)
                req = next(
                    r for r in state["requirements"] if r["economic_id"] == a["id"]
                )
                self.assertEqual(req["status"], "resolved")
                self.assertEqual(req["history"][0]["status"], "missing")
                self.assertEqual(req["filing_acceptability"], "unverified")
                statuses = {r["tax_year"]: r["status"] for r in state["results"]}
                self.assertEqual(statuses, {2024: "current", 2025: "stale"})
                self.assertNotEqual(
                    old_digest,
                    case.input_digest(
                        state, state["taxpayer_id"], 2025, "0" * 64, case.ENGINE_VERSION
                    ),
                )
                self.assertIsNone(
                    next(y for y in case.wage_summary(state) if y["tax_year"] == 2025)[
                        "wage_base"
                    ]
                )

    def test_freshness_atomic_failure(self):
        for failure in (
            "revision",
            "checkpoint_replace",
            "summary_clear",
            "crash_after_summary",
        ):
            with self.subTest(failure=failure), temporary() as parent:
                root, state = baseline(parent)
                state = store_probe(root, state)
                with case.locked(root) as fd:
                    case.atomic_text(
                        fd,
                        "summary.md",
                        "SYNTHETIC historical estimate marker; must clear before conflict commit",
                    )
                before = (root / "checkpoint.json").read_bytes()
                incoming = batch(state, [fixture()["conflicting_106"]])
                original_replace = case.os.replace
                original_atomic = case.atomic_text

                class Crash(BaseException):
                    pass

                def replace(
                    src,
                    dst,
                    failure=failure,
                    original_replace=original_replace,
                    **kwargs,
                ):
                    if dst == "checkpoint.json":
                        if failure == "crash_after_summary":
                            raise Crash()
                        raise OSError("injected checkpoint failure")
                    return original_replace(src, dst, **kwargs)

                def atomic(fd, name, content, original_atomic=original_atomic):
                    if name == "summary.md":
                        raise OSError("injected summary-clear failure")
                    return original_atomic(fd, name, content)

                if failure == "revision":
                    incoming["expected_revision"] -= 1
                    with self.assertRaises(case.CaseError) as err:
                        case.import_evidence(root, incoming)
                    self.assertEqual(err.exception.code, "revision_conflict")
                elif failure == "summary_clear":
                    with (
                        patch.object(case, "atomic_text", side_effect=atomic),
                        self.assertRaises(OSError),
                    ):
                        case.import_evidence(root, incoming)
                else:
                    with (
                        patch.object(case.os, "replace", side_effect=replace),
                        self.assertRaises(
                            Crash if failure == "crash_after_summary" else OSError
                        ),
                    ):
                        case.import_evidence(root, incoming)
                    self.assertEqual(
                        (root / "summary.md").read_text(),
                        "Recalculation required. Previous estimates are unavailable.\n",
                    )
                self.assertEqual((root / "checkpoint.json").read_bytes(), before)
                self.assertEqual(case.load(root), state)
                self.assertFalse(list(root.glob(".checkpoint.*.tmp")))

    def test_storage_and_isolation(self):
        with temporary() as parent:
            root, state = baseline(parent)
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            self.assertEqual(
                stat.S_IMODE((root / "checkpoint.json").stat().st_mode), 0o600
            )
            before = (root / "checkpoint.json").read_bytes()
            with self.assertRaises(FileExistsError):
                case.initialize(root, "other", [2025], synthetic=True)
            wrong = batch(state, fixture()["corroborating"])
            wrong["case_id"] = "another-case"
            with self.assertRaises(case.CaseError):
                case.import_evidence(root, wrong)
            wrong = batch(state, fixture()["corroborating"])
            wrong["observations"][0]["owner"] = "another-person"
            with self.assertRaises(case.CaseError):
                case.import_evidence(root, wrong)
            wrong = batch(state, fixture()["corroborating"])
            wrong["observations"][0]["tax_year"] = 2023
            with self.assertRaises(case.CaseError):
                case.import_evidence(root, wrong)
            self.assertEqual((root / "checkpoint.json").read_bytes(), before)
            link = Path(parent) / "alias"
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaises(case.CaseError):
                case.load(link)
            hardlink = Path(parent) / "linked-checkpoint"
            os.link(root / "checkpoint.json", hardlink)
            with self.assertRaises(case.CaseError):
                case.load(root)
            hardlink.unlink()
            (root / "checkpoint.json").chmod(0o644)
            with self.assertRaises(case.CaseError):
                case.load(root)

    def test_source_boundaries_from_installed_cli(self):
        for layout in ("standalone", "plugin", "git-directory", "git-file", "marker"):
            with self.subTest(layout=layout), temporary() as parent:
                parent = Path(parent)
                source = parent / "install"
                wrapped = layout != "standalone"
                plugin = source if layout == "plugin" else source / "plugin"
                skill = (
                    plugin / "skills/taxtidy-israel"
                    if wrapped
                    else source / "taxtidy-israel"
                )
                shutil.copytree(
                    SCRIPTS.parent, skill, ignore=shutil.ignore_patterns("__pycache__")
                )
                protected = [skill]
                if wrapped:
                    (plugin / "plugin.json").write_text("{}")
                    protected.append(plugin)
                if layout == "git-directory":
                    (source / ".git").mkdir()
                elif layout == "git-file":
                    (source / ".git").write_text(
                        "gitdir: /fictional/git/worktrees/install\n"
                    )
                elif layout == "marker":
                    marker = source / ".docs/plans/taxtidy-israel.md"
                    marker.parent.mkdir(parents=True)
                    marker.touch()
                if layout in {"git-directory", "git-file", "marker"}:
                    protected.append(source)

                def init(target, skill=skill):
                    return subprocess.run(
                        [
                            sys.executable,
                            str(skill / "scripts/taxtidy.py"),
                            "init",
                            "--case-root",
                            str(target),
                            "--taxpayer-id",
                            "fictional-taxpayer",
                            "--years",
                            "2025",
                            "--synthetic",
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )

                neighbor = parent / "private-case"
                if not wrapped:
                    neighbor = skill.with_name("private-case")
                result = init(neighbor)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((neighbor / "checkpoint.json").is_file())
                for directory in protected:
                    with self.subTest(protected=directory.name):
                        for target in (directory, directory / "case"):
                            result = init(target)
                            self.assertEqual(result.returncode, 1, result.stdout)
                            self.assertEqual(
                                json.loads(result.stderr)["reason"],
                                "case_inside_shared_source",
                            )
                        self.assertFalse((directory / "case").exists())
                        self.assertFalse((directory / "checkpoint.json").exists())

    def test_money_and_json_boundaries(self):
        for invalid in (1.0, True, "NaN", "Infinity", "1,000", "1e3", " 1", "01"):
            with self.subTest(invalid=invalid), self.assertRaises(case.CaseError):
                case.money(
                    {
                        "value_state": "known",
                        "amount": invalid,
                        "currency": "ILS",
                        "tax_year": 2025,
                    }
                )
        for value in (
            '{"x":1,"x":2}',
            '{"x":NaN}',
            '{"x":1.5}',
            '{"password":"SYNTHETIC_CANARY"}',
        ):
            with self.assertRaises(case.CaseError):
                case.parse_json(value)
        self.assertNotEqual(
            case.money({"value_state": "unknown", "currency": "ILS", "tax_year": 2025}),
            case.money({"value_state": "blank", "currency": "ILS", "tax_year": 2025}),
        )
        self.assertEqual(
            case.money(
                {
                    "value_state": "known",
                    "amount": "-0.000",
                    "currency": "ILS",
                    "tax_year": 2025,
                }
            )["amount"],
            "0",
        )

    def test_unreviewed_ocr_and_unsupported_income(self):
        with temporary() as parent:
            root, state = baseline(parent)
            for change in (
                {
                    "review": {
                        "reviewer": "synthetic",
                        "owner_year_checked": True,
                        "fields_checked": [],
                        "method": "ocr_unreviewed",
                    }
                },
                {"kind": "foreign_income"},
            ):
                raw = copy.deepcopy(fixture()["corroborating"][0])
                raw.update(change)
                with self.assertRaises(case.CaseError):
                    case.import_evidence(root, batch(state, [raw]))

    def test_monthly_and_ytd_coverage(self):
        with temporary() as parent:
            root = Path(parent) / "case"
            state = case.initialize(root, "fictional-taxpayer", [2025], synthetic=True)
            sources = fixture()["corroborating"][:2]
            state = case.import_evidence(root, batch(state, sources))
            self.assertEqual(case.wage_summary(state)[0]["wage_base"], "80000")
        with temporary() as parent:
            root = Path(parent) / "case"
            state = case.initialize(root, "fictional-taxpayer", [2025], synthetic=True)
            monthly = copy.deepcopy(fixture()["baseline"][0])
            monthly.update(
                document_type="payslip_monthly",
                period_start="2025-01-01",
                period_end="2025-01-31",
            )
            second = copy.deepcopy(monthly)
            second.update(
                period_start="2025-02-01",
                period_end="2025-02-28",
                business_reference="monthly-Feb",
            )
            state = case.import_evidence(root, batch(state, [monthly, second, monthly]))
            self.assertEqual(case.wage_summary(state)[0]["wage_base"], "160000")
            overlap = copy.deepcopy(second)
            overlap.update(period_start="2025-01-15", business_reference="overlapping")
            state = case.import_evidence(root, batch(state, [overlap]))
            self.assertTrue(state["conflicts"])
            self.assertIsNone(case.wage_summary(state)[0]["wage_base"])

    def test_monthly_certificate_reconciliation(self):
        months = [
            wage(
                "payslip_monthly",
                f"2025-{m:02}-01",
                f"2025-{m:02}-{calendar.monthrange(2025, m)[1]}",
                "7000",
                "500",
                f"monthly-{m}",
            )
            for m in range(1, 13)
        ]
        for document_type in ("form_106", "payslip_ytd"):
            for amount, withholding, conflict in (
                ("84000", "6000", None),
                ("80000", "6000", "amount"),
                ("84000", "6100", "withholding"),
            ):
                for certificate_first in (False, True):
                    with (
                        self.subTest(
                            document_type=document_type,
                            conflict=conflict,
                            certificate_first=certificate_first,
                        ),
                        temporary() as parent,
                    ):
                        root = Path(parent) / "case"
                        state = case.initialize(
                            root, "fictional-taxpayer", [2024, 2025], synthetic=True
                        )
                        certificate = wage(
                            document_type,
                            "2025-01-01",
                            "2025-12-31",
                            amount,
                            withholding,
                            "certificate",
                        )
                        initial, incoming = (
                            ([certificate], months)
                            if certificate_first
                            else (months, [certificate])
                        )
                        state = case.import_evidence(root, batch(state, initial))
                        state = store_probe(root, state)
                        with case.locked(root) as fd:
                            case.atomic_text(fd, "summary.md", "SYNTHETIC OLD ESTIMATE")
                        state = case.import_evidence(root, batch(state, incoming))
                        self.assertEqual(case.load(root), state)
                        self.assertEqual(len(state["observations"]), 13)
                        self.assertEqual(len(state["economic_items"]), 1)
                        self.assertEqual(
                            {r["tax_year"]: r["status"] for r in state["results"]},
                            {2024: "current", 2025: "stale"},
                        )
                        self.assertNotIn(
                            "OLD ESTIMATE", (root / "summary.md").read_text()
                        )
                        public = next(
                            y for y in case.wage_summary(state) if y["tax_year"] == 2025
                        )
                        if conflict:
                            self.assertIsNone(public["wage_base"])
                            found = next(
                                c for c in state["conflicts"] if c["field"] == conflict
                            )
                            self.assertEqual(found["status"], "unresolved")
                            aggregate = next(
                                o
                                for o in found["observations"]
                                if "source_observations" in o
                            )
                            self.assertEqual(
                                set(aggregate["source_observations"]),
                                {case.digest(o) for o in months},
                            )
                            expected = (
                                {"80000", "84000"}
                                if conflict == "amount"
                                else {"6000", "6100"}
                            )
                            self.assertEqual(
                                {o["value"]["amount"] for o in found["observations"]},
                                expected,
                            )
                        else:
                            self.assertFalse(state["conflicts"])
                            self.assertEqual(public["wage_base"], "84000")
                        self.assertEqual(
                            case.import_evidence(
                                root, batch(state, months + [certificate])
                            ),
                            state,
                        )
                        self.assertEqual(case.load(root), state)

    def test_monthly_partial_coverage_is_not_an_annual_total(self):
        for periods in (
            [("2025-01-01", "2025-01-31")],
            [("2025-01-01", "2025-01-31"), ("2025-12-01", "2025-12-31")],
        ):
            with self.subTest(periods=periods), temporary() as parent:
                root = Path(parent) / "case"
                state = case.initialize(
                    root, "fictional-taxpayer", [2025], synthetic=True
                )
                sources = [
                    wage(
                        "form_106",
                        "2025-01-01",
                        "2025-12-31",
                        "84000",
                        "6000",
                        "annual",
                    )
                ] + [
                    wage("payslip_monthly", start, end, "7000", "500", f"month-{i}")
                    for i, (start, end) in enumerate(periods)
                ]
                state = case.import_evidence(root, batch(state, sources))
                self.assertFalse(state["conflicts"])
                self.assertEqual(
                    case.wage_summary(case.load(root))[0]["wage_base"], "84000"
                )

    def test_monthly_period_conflicts_with_annual(self):
        for start, end in (("2025-01-02", "2025-12-31"), ("2025-01-01", "2025-12-30")):
            with self.subTest(start=start, end=end), temporary() as parent:
                root = Path(parent) / "case"
                state = case.initialize(
                    root, "fictional-taxpayer", [2025], synthetic=True
                )
                state = case.import_evidence(
                    root,
                    batch(
                        state,
                        [
                            wage(
                                "form_106", start, end, "84000", "6000", "annual-period"
                            ),
                            wage(
                                "payslip_monthly",
                                "2025-01-01",
                                "2025-12-31",
                                "84000",
                                "6000",
                                "covered-period",
                            ),
                        ],
                    ),
                )
                self.assertTrue(state["conflicts"])
                self.assertIsNone(case.wage_summary(case.load(root))[0]["wage_base"])

    def test_gapped_monthly_employment_period_conflicts(self):
        months = [
            wage(
                "payslip_monthly", "2025-01-01", "2025-01-31", "6000", "300", "January"
            ),
            wage(
                "payslip_monthly", "2025-12-01", "2025-12-31", "6000", "300", "December"
            ),
        ]
        for document_type in ("form_106", "a99_5"):
            for start, end, fields in (
                ("2025-02-01", "2025-11-30", {"period_start", "period_end"}),
                ("2025-02-01", "2025-12-31", {"period_start"}),
                ("2025-01-01", "2025-11-30", {"period_end"}),
                ("2025-01-15", "2025-12-15", {"period_start", "period_end"}),
            ):
                for certificate_first in (False, True):
                    with (
                        self.subTest(
                            document_type=document_type,
                            start=start,
                            end=end,
                            certificate_first=certificate_first,
                        ),
                        temporary() as parent,
                    ):
                        root = Path(parent) / "case"
                        state = case.initialize(
                            root, "fictional-taxpayer", [2024, 2025], synthetic=True
                        )
                        certificate = wage(
                            document_type,
                            start,
                            end,
                            "60000",
                            "3000",
                            "employment-period",
                        )
                        initial, incoming = (
                            ([certificate], months)
                            if certificate_first
                            else (months, [certificate])
                        )
                        state = case.import_evidence(root, batch(state, initial))
                        state = store_probe(root, state)
                        previous_digest = next(
                            r["input_digest"]
                            for r in state["results"]
                            if r["tax_year"] == 2025
                        )
                        with case.locked(root) as fd:
                            case.atomic_text(fd, "summary.md", "SYNTHETIC OLD ESTIMATE")
                        state = case.import_evidence(root, batch(state, incoming))
                        state = case.load(root)
                        self.assertEqual(len(state["observations"]), 3)
                        item = state["economic_items"][0]
                        self.assertEqual(len(state["economic_items"]), 1)
                        self.assertEqual(item["amount"]["amount"], "60000")
                        self.assertEqual(item["calculation_completeness"], "conflict")
                        self.assertEqual(
                            {c["field"] for c in state["conflicts"]}, fields
                        )
                        for conflict in state["conflicts"]:
                            field = conflict["field"]
                            month = months[0 if field == "period_start" else 1]
                            self.assertEqual(conflict["status"], "unresolved")
                            self.assertEqual(
                                {
                                    o["identity"]: o["value"]
                                    for o in conflict["observations"]
                                },
                                {
                                    case.digest(certificate): certificate[field],
                                    case.digest(month): month[field],
                                },
                            )
                        self.assertEqual(
                            {r["tax_year"]: r["status"] for r in state["results"]},
                            {2024: "current", 2025: "stale"},
                        )
                        self.assertNotEqual(
                            previous_digest,
                            case.input_digest(
                                state,
                                state["taxpayer_id"],
                                2025,
                                "0" * 64,
                                case.ENGINE_VERSION,
                            ),
                        )
                        self.assertNotIn(
                            "OLD ESTIMATE", (root / "summary.md").read_text()
                        )
                        replay = Path(parent) / "reviewed.json"
                        replay.write_text(
                            json.dumps(batch(state, months + [certificate]))
                        )
                        replay.chmod(0o600)
                        output = cli(
                            "import-evidence", "--case-root", root, "--input", replay
                        )
                        self.assertEqual(output.returncode, 0, output.stderr)
                        public = next(
                            y
                            for y in json.loads(output.stdout)["years"]
                            if y["tax_year"] == 2025
                        )
                        self.assertIsNone(public["wage_base"])
                        self.assertIsNone(public["tax_estimate"])
                        self.assertEqual(case.load(root), state)

    def test_checkpoint_size_boundary_and_growth(self):
        self.assertEqual(case.MAX_CASE_BYTES, 50 * 1024 * 1024)
        for limit_delta in (0, -1):
            with self.subTest(limit_delta=limit_delta), temporary() as parent:
                root, state = baseline(parent)
                state = store_probe(root, state)
                before = (root / "checkpoint.json").read_bytes()
                incoming = batch(
                    state,
                    [
                        wage(
                            "form_106",
                            "2025-01-01",
                            "2025-12-31",
                            "82000",
                            "8000",
                            "size-case",
                        )
                    ],
                )
                candidate = case.import_evidence(root, incoming)
                encoded = (root / "checkpoint.json").read_bytes()
                self.assertGreater(len(encoded), len(encoded.decode("utf-8")))
                with case.locked(root) as fd:
                    case.atomic_text(fd, "checkpoint.json", before.decode("utf-8"))
                    case.atomic_text(fd, "summary.md", "SYNTHETIC current summary")
                summary = (root / "summary.md").read_bytes()
                with patch.object(case, "MAX_CASE_BYTES", len(encoded) + limit_delta):
                    if limit_delta:
                        with self.assertRaisesRegex(case.CaseError, "^case_too_large$"):
                            case.import_evidence(root, incoming)
                        self.assertEqual(
                            (root / "checkpoint.json").read_bytes(), before
                        )
                        self.assertEqual((root / "summary.md").read_bytes(), summary)
                        self.assertEqual(case.load(root), state)
                    else:
                        self.assertEqual(
                            case.import_evidence(root, incoming), candidate
                        )
                        self.assertEqual(case.load(root), candidate)
                        accepted = (root / "checkpoint.json").read_bytes()
                        with case.locked(root) as fd:
                            case.atomic_text(
                                fd, "summary.md", "SYNTHETIC retained summary"
                            )
                        summary = (root / "summary.md").read_bytes()
                        overflow = batch(candidate, [fixture()["withholding_conflict"]])
                        self.assertLess(
                            len(case.canonical(overflow)), case.MAX_CASE_BYTES
                        )
                        with self.assertRaisesRegex(case.CaseError, "^case_too_large$"):
                            case.import_evidence(root, overflow)
                        self.assertEqual(
                            (root / "checkpoint.json").read_bytes(), accepted
                        )
                        self.assertEqual((root / "summary.md").read_bytes(), summary)
                        self.assertEqual(case.load(root), candidate)
                        with (
                            case.locked(root) as fd,
                            self.assertRaisesRegex(case.CaseError, "^case_too_large$"),
                        ):
                            case.atomic_text(
                                fd,
                                "checkpoint.json",
                                "א" * (case.MAX_CASE_BYTES // 2 + 1),
                            )
                        self.assertEqual(
                            (root / "checkpoint.json").read_bytes(), accepted
                        )
                self.assertFalse(list(root.glob(".checkpoint.*.tmp")))

    def test_cli_boundaries(self):
        self.assertEqual(cli("--help").returncode, 0)
        bad = cli("--password", "SYNTHETIC_SECRET_CANARY")
        self.assertNotEqual(bad.returncode, 0)
        self.assertNotIn("SYNTHETIC_SECRET_CANARY", bad.stdout + bad.stderr)
        with temporary() as parent:
            root = Path(parent) / "case"
            created = cli(
                "init",
                "--case-root",
                root,
                "--taxpayer-id",
                "fictional-taxpayer",
                "--years",
                "2025",
                "--synthetic",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            state = case.load(root)
            infile = Path(parent) / "reviewed.json"
            infile.write_text(json.dumps(batch(state, fixture()["baseline"])))
            imported = cli("import-evidence", "--case-root", root, "--input", infile)
            self.assertEqual(imported.returncode, 0, imported.stderr)
            body = json.loads(imported.stdout)
            self.assertTrue(body["tax_calculation_available"])
            self.assertIsNone(body["years"][0]["tax_estimate"])
            bad = cli("import-evidence", "--case-root", root, "--input", infile)
            self.assertNotEqual(bad.returncode, 0)
            self.assertNotIn(fixture()["baseline"][0]["source"]["text"], bad.stderr)


if __name__ == "__main__":
    unittest.main()
