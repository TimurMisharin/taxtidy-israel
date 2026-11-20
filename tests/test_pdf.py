"""Real PDF/cryptographic/OCR operations, content review and failure invariants."""

import hashlib
import importlib
import io
import json
import os
import pty
import secrets
import select
import shutil
import stat
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from PIL import Image, ImageFont
from pypdf import PdfReader, PdfWriter

from tests.make_pdf_fixtures import (
    make,
    mismatching_worker,
    ocr_timeout_worker,
    stalled_worker,
    unexpected_failure_worker,
)
from tests.support import ROOT, SCRIPTS, case, cli, temporary

pdf_tools = importlib.import_module("pdf_tools")

TESSERACT = "/opt/homebrew/bin/tesseract"
TESSDATA = str(ROOT / ".runtime/tessdata")


def process(root, path, password=None, **options):
    return pdf_tools.process(
        root,
        str(path),
        "fictional-taxpayer",
        2025,
        "annual-employer-certificate",
        authorized=True,
        tesseract=TESSERACT,
        tessdata=TESSDATA,
        password_provider=lambda: password,
        **options,
    )


def review_batch(root, report, recipient="unconfirmed"):
    state = case.load(root)
    record = next(
        r for r in state["attachments"] if r["document_id"] == report["document_id"]
    )
    fields = []
    for name, value in (
        ("wages", "80000"),
        ("withholding", "8000"),
        ("adjustment", "-450"),
        ("empty", None),
    ):
        money = {
            "value_state": "blank" if value is None else "known",
            "currency": "ILS",
            "tax_year": 2025,
        }
        if value is not None:
            money["amount"] = value
        fields.append({"page": 1, "field": name, "value": money})
    return {
        "case_id": state["case_id"],
        "expected_revision": state["revision"],
        "document_id": record["document_id"],
        "report_sha256": record["report_sha256"],
        "review": {
            "reviewer": "synthetic-manual-reviewer",
            "reviewed_at": "2026-11-20",
            "owner": "fictional-taxpayer",
            "tax_year": 2025,
            "purpose": "annual-employer-certificate",
            "content_matches": True,
            "pages_visual_checked": [1],
            "fields": fields,
            "recipient_version": recipient,
        },
    }


def exercise_acceptance(test, parent):
    password = secrets.token_urlsafe(24)
    source = Path(parent) / "fixtures"
    signature = make(source, password)
    root = Path(parent) / "case"
    case.initialize(root, "fictional-taxpayer", [2025], synthetic=True)
    hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("*.pdf")
    }
    wrong = process(
        root, source / "protected.pdf", "incorrect-" + secrets.token_urlsafe(12)
    )["documents"][0]
    test.assertEqual(wrong["reason"], "incorrect_pdf_password")
    test.assertFalse(wrong["attachment_ready"])
    test.assertFalse(
        (root / "documents" / wrong["document_id"] / "working.pdf").exists()
    )
    correct = process(root, source / "protected.pdf", password)["documents"][0]
    test.assertEqual(correct["status"], "needs_review")
    working = root / "documents" / correct["document_id"] / "working.pdf"
    test.assertFalse(PdfReader(working).is_encrypted)
    test.assertIn("8000", PdfReader(working).pages[0].extract_text())
    test.assertFalse(correct["attachment_ready"])
    confirmed = case.review_document(root, review_batch(root, correct))["document"]
    test.assertTrue(confirmed["attachment_ready"])
    signed = process(root, source / "signed.pdf")["documents"][0]
    test.assertEqual(signed["signature_count"], 1)
    test.assertEqual(signed["signature_validation"], "present_unvalidated")
    test.assertIsNone(signed["working_sha256"])
    test.assertFalse(signed["attachment_ready"])
    test.assertTrue(signature["signature_valid"])
    scan = process(root, source / "hebrew-scan.pdf")["documents"][0]
    test.assertEqual(scan["status"], "needs_review", scan)
    test.assertEqual(scan["copy_kind"], "visual_ocr_copy")
    text = scan["pages"][0]["working_text"]
    for value in ("80000", "8000", "450"):
        test.assertIn(value, text)
    test.assertTrue(any("א" <= c <= "ת" for c in text))
    test.assertFalse(scan["attachment_ready"])
    test.assertEqual(case.load(root)["observations"], [])
    for name, before in hashes.items():
        test.assertEqual(
            hashlib.sha256((source / name).read_bytes()).hexdigest(), before
        )
    for path in root.rglob("*"):
        if path.is_file():
            test.assertNotIn(password.encode(), path.read_bytes())
            test.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        else:
            test.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
    public = json.loads(cli("summary", "--case-root", root).stdout)
    test.assertEqual(public["years"][0]["filing"]["state"], "unverified")
    return {
        "root": root,
        "signature": signature,
        "wrong": wrong,
        "correct": correct,
        "signed": signed,
        "scan": scan,
        "source_hashes": hashes,
    }


class PDFTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = temporary()
        cls.parent = Path(cls.workspace.name)
        cls.password = secrets.token_urlsafe(24)
        cls.source = cls.parent / "fixtures"
        cls.signature = make(cls.source, cls.password)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def new_case(self, parent):
        root = Path(parent) / "case"
        case.initialize(root, "fictional-taxpayer", [2025], synthetic=True)
        return root

    def test_acceptance_document_chain(self):
        with temporary() as parent:
            exercise_acceptance(self, parent)

    def test_hebrew_fixture_is_image_only_and_preserves_blank_cell(self):
        with pymupdf.open(self.source / "hebrew-scan.pdf") as doc:
            self.assertEqual(len(doc), 1)
            self.assertEqual(doc[0].get_text().strip(), "")
            self.assertEqual(len(doc[0].get_images()), 1)
            pix = doc[0].get_pixmap(dpi=200, colorspace=pymupdf.csRGB, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            self.assertEqual(
                image.crop((175, 1170, 665, 1270)).getextrema(), ((255, 255),) * 3
            )
            self.assertNotEqual(
                image.crop((175, 690, 665, 790)).getextrema(), ((255, 255),) * 3
            )

    def test_fixture_rejects_missing_numeric_glyphs(self):
        with temporary() as parent:
            font = ImageFont.truetype(
                io.BytesIO((ROOT / "tests/resources/hebrew-font.ttf").read_bytes()), 45
            )
            with (
                patch(
                    "tests.make_pdf_fixtures.ImageFont.load_default", return_value=font
                ),
                self.assertRaisesRegex(AssertionError, "numeric font lacks"),
            ):
                make(Path(parent), self.password)
            self.assertFalse((Path(parent) / "hebrew-scan.pdf").exists())

    def test_signature_review_and_empty_field(self):
        with temporary() as parent:
            root = self.new_case(parent)
            empty = process(root, self.source / "empty-signature.pdf")["documents"][0]
            self.assertEqual(empty["signature_count"], 0)
            signed = process(root, self.source / "signed.pdf")["documents"][0]
            wrong = case.review_document(root, review_batch(root, signed, "working"))[
                "document"
            ]
            self.assertFalse(wrong["attachment_ready"])
            accepted = case.review_document(
                root, review_batch(root, wrong, "original")
            )["document"]
            self.assertTrue(accepted["attachment_ready"])
            converted = process(root, self.source / "signed.pdf", convert_signed=True)[
                "documents"
            ][0]
            self.assertIsNotNone(converted["working_sha256"])
            self.assertEqual(converted["copy_kind"], "visual_copy")
            self.assertEqual(converted["signature_validation"], "present_unvalidated")
            self.assertFalse(converted["attachment_ready"])
            for recipient in ("unconfirmed", "original"):
                self.assertFalse(
                    case.review_document(
                        root, review_batch(root, converted, recipient)
                    )["document"]["attachment_ready"]
                )
            self.assertTrue(
                case.review_document(root, review_batch(root, converted, "working"))[
                    "document"
                ]["attachment_ready"]
            )
            summary = json.loads(cli("summary", "--case-root", root).stdout)
            shown = next(
                d
                for d in summary["years"][0]["documents"]
                if d["document_id"] == converted["document_id"]
            )
            self.assertEqual(shown["copy_kind"], "visual_copy")
            self.assertTrue(shown["attachment_ready"])
            self.assertEqual(shown["portal_acceptance"], "unobserved")
            self.assertEqual(summary["years"][0]["filing"]["state"], "unverified")

    def test_corruption_rotation_mixed_batch_and_limits(self):
        with temporary() as parent:
            root = self.new_case(parent)
            batch = Path(parent) / "batch"
            batch.mkdir(mode=0o700)
            for name in ("plain.pdf", "corrupt.pdf", "rotated.pdf"):
                shutil.copy(self.source / name, batch / name)
            output = process(root, batch)
            self.assertFalse(output["ok"])
            self.assertEqual(
                sum(r["status"] == "failed" for r in output["documents"]), 1
            )
            rotated = next(
                r for r in output["documents"] if r["display_filename"] == "rotated.pdf"
            )
            self.assertEqual(rotated["pages"][0]["rotation"], 90)
            self.assertEqual(rotated["pages"][0]["working_rotation"], 90)
            for name, reason in (
                ("too-many-pages.pdf", "pdf_page_limit"),
                ("too-many-pixels.pdf", "pdf_pixel_limit"),
            ):
                result = process(root, self.source / name)["documents"][0]
                self.assertEqual(result["reason"], reason)
                self.assertFalse(result["attachment_ready"])
            big = Path(parent) / "big.pdf"
            with big.open("wb") as f:
                f.truncate(pdf_tools.MAX_FILE + 1)
            self.assertEqual(
                process(root, big)["documents"][0]["reason"], "pdf_size_limit"
            )
            for i in range(101):
                (batch / f"{i}.pdf").write_bytes(b"%PDF")
            with self.assertRaises(pdf_tools.case.CaseError) as caught:
                process(root, batch)
            self.assertEqual(caught.exception.code, "pdf_batch_count_limit")
            for p in batch.iterdir():
                p.unlink()
            for i in range(11):
                with (batch / f"{i}.pdf").open("wb") as f:
                    f.truncate(49 * 1024 * 1024)
            with self.assertRaises(pdf_tools.case.CaseError) as caught:
                process(root, batch)
            self.assertEqual(caught.exception.code, "pdf_batch_size_limit")

    def test_lossless_comparison_preserves_cropbox_coordinates(self):
        with pymupdf.open() as source, pymupdf.open() as candidate:
            original = source.new_page(width=300, height=300)
            copy = candidate.new_page(width=300, height=300)
            original.set_cropbox(pymupdf.Rect(0, 0, 200, 200))
            copy.set_cropbox(original.cropbox)
            pdf_tools.compare_page(original, copy, False)
            copy.set_cropbox(pymupdf.Rect(50, 50, 250, 250))
            self.assertEqual(original.rect, copy.rect)
            self.assertEqual(original.mediabox, copy.mediabox)
            self.assertEqual(original.rotation, copy.rotation)
            self.assertEqual(original.get_text(), copy.get_text())
            self.assertEqual(
                pdf_tools.render(original, 150).samples,
                pdf_tools.render(copy, 150).samples,
            )
            for first, second in ((original, copy), (copy, original)):
                with self.assertRaises(pdf_tools.case.CaseError) as caught:
                    pdf_tools.compare_page(first, second, False)
                self.assertEqual(caught.exception.code, "pdf_comparison_failed")

    def test_unreadable_file_does_not_abort_batch(self):
        with temporary() as parent:
            root = self.new_case(parent)
            batch = Path(parent) / "batch"
            batch.mkdir(mode=0o700)
            unreadable = batch / "a-unreadable.pdf"
            good = batch / "b-good.pdf"
            data = (self.source / "plain.pdf").read_bytes()
            unreadable.write_bytes(data)
            good.write_bytes(data)
            good.chmod(0o600)
            unreadable.chmod(0)
            try:
                result = cli(
                    "pdf",
                    "--case-root",
                    root,
                    "--input",
                    batch,
                    "--owner",
                    "fictional-taxpayer",
                    "--tax-year",
                    "2025",
                    "--purpose",
                    "annual-employer-certificate",
                    "--authorized",
                )
            finally:
                unreadable.chmod(0o600)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stderr, "")
            output = json.loads(result.stdout)
            self.assertFalse(output["ok"])
            failed, passed = output["documents"]
            self.assertEqual(failed["display_filename"], unreadable.name)
            self.assertEqual(failed["reason"], "local_io_error")
            self.assertFalse(failed["attachment_ready"])
            self.assertEqual(passed["display_filename"], good.name)
            self.assertEqual(passed["status"], "needs_review")
            self.assertTrue(passed["structural_checks_passed"])
            state = case.load(root)
            self.assertEqual(len(state["attachments"]), 1)
            self.assertEqual(
                state["attachments"][0]["document_id"], passed["document_id"]
            )
            self.assertEqual(unreadable.read_bytes(), data)
            self.assertEqual(good.read_bytes(), data)

    def test_encryption_is_distinct_from_password_prompt(self):
        with temporary() as parent:
            root = self.new_case(parent)
            source = Path(parent) / "owner-protected.pdf"
            owner_password = secrets.token_urlsafe(24)
            writer = PdfWriter(clone_from=PdfReader(self.source / "plain.pdf"))
            writer.encrypt("", owner_password=owner_password, algorithm="AES-256")
            with source.open("wb") as stream:
                writer.write(stream)
            source.chmod(0o600)
            before = source.read_bytes()
            self.assertTrue(PdfReader(source).is_encrypted)
            with pymupdf.open(source) as doc:
                self.assertFalse(doc.needs_pass)
            report = pdf_tools.process(
                root,
                str(source),
                "fictional-taxpayer",
                2025,
                "annual-employer-certificate",
                authorized=True,
                password_provider=lambda: self.fail("Unexpected password request"),
            )["documents"][0]
            self.assertTrue(report["encrypted"])
            self.assertEqual(report["status"], "needs_review")
            self.assertFalse(report["attachment_ready"])
            copy = root / "documents" / report["document_id"] / "working.pdf"
            self.assertFalse(PdfReader(copy).is_encrypted)
            self.assertEqual(source.read_bytes(), before)
            plain = process(root, self.source / "plain.pdf")["documents"][0]
            self.assertFalse(plain["encrypted"])
            for path in root.rglob("*"):
                if path.is_file():
                    self.assertNotIn(owner_password.encode(), path.read_bytes())

    def test_actual_comparison_and_worker_timeouts(self):
        for worker, name, reason, options in (
            (mismatching_worker, "plain.pdf", "pdf_comparison_failed", {}),
            (
                stalled_worker,
                "plain.pdf",
                "pdf_document_timeout",
                {"DOCUMENT_SECONDS": 0.5},
            ),
        ):
            with self.subTest(reason=reason), temporary() as parent:
                root = self.new_case(parent)
                with (
                    patch.object(pdf_tools, "_worker", worker),
                    patch.object(
                        pdf_tools,
                        "DOCUMENT_SECONDS",
                        options.get("DOCUMENT_SECONDS", pdf_tools.DOCUMENT_SECONDS),
                    ),
                ):
                    report = process(root, self.source / name)["documents"][0]
                self.assertEqual(report["reason"], reason)
                self.assertFalse(
                    (
                        root / "documents" / report["document_id"] / "working.pdf"
                    ).exists()
                )
        with temporary() as parent:
            root = self.new_case(parent)
            script = Path(parent) / "slow-ocr"
            script.write_text("#!/bin/sh\nsleep 5\n")
            script.chmod(0o700)
            with patch.object(pdf_tools, "_worker", ocr_timeout_worker):
                report = pdf_tools.process(
                    root,
                    str(self.source / "hebrew-scan.pdf"),
                    "fictional-taxpayer",
                    2025,
                    "annual-employer-certificate",
                    authorized=True,
                    tesseract=str(script),
                    tessdata=TESSDATA,
                )["documents"][0]
            self.assertEqual(report["reason"], "pdf_ocr_timeout")

    def test_ocr_zero_exit_without_output_fails_closed(self):
        with temporary() as parent:
            root = self.new_case(parent)
            executable = Path(parent) / "no-output-ocr"
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o700)
            source = self.source / "hebrew-scan.pdf"
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            result = pdf_tools.process(
                root,
                str(source),
                "fictional-taxpayer",
                2025,
                "annual-employer-certificate",
                authorized=True,
                tesseract=str(executable),
                tessdata=TESSDATA,
            )
            report = result["documents"][0]
            self.assertFalse(result["ok"])
            self.assertEqual(report["reason"], "pdf_ocr_unavailable")
            self.assertFalse(report["attachment_ready"])
            self.assertFalse(
                (root / "documents" / report["document_id"] / "working.pdf").exists()
            )
            self.assertEqual(before, hashlib.sha256(source.read_bytes()).hexdigest())

    def test_unexpected_worker_failure_is_private(self):
        with temporary() as parent:
            root = self.new_case(parent)
            canary = secrets.token_urlsafe(24)
            options = {"canary": canary}
            with patch.object(pdf_tools, "_worker", unexpected_failure_worker):
                report = pdf_tools.process_one(
                    root,
                    (self.source / "plain.pdf").read_bytes(),
                    "plain.pdf",
                    "fictional-taxpayer",
                    2025,
                    "annual-employer-certificate",
                    options,
                )
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["reason"], "pdf_worker_failed")
            self.assertFalse(report["attachment_ready"])
            folder = root / "documents" / report["document_id"]
            self.assertEqual(
                {p.name for p in folder.iterdir()}, {"original.pdf", "report.json"}
            )
            for p in root.rglob("*"):
                if p.is_file():
                    self.assertNotIn(canary.encode(), p.read_bytes())

    def test_review_guards_tampering_and_atomic_failure(self):
        with temporary() as parent:
            root = self.new_case(parent)
            report = process(root, self.source / "plain.pdf")["documents"][0]
            before = (root / "checkpoint.json").read_bytes()
            bad = review_batch(root, report)
            bad["review"]["owner"] = "someone-else"
            with self.assertRaises(case.CaseError):
                case.review_document(root, bad)
            self.assertEqual(before, (root / "checkpoint.json").read_bytes())
            review = review_batch(root, report)
            review["review"]["pages_visual_checked"] = []
            review["review"]["fields"] = []
            self.assertFalse(
                case.review_document(root, review)["document"]["attachment_ready"]
            )
            review = review_batch(root, report)
            report_path = root / "documents" / report["document_id"] / "report.json"
            old = report_path.read_bytes()
            atomic = case.atomic_text

            def fail(fd, name, content):
                if name == "checkpoint.json":
                    raise OSError("synthetic write failure")
                return atomic(fd, name, content)

            with patch.object(case, "atomic_text", fail), self.assertRaises(OSError):
                case.review_document(root, review)
            self.assertEqual(old, report_path.read_bytes())
            case.review_document(root, review)
            working = root / "documents" / report["document_id"] / "working.pdf"
            working.write_bytes(b"tampered")
            public = json.loads(cli("summary", "--case-root", root).stdout)
            self.assertFalse(public["years"][0]["documents"][0]["attachment_ready"])
            self.assertEqual(
                public["years"][0]["documents"][0]["status"], "document_unverifiable"
            )

    def test_paths_authorization_and_concealed_cli(self):
        with temporary() as parent:
            root = self.new_case(parent)
            linked = Path(parent) / "link.pdf"
            linked.symlink_to(self.source / "plain.pdf")
            with self.assertRaises(pdf_tools.case.CaseError):
                process(root, linked)
            with self.assertRaises(pdf_tools.case.CaseError):
                pdf_tools.process(
                    root,
                    str(self.source / "plain.pdf"),
                    "fictional-taxpayer",
                    2025,
                    "test",
                )
            args = [
                sys.executable,
                str(SCRIPTS / "taxtidy.py"),
                "pdf",
                "--case-root",
                str(root),
                "--input",
                str(self.source / "protected.pdf"),
                "--owner",
                "fictional-taxpayer",
                "--tax-year",
                "2025",
                "--purpose",
                "annual-employer-certificate",
                "--authorized",
            ]
            noninteractive = subprocess.run(
                args, input="", text=True, capture_output=True, check=False
            )
            self.assertEqual(noninteractive.returncode, 1)
            self.assertIn("concealed_input_unavailable", noninteractive.stdout)
            master, slave = pty.openpty()
            child = subprocess.Popen(
                args, stdin=slave, stdout=slave, stderr=slave, start_new_session=True
            )
            os.close(slave)
            output = bytearray()
            sent = False
            deadline = time.monotonic() + 30
            try:
                while time.monotonic() < deadline:
                    if select.select([master], [], [], 0.1)[0]:
                        try:
                            data = os.read(master, 65536)
                        except OSError:
                            break
                        if not data:
                            break
                        output.extend(data)
                        if not sent and b"concealed input):" in output:
                            os.write(master, self.password.encode() + b"\n")
                            sent = True
                    if (
                        child.poll() is not None
                        and not select.select([master], [], [], 0)[0]
                    ):
                        break
                self.assertTrue(sent)
                self.assertEqual(
                    child.wait(timeout=5), 0, output.decode(errors="replace")
                )
                self.assertNotIn(self.password.encode(), output)
                self.assertNotIn(self.password, json.dumps(args))
                for p in root.rglob("*"):
                    if p.is_file():
                        self.assertNotIn(self.password.encode(), p.read_bytes())
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, 9)
                    child.wait()
                os.close(master)
            # Explicit argv secrets are refused without echoing argparse's input.
            rejected = subprocess.run(
                args + ["--password", self.password], capture_output=True, check=False
            )
            self.assertEqual(rejected.returncode, 2)
            self.assertNotIn(self.password.encode(), rejected.stderr + rejected.stdout)


if __name__ == "__main__":
    unittest.main()
