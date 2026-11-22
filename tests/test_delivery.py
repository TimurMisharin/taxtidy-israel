"""Package checks exercise invalid links, schema, templates and symlinks."""

import importlib.util
import io
import json
import shutil
import stat
import subprocess
import sys
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter

from tests.support import ROOT, temporary

spec = importlib.util.spec_from_file_location(
    "package_skill", ROOT / "tools/package_skill.py"
)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class DeliveryTests(unittest.TestCase):
    def test_public_archive_rejects_encrypted_pdfs_without_retaining_them(self):
        with temporary() as parent:
            parent = Path(parent)
            archive = parent / "openai.zip"
            package.build_public(ROOT / "taxtidy-israel", archive)
            with zipfile.ZipFile(archive) as built:
                self.assertNotIn(
                    "taxtidy-israel/" + package.PASSWORD_HELPER, built.namelist()
                )
                built.extractall(parent)
            script = parent / "taxtidy-israel/skills/taxtidy-israel/scripts/taxtidy.py"
            root = parent / "case"
            initialized = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "init",
                    "--case-root",
                    str(root),
                    "--taxpayer-id",
                    "person-a",
                    "--years",
                    "2025",
                    "--synthetic",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            revision = json.loads(initialized.stdout)["revision"]
            source = parent / "fixture.pdf"
            for password in ("fixture-only", ""):
                with self.subTest(empty_password=not password):
                    writer = PdfWriter()
                    writer.add_blank_page(width=72, height=72)
                    writer.encrypt(password)
                    writer.write(source)
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(script),
                            "pdf",
                            "--case-root",
                            str(root),
                            "--input",
                            str(source),
                            "--owner",
                            "person-a",
                            "--tax-year",
                            "2025",
                            "--purpose",
                            "synthetic-test",
                            "--authorized",
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    response = json.loads(result.stdout)
                    self.assertEqual(response["revision"], revision)
                    self.assertEqual(
                        response["documents"][0]["reason"], "encrypted_pdf_unsupported"
                    )
                    self.assertEqual(list((root / "documents").iterdir()), [])

    def test_deterministic_archive_and_unsafe_entries(self):
        with temporary() as parent:
            parent = Path(parent)
            first, second = parent / "one.zip", parent / "two.zip"
            self.assertEqual(
                package.build(ROOT / "taxtidy-israel", first),
                package.build(ROOT / "taxtidy-israel", second),
            )
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                members = [(info, archive.read(info)) for info in archive.infolist()]
                self.assertEqual(len(members), len(package.FILES))
                self.assertFalse(
                    any(".DS_Store" in Path(info.filename).parts for info, _ in members)
                )
            for variant in (
                "traversal",
                "extra",
                "duplicate",
                "symlink",
                "missing",
                "secret",
                "machine_path",
            ):
                with self.subTest(variant=variant):
                    bad = parent / (variant + ".zip")
                    with zipfile.ZipFile(bad, "w") as archive:
                        for info, data in members:
                            if info.filename.endswith("SETUP.md"):
                                if variant == "missing":
                                    continue
                                if variant == "symlink":
                                    info = zipfile.ZipInfo(info.filename)
                                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                                if variant == "secret":
                                    data += b"\n-----BEGIN PRIVATE KEY-----"
                                if variant == "machine_path":
                                    data += b"\n/Users/example/private-case"
                            archive.writestr(info, data)
                        if variant in {"traversal", "extra", "duplicate"}:
                            name = {
                                "traversal": "../escaped",
                                "extra": "taxtidy-israel/case.json",
                                "duplicate": members[0][0].filename,
                            }[variant]
                            archive.writestr(name, b"private")
                    with self.assertRaises(ValueError):
                        package.check_archive(bad)

    def test_private_source_and_missing_handoff_rejected(self):
        for name in ("private-case.json", ".DS_Store", ".env", "missing-setup"):
            with self.subTest(name=name), temporary() as parent:
                root = Path(parent) / "package"
                shutil.copytree(
                    ROOT / "taxtidy-israel",
                    root,
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
                if name == "missing-setup":
                    (root / "SETUP.md").unlink()
                else:
                    (root / name).write_text("unrelated")
                with self.assertRaises(ValueError):
                    package.check(root)

    def test_acceptance_report_never_promotes_failure_or_missing_observations(self):
        from tests.test_acceptance import AcceptanceTests, report

        for skipped in (False, True):
            with self.subTest(skipped=skipped), temporary() as parent:

                def failed(test, skipped=skipped):
                    if skipped:
                        test.skipTest("synthetic missing dependency")
                    test.fail("synthetic injected failure")

                path = Path(parent) / "report.json"
                with (
                    patch.object(AcceptanceTests, "test_01_wage_overlap", failed),
                    redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(report(path), 1)
                data = json.loads(path.read_text())
                self.assertEqual(data["overall"], "FAIL")
                self.assertEqual(len(data["cases"]), 9)
                self.assertEqual(data["cases"][0]["status"], "FAIL")
                self.assertTrue(
                    all(row["status"] == "NOT_RUN" for row in data["cases"][1:])
                )
                self.assertTrue(path.with_suffix(".md").is_file())
                self.assertNotIn("PASS", path.read_text())

    def test_non_object_template_rejected(self):
        with temporary() as parent:
            root = Path(parent) / "package"
            shutil.copytree(
                ROOT / "taxtidy-israel",
                root,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            (root / "skills/taxtidy-israel/assets/templates/evidence.json").write_text(
                "[]\n"
            )
            with self.assertRaises(TypeError):
                package.check(root)
            with patch("sys.argv", ["package_skill.py", "check", "--root", str(root)]):
                self.assertEqual(package.main(), 1)

    def test_package_and_unsafe_variants(self):
        package.check(ROOT / "taxtidy-israel")
        for bad in (
            "schema",
            "missing_install_notice",
            "missing_license_notice",
            "symlink",
            "missing",
            "escape",
            "template",
            "capability",
            "calculator",
            "rules",
            "rule_year",
            "heading",
            "unverified_rule",
            "workflow_reference",
            "pdf_reference",
            "review_template_missing",
            "review_template_malformed",
        ):
            with self.subTest(bad=bad), temporary() as parent:
                root = Path(parent) / "package"
                shutil.copytree(
                    ROOT / "taxtidy-israel",
                    root,
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
                skill = root / "skills/taxtidy-israel"
                if bad in {"schema", "missing_install_notice"}:
                    path = root / "plugin.json"
                    manifest = json.loads(path.read_text())
                    if bad == "schema":
                        manifest["$schema"] = "https://invalid.example/schema"
                    else:
                        del manifest["extensions"]["com.openai"]["interface"][
                            "longDescription"
                        ]
                    path.write_text(json.dumps(manifest))
                elif bad == "missing_license_notice":
                    (root / "LICENSE-NOTICE.md").unlink()
                elif bad == "symlink":
                    (skill / "references/external.md").symlink_to(
                        ROOT / "tools/package_skill.py"
                    )
                elif bad in {"missing", "escape"}:
                    with (skill / "SKILL.md").open("a") as stream:
                        stream.write(
                            "\n[bad]("
                            + (
                                "missing.md"
                                if bad == "missing"
                                else "../../../../outside.md"
                            )
                            + ")\n"
                        )
                elif bad == "template":
                    path = skill / "assets/templates/checkpoint.json"
                    template = json.loads(path.read_text())
                    template["case_id"] = "real-person-like-data"
                    path.write_text(json.dumps(template))
                elif bad == "capability":
                    (skill / "scripts/pdf_tools.py").unlink()
                elif bad == "pdf_reference":
                    (skill / "references/pdf-workflow.md").unlink()
                elif bad == "review_template_missing":
                    (skill / "assets/templates/document-review.json").unlink()
                elif bad == "review_template_malformed":
                    (skill / "assets/templates/document-review.json").write_text("[]")
                elif bad == "calculator":
                    (skill / "scripts/calculate.py").unlink()
                elif bad == "rules":
                    (skill / "assets/rules/2025.json").unlink()
                elif bad == "workflow_reference":
                    (skill / "references/portal-and-routing.md").unlink()
                elif bad == "heading":
                    path = skill / "SKILL.md"
                    path.write_text(
                        path.read_text().replace(
                            "## Supported local workflow",
                            "## Current capability: phase 3",
                        )
                    )
                else:
                    path = skill / "assets/rules/2025.json"
                    rules = json.loads(path.read_text())
                    if bad == "rule_year":
                        rules["tax_year"] = 2024
                    else:
                        rules["rules"]["credit_point"]["verified"] = False
                    path.write_text(json.dumps(rules))
                with self.assertRaises(ValueError):
                    package.check(root)


if __name__ == "__main__":
    unittest.main()
