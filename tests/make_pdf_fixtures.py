"""Synthetic PDFs and ephemeral signing keys; no passwords or private keys saved."""

import io
import os
from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path

import pymupdf
from asn1crypto import keys
from asn1crypto import x509 as asn1_x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from PIL import Image, ImageDraw, ImageFont
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign import signers
from pyhanko.sign.fields import SigFieldSpec
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext
from pyhanko_certvalidator.registry import SimpleCertificateStore
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject
from reportlab.pdfgen import canvas

from tests.support import ROOT, fixture


def save(path, data):
    path.write_bytes(data)
    path.chmod(0o600)


def make(parent, password):
    parent = Path(parent)
    parent.mkdir(mode=0o700, exist_ok=True)
    oracle = fixture()["phase4"]
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=(595, 842))
    for index, text in enumerate(oracle["text_lines"]):
        page.drawString(50, 790 - 35 * index, text)
    page.showPage()
    page.save()
    raw = buffer.getvalue()
    save(parent / "plain.pdf", raw)
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(raw)))
    writer.encrypt(password, algorithm="AES-256")
    protected = io.BytesIO()
    writer.write(protected)
    save(parent / "protected.pdf", protected.getvalue())
    # A signature field without a signature is a distinct negative fixture.
    empty = PdfWriter(clone_from=PdfReader(io.BytesIO(raw)))
    field = DictionaryObject(
        {
            NameObject("/FT"): NameObject("/Sig"),
            NameObject("/T"): TextStringObject("EmptySignature"),
        }
    )
    empty.root_object[NameObject("/AcroForm")] = empty._add_object(
        DictionaryObject(
            {NameObject("/Fields"): ArrayObject([empty._add_object(field)])}
        )
    )
    out = io.BytesIO()
    empty.write(out)
    save(parent / "empty-signature.pdf", out.getvalue())
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Fictional TaxTidy Fixture Only")]
    )
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    asn_cert = asn1_x509.Certificate.load(cert.public_bytes(serialization.Encoding.DER))
    signer = signers.SimpleSigner(
        asn_cert,
        keys.PrivateKeyInfo.load(
            key.private_bytes(
                serialization.Encoding.DER,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        ),
        SimpleCertificateStore(),
    )
    signed = signers.sign_pdf(
        IncrementalPdfFileWriter(io.BytesIO(raw)),
        signers.PdfSignatureMetadata(field_name="FictionalSignature"),
        signer=signer,
        new_field_spec=SigFieldSpec("FictionalSignature"),
    )
    signed_data = signed.getvalue()
    status = validate_pdf_signature(
        PdfFileReader(io.BytesIO(signed_data)).embedded_signatures[0],
        ValidationContext(trust_roots=[asn_cert], allow_fetching=False),
    )
    if not status.intact or not status.valid or not status.trusted:
        raise AssertionError("Synthetic cryptographic signature validation failed")
    save(parent / "signed.pdf", signed_data)
    # Shape logical Hebrew with installed MuPDF/HarfBuzz, then flatten to a real scan.
    image = Image.new("RGB", (1654, 2339), "white")
    draw = ImageDraw.Draw(image)
    # The Hebrew-only font has no digits; use Pillow's bundled Aileron for cells.
    latin = ImageFont.load_default(size=45)
    numeric_font = pymupdf.Font(fontbuffer=latin.path.getvalue())
    if any(not numeric_font.has_glyph(ord(char)) for char in "0123456789-"):
        raise AssertionError("Synthetic numeric font lacks required glyphs")
    for index, text in enumerate(oracle["hebrew_labels"]):
        y = 220 + index * 240
        with pymupdf.open() as label:
            label_page = label.new_page(width=750, height=120)
            spare, scale = label_page.insert_htmlbox(
                label_page.rect,
                '<div dir="rtl">' + escape(text) + "</div>",
                css="@font-face {font-family: fixture; src: url(hebrew-font.ttf);}"
                "* {font-family: fixture; font-size: 50pt; margin: 0; text-align: right;}",
                archive=pymupdf.Archive(str(ROOT / "tests/resources")),
                scale_low=1,
            )
            if spare < 0 or scale != 1:
                raise AssertionError("Synthetic Hebrew label does not fit")
            pix = label_page.get_pixmap(dpi=72, colorspace=pymupdf.csRGB, alpha=False)
            image.paste(
                Image.frombytes("RGB", (pix.width, pix.height), pix.samples),
                (700, y - 20),
            )
        draw.rectangle((160, y - 20, 680, y + 100), outline="black", width=3)
        value = oracle["scan_cells"][index]
        if value is not None:
            draw.text((220, y), value, font=latin, fill="black")
    raster = io.BytesIO()
    image.save(raster, format="PNG")
    pdf = pymupdf.open()
    pdf.new_page(width=595.44, height=842.04).insert_image(
        pymupdf.Rect(0, 0, 595.44, 842.04), stream=raster.getvalue()
    )
    save(parent / "hebrew-scan.pdf", pdf.tobytes())
    pdf.close()
    with pymupdf.open(stream=raw, filetype="pdf") as rotated:
        rotated[0].set_rotation(90)
        save(parent / "rotated.pdf", rotated.tobytes())
    save(parent / "corrupt.pdf", b"%PDF-1.7\nsynthetic corrupt input\n")
    oversized = PdfWriter()
    for _ in range(101):
        oversized.add_blank_page(width=100, height=100)
    out = io.BytesIO()
    oversized.write(out)
    save(parent / "too-many-pages.pdf", out.getvalue())
    giant = PdfWriter()
    giant.add_blank_page(width=4000, height=4000)
    out = io.BytesIO()
    giant.write(out)
    save(parent / "too-many-pixels.pdf", out.getvalue())
    return {
        "signature_intact": bool(status.intact),
        "signature_valid": bool(status.valid),
        "signature_trusted_only_in_fixture_context": bool(status.trusted),
        "oracle": oracle,
    }


def stalled_worker(folder, connection, options):
    """Deterministic timeout fixture runs in its own process group."""
    import time

    os.setsid()
    time.sleep(30)


def mismatching_worker(folder, connection, options):
    import pdf_tools

    compare = pdf_tools.compare_page

    def changed(original, candidate, visual):
        with pymupdf.open() as blank:
            blank.new_page(width=original.rect.width, height=original.rect.height)
            return compare(original, blank[0], visual)

    pdf_tools.compare_page = changed
    pdf_tools._worker(folder, connection, options)


def ocr_timeout_worker(folder, connection, options):
    import pdf_tools

    pdf_tools.OCR_SECONDS = 0.1
    pdf_tools._worker(folder, connection, options)


class UnexpectedFixtureError(Exception):
    """An unanticipated library exception outside the expected parser error classes."""


def unexpected_failure_worker(folder, connection, options):
    import pdf_tools

    def fail(*args):
        raise UnexpectedFixtureError(options["canary"])

    pdf_tools._process = fail
    pdf_tools._worker(folder, connection, options)
