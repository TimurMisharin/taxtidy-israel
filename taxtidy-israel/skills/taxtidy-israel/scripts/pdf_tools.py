"""Local bounded PDF processing. No signature trust or portal acceptance is inferred."""

import hashlib
import io
import logging
import math
import multiprocessing
import os
import shutil
import signal
import stat
import subprocess
import time
import uuid
from pathlib import Path

import case
import pymupdf
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

if Path(__file__).with_name("pdf_password.py").is_file():
    from pdf_password import hidden_password
else:
    hidden_password = None

MAX_FILE = 50 * 1024 * 1024
MAX_PAGES = 100
MAX_FILES = 100
MAX_BATCH = 500 * 1024 * 1024
MAX_PIXELS = 16_000_000
OCR_SECONDS = 60
DOCUMENT_SECONDS = 120


def file_bytes(path, limit=MAX_FILE):
    path = Path(path)
    case.require(path.is_absolute() and ".." not in path.parts, "unsafe_pdf_path")
    case.require(
        not any(p.is_symlink() for p in (path, *path.parents)), "unsafe_pdf_path"
    )
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        meta = os.fstat(stream.fileno())
        case.require(stat.S_ISREG(meta.st_mode), "unsafe_pdf_path")
        case.require(meta.st_size <= limit, "pdf_size_limit")
        data = stream.read(limit + 1)
        case.require(len(data) <= limit, "pdf_size_limit")
        return data


def sha(data):
    return hashlib.sha256(data).hexdigest()


def private_write(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def signature_count(reader):
    fields = reader.get_fields() or {}
    count = 0
    for field in fields.values():
        value = field.get("/V")
        if field.get("/FT") != "/Sig" or value is None:
            continue
        value = value.get_object()
        if value.get("/Contents") and value.get("/ByteRange"):
            count += 1
    return count


def render(page, dpi):
    width = math.ceil(page.rect.width * dpi / 72)
    height = math.ceil(page.rect.height * dpi / 72)
    case.require(
        width > 0 and height > 0 and width * height <= MAX_PIXELS, "pdf_pixel_limit"
    )
    return page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False, annots=True)


def compare_page(original, candidate, visual):
    case.require(
        abs(original.rect.width - candidate.rect.width) < 1
        and abs(original.rect.height - candidate.rect.height) < 1,
        "pdf_comparison_failed",
    )
    if not visual:
        case.require(
            original.rotation == candidate.rotation
            and tuple(original.mediabox) == tuple(candidate.mediabox)
            and tuple(original.cropbox) == tuple(candidate.cropbox)
            and original.get_text() == candidate.get_text(),
            "pdf_comparison_failed",
        )
    a, b = render(original, 150), render(candidate, 150)
    case.require(a.width == b.width and a.height == b.height, "pdf_comparison_failed")
    if visual:
        # OCR image compression is lossy; important figures still require visual review.
        changed = sum(abs(x - y) > 20 for x, y in zip(a.samples, b.samples))
        case.require(changed * 100 <= len(a.samples), "pdf_comparison_failed")
    else:
        case.require(a.samples == b.samples, "pdf_comparison_failed")
    return a, b


def _process(folder, connection, options):
    original = (folder / "original.pdf").read_bytes()
    doc = pymupdf.open(stream=original, filetype="pdf")
    encrypted = doc.needs_pass
    password = None
    if encrypted:
        case.require(options["allow_encrypted"], "encrypted_pdf_unsupported")
        connection.send({"need": "document_password"})
        password = connection.recv()
        case.require(
            type(password) is str and doc.authenticate(password),
            "incorrect_pdf_password",
        )
    case.require(not doc.is_repaired, "pdf_repaired")
    case.require(0 < len(doc) <= MAX_PAGES, "pdf_page_limit")
    reader = PdfReader(io.BytesIO(original), strict=True)
    if reader.is_encrypted:
        case.require(options["allow_encrypted"], "encrypted_pdf_unsupported")
        case.require(reader.decrypt(password or ""), "incorrect_pdf_password")
    signed = signature_count(reader)
    pages = []
    scans = []
    for index, page in enumerate(doc):
        pix = render(page, 150)
        pix.save(folder / f"source-{index + 1}.png")
        content = page.get_text()
        case.require(len(content.encode()) <= 1024 * 1024, "pdf_text_limit")
        scan = not content.strip() and bool(page.get_images())
        scans.append(scan)
        pages.append(
            {
                "page": index + 1,
                "rotation": page.rotation,
                "width": str(page.rect.width),
                "height": str(page.rect.height),
                "scan": scan,
                "source_text": content,
                "source_render_sha256": sha(pix.samples),
            }
        )
    report = {
        "status": "needs_review",
        "reason": None,
        "encrypted": bool(reader.is_encrypted),
        "signature_count": signed,
        "signature_validation": "present_unvalidated" if signed else "none_detected",
        "conversion_authorized": options["convert_signed"],
        "copy_kind": "visual_ocr_copy"
        if any(scans)
        else "visual_copy"
        if signed
        else "unencrypted_working_copy",
        "working_sha256": None,
        "page_count": len(doc),
        "pages": pages,
        "structural_checks_passed": False,
        "review": None,
    }
    if signed and not options["convert_signed"]:
        report.update(
            status="preserved_signed",
            copy_kind="signed_original",
            structural_checks_passed=True,
        )
        return report
    candidate = folder / "candidate.pdf"
    if any(scans):
        out = pymupdf.open()
        for index, scan in enumerate(scans):
            if not scan:
                out.insert_pdf(doc, from_page=index, to_page=index)
                continue
            pix = render(doc[index], 200)
            image = folder / f"ocr-{index + 1}.png"
            pix.save(image)
            prefix = folder / f"ocr-{index + 1}"
            args = [options["tesseract"], str(image), str(prefix)]
            if options["tessdata"]:
                args += ["--tessdata-dir", options["tessdata"]]
            args += [
                "-l",
                "heb+eng",
                "--dpi",
                "200",
                "--psm",
                "3",
                "-c",
                "tessedit_create_pdf=1",
            ]
            try:
                run = subprocess.run(
                    args, capture_output=True, timeout=OCR_SECONDS, check=False
                )
            except subprocess.TimeoutExpired:
                raise case.CaseError("pdf_ocr_timeout") from None
            case.require(
                run.returncode == 0 and prefix.with_suffix(".pdf").is_file(),
                "pdf_ocr_unavailable",
            )
            with pymupdf.open(prefix.with_suffix(".pdf")) as ocr:
                case.require(
                    len(ocr) == 1 and ocr[0].get_text().strip(), "pdf_ocr_empty"
                )
                out.insert_pdf(ocr)
        out.save(candidate)
        out.close()
    else:
        writer = PdfWriter(clone_from=reader)
        with candidate.open("wb") as stream:
            writer.write(stream)
    password = None
    check = PdfReader(candidate, strict=True)
    case.require(
        not check.is_encrypted and len(check.pages) == len(doc), "pdf_comparison_failed"
    )
    with pymupdf.open(candidate) as output:
        case.require(
            not output.needs_pass
            and not output.is_repaired
            and len(output) == len(doc),
            "pdf_comparison_failed",
        )
        for index, page in enumerate(doc):
            a, b = compare_page(page, output[index], scans[index])
            b.save(folder / f"working-{index + 1}.png")
            pages[index].update(
                working_text=output[index].get_text(),
                working_rotation=output[index].rotation,
                working_render_sha256=sha(b.samples),
                render_comparison="within_visual_tolerance"
                if scans[index]
                else "exact",
                source_render_sha256=sha(a.samples),
            )
    os.rename(candidate, folder / "working.pdf")
    report.update(
        working_sha256=sha((folder / "working.pdf").read_bytes()),
        structural_checks_passed=True,
    )
    return report


def _worker(folder, connection, options):
    os.setsid()
    os.umask(0o077)
    # Unexpected parser tracebacks must stay private; the parent fails closed on EOF.
    null = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(null, 1)
        os.dup2(null, 2)
    finally:
        os.close(null)
    logging.disable(logging.CRITICAL)
    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    try:
        report = _process(Path(folder), connection, options)
    except case.CaseError as exc:
        report = {"status": "failed", "reason": exc.code}
    except (
        PyPdfError,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        LookupError,
        ArithmeticError,
        EOFError,
    ):
        report = {"status": "failed", "reason": "pdf_invalid_or_unsupported"}
    connection.send({"report": report})
    connection.close()


def process_one(
    root,
    data,
    display_name,
    owner,
    tax_year,
    purpose,
    options,
    password_provider=hidden_password,
):
    options = {
        **options,
        "allow_encrypted": hidden_password is not None
        and password_provider is not None,
    }
    document_id = uuid.uuid4().hex
    with case.document_directory(root, create=True) as parent:
        folder = parent / document_id
        folder.mkdir(mode=0o700)
        private_write(folder / "original.pdf", data)
        context = multiprocessing.get_context("spawn")
        connection, child = context.Pipe()
        worker = context.Process(target=_worker, args=(str(folder), child, options))
        worker.start()
        child.close()
        deadline = time.monotonic() + DOCUMENT_SECONDS
        report = {"status": "failed", "reason": "pdf_document_timeout"}
        try:
            while time.monotonic() < deadline:
                if not connection.poll(min(0.1, max(0, deadline - time.monotonic()))):
                    if not worker.is_alive():
                        report = {"status": "failed", "reason": "pdf_worker_failed"}
                        break
                    continue
                message = connection.recv()
                if "need" in message:
                    connection.send(password_provider())
                else:
                    report = message["report"]
                    break
        except (case.CaseError, EOFError) as exc:
            report = {
                "status": "failed",
                "reason": getattr(exc, "code", "pdf_worker_failed"),
            }
        finally:
            if worker.is_alive():
                try:
                    os.killpg(worker.pid, signal.SIGTERM)
                except ProcessLookupError:
                    worker.terminate()
            worker.join(2)
            if worker.is_alive():
                os.killpg(worker.pid, signal.SIGKILL)
                worker.join()
            connection.close()
        if report["reason"] == "encrypted_pdf_unsupported":
            (folder / "original.pdf").unlink()
            folder.rmdir()
            return {
                **report,
                "display_filename": display_name,
                "attachment_ready": False,
            }
        if report["status"] == "failed":
            for path in folder.iterdir():
                if path.name != "original.pdf":
                    path.unlink()
            report.update(
                structural_checks_passed=False, working_sha256=None, review=None
            )
        else:
            for path in folder.glob("ocr-*"):
                path.unlink()
        report.update(
            document_id=document_id,
            owner=owner,
            tax_year=tax_year,
            purpose=purpose,
            display_filename=display_name,
            original_sha256=sha(data),
            attachment_ready=False,
            recipient_acceptance="unconfirmed",
        )
        private_write(folder / "report.json", case.canonical(report))
        return report


def process(
    root,
    input_path,
    owner,
    tax_year,
    purpose,
    authorized=False,
    convert_signed=False,
    tesseract=None,
    tessdata=None,
    password_provider=hidden_password,
):
    case.require(authorized is True, "document_authorization_required")
    state = case.load(root)
    case.require(
        owner in {p["id"] for p in state["participants"]}
        and tax_year in state["years"],
        "owner_year_mismatch",
    )
    case.text(purpose)
    source = Path(input_path)
    case.require(
        source.is_absolute()
        and not any(p.is_symlink() for p in (source, *source.parents)),
        "unsafe_pdf_path",
    )
    paths = sorted(source.glob("*.pdf")) if source.is_dir() else [source]
    case.require(0 < len(paths) <= MAX_FILES, "pdf_batch_count_limit")
    sizes = []
    for path in paths:
        case.require(not path.is_symlink() and path.is_file(), "unsafe_pdf_path")
        sizes.append(path.stat().st_size)
    case.require(sum(sizes) <= MAX_BATCH, "pdf_batch_size_limit")
    options = {
        "convert_signed": bool(convert_signed),
        "tesseract": tesseract or shutil.which("tesseract") or "tesseract",
        "tessdata": tessdata,
    }
    reports = []
    for path in paths:
        try:
            data = file_bytes(path)
        except (case.CaseError, OSError) as exc:
            reports.append(
                {
                    "display_filename": path.name,
                    "status": "failed",
                    "reason": exc.code
                    if isinstance(exc, case.CaseError)
                    else "local_io_error",
                    "attachment_ready": False,
                }
            )
            continue
        report = process_one(
            root, data, path.name, owner, tax_year, purpose, options, password_provider
        )
        if "document_id" in report:
            state = case.register_document(root, state, report)
        reports.append(report)
    return {
        "ok": all(r["status"] != "failed" for r in reports),
        "documents": reports,
        "revision": state["revision"],
    }
