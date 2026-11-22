"""Validate and deterministically package the portable skill; never install it."""

import argparse
import hashlib
import json
import os
import re
import stat
import struct
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

import yaml

DESCRIPTION = "Find your tax documents, estimate your refund or balance due, and see what still needs filing."
PUBLIC_DESCRIPTION = "Organize Israeli tax records, reconcile evidence, and explore limited 2025 estimates using redacted or fictional inputs."
VERSION = "0.1.3"
INSTALL_SUBTITLE = "כלי עזר בלבד • אינו ייעוץ מס"
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "taxtidy-israel"
SUBMISSION_ROOT = DEFAULT_ROOT.parent / "submission"
ICON = "assets/icon.png"
SKILL = "skills/taxtidy-israel/SKILL.md"
PASSWORD_HELPER = "skills/taxtidy-israel/scripts/pdf_password.py"
PDF_REFERENCE = "skills/taxtidy-israel/references/pdf-workflow.md"
COLLECTION_REFERENCE = "skills/taxtidy-israel/references/collection.md"

FILES = frozenset(
    (
        "DEMO.md",
        "SETUP.md",
        "VERIFICATION.md",
        "LICENSE",
        "LICENSE-NOTICE.md",
        "THIRD_PARTY_NOTICES.md",
        "plugin.json",
        SKILL,
        "skills/taxtidy-israel/assets/rules/2025.json",
        "skills/taxtidy-israel/assets/rules/services.json",
        "skills/taxtidy-israel/assets/templates/checkpoint.json",
        "skills/taxtidy-israel/assets/templates/document-review.json",
        "skills/taxtidy-israel/assets/templates/evidence.json",
        "skills/taxtidy-israel/assets/templates/inquiry.md",
        "skills/taxtidy-israel/assets/templates/year-summary.md",
        "skills/taxtidy-israel/references/case-format.md",
        COLLECTION_REFERENCE,
        "skills/taxtidy-israel/references/equity-and-benefits.md",
        "skills/taxtidy-israel/references/languages.md",
        PDF_REFERENCE,
        "skills/taxtidy-israel/references/portal-and-routing.md",
        "skills/taxtidy-israel/references/tax-rules.md",
        "skills/taxtidy-israel/requirements.txt",
        "skills/taxtidy-israel/scripts/calculate.py",
        "skills/taxtidy-israel/scripts/case.py",
        PASSWORD_HELPER,
        "skills/taxtidy-israel/scripts/pdf_tools.py",
        "skills/taxtidy-israel/scripts/taxtidy.py",
    )
)
PUBLIC_FILES = (FILES - {PASSWORD_HELPER, "DEMO.md", "VERIFICATION.md"}) | {
    ICON,
    "PRIVACY.md",
}


def package_files(root, expected=FILES):
    files = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("package_symlink")
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        if "__pycache__" in path.parts and path.suffix == ".pyc":
            continue
        if relative not in expected or not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("unexpected_package_file")
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("package_file_too_large")
        data = path.read_bytes()
        if relative == ICON:
            check_icon(data)
            files[relative] = data
            continue
        text = data.decode("utf-8")
        if re.search(
            r"/Users/|/home/|/private/(?:var|tmp)/|BEGIN [A-Z ]*PRIVATE KEY|(?:sk|ghp)-[A-Za-z0-9]{20,}",
            text,
        ):
            raise ValueError("private_package_content")
        files[relative] = data
    if set(files) != expected:
        raise ValueError("missing_package_file")
    return files


def check_icon(data):
    if not data.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR") or len(data) < 45:
        raise ValueError("invalid_icon_png")
    width, height = struct.unpack_from(">II", data, 16)
    if width != height or not 256 <= width <= 4096:
        raise ValueError("invalid_icon_dimensions")


def single_line(value, limit):
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value) <= limit
        and value.splitlines() == [value]
    )


def check_public_manifest(manifest):
    platform = manifest["extensions"]["com.openai"]
    if set(platform) != {"interface", "review", "publication"}:
        raise ValueError("unexpected_public_extension")
    interface = platform["interface"]
    if (
        not single_line(manifest["author"]["name"], 80)
        or not single_line(interface.get("displayName"), 30)
        or not single_line(interface.get("shortDescription"), 30)
        or interface.get("category") != "Finance"
        or interface.get("logo") != f"./{ICON}"
        or interface.get("composerIcon") != f"./{ICON}"
        or not isinstance(interface.get("longDescription"), str)
        or not 1 <= len(interface["longDescription"]) <= 4000
        or "Before installing:" not in interface["longDescription"]
    ):
        raise ValueError("invalid_public_listing")
    if not single_line(interface.get("developerName"), 80):
        raise ValueError("invalid_developer_name")
    for field in ("websiteURL", "supportURL", "termsOfServiceURL", "privacyPolicyURL"):
        url = interface[field]
        parsed = urlsplit(url)
        if (
            not single_line(url, 1024)
            or parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
        ):
            raise ValueError("invalid_public_url")
    starters = interface["defaultPrompt"]
    if (
        not isinstance(starters, list)
        or not 1 <= len(starters) <= 3
        or any(not single_line(prompt, 128) or "@" in prompt for prompt in starters)
        or len(
            {
                " ".join(unicodedata.normalize("NFKC", prompt).split())
                for prompt in starters
            }
        )
        != len(starters)
    ):
        raise ValueError("invalid_starter_prompts")
    review = platform["review"]["prompts"]
    if (
        not isinstance(review, list)
        or not 1 <= len(review) <= 20
        or type(platform["review"].get("commerce")) is not bool
        or any(
            not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 4000
            for prompt in review
        )
        or not single_line(platform["publication"].get("release_notes"), 4000)
    ):
        raise ValueError("invalid_public_review")


def check(root, public=False):
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("unsafe_package_root")
    root = root.resolve()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("package_symlink")
    package_files(root, PUBLIC_FILES if public else FILES)
    manifest = json.loads((root / "plugin.json").read_text())
    if (
        not isinstance(manifest, dict)
        or manifest.get("$schema")
        != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
        or manifest.get("name") != "taxtidy-israel"
        or (
            not re.fullmatch(
                r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", manifest.get("version", "")
            )
            if public
            else manifest.get("version") != VERSION
        )
        or manifest.get("description")
        != (PUBLIC_DESCRIPTION if public else DESCRIPTION)
    ):
        raise ValueError("invalid_manifest")
    expected_fields = {"$schema", "name", "version", "description", "extensions"}
    if public:
        expected_fields.add("author")
    if set(manifest) != expected_fields or set(manifest["extensions"]) != {
        "com.openai"
    }:
        raise ValueError("unexpected_manifest_fields")
    interface = manifest["extensions"]["com.openai"]["interface"]
    if not isinstance(interface, dict):
        raise TypeError("invalid_interface")
    notice = interface.get("longDescription")
    if public:
        check_public_manifest(manifest)
    elif {k: v for k, v in interface.items() if k != "longDescription"} != {
        "displayName": "TaxTidy Israel",
        "shortDescription": INSTALL_SUBTITLE,
        "termsOfServiceURL": "https://github.com/TimurMisharin/taxtidy-israel/blob/main/taxtidy-israel/LICENSE-NOTICE.md",
        "capabilities": [],
    } or (
        not isinstance(notice, str)
        or not notice.startswith("הודעה לפני התקנה:")
        or "Before installing:" not in notice
        or len(notice) > 4000
    ):
        raise ValueError("invalid_interface")
    skill = root / "skills/taxtidy-israel"
    content = (skill / "SKILL.md").read_text(encoding="utf-8")
    if len(content.encode()) > 1024 * 1024 or not content.startswith("---\n"):
        raise ValueError("invalid_skill")
    front = yaml.safe_load(content.split("---", 2)[1])
    if front != {
        "name": "taxtidy-israel",
        "description": PUBLIC_DESCRIPTION if public else DESCRIPTION,
    }:
        raise ValueError("invalid_skill_frontmatter")
    if public and "## Privacy and scope for the public plugin\n" not in content:
        raise ValueError("missing_public_privacy_instructions")
    for md in root.rglob("*.md"):
        for link in re.findall(r"\]\(([^)]+)\)", md.read_text()):
            if link.startswith(("https://", "#")):
                continue
            candidate = (md.parent / link.split("#")[0]).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file():
                raise ValueError("unsafe_or_missing_resource")
    for required in (
        "scripts/taxtidy.py",
        "scripts/case.py",
        "references/case-format.md",
        "references/collection.md",
        "requirements.txt",
    ):
        if not (skill / required).is_file():
            raise ValueError("missing_resource")
    for filename in ("checkpoint.json", "evidence.json"):
        template = json.loads((skill / "assets/templates" / filename).read_text())
        if not isinstance(template, dict):
            raise TypeError("invalid_template")
    blank = json.loads((skill / "assets/templates/checkpoint.json").read_text())
    if (
        blank.get("case_id") is not None
        or blank.get("observations") != []
        or blank.get("results") != []
    ):
        raise ValueError("template_contains_case_data")
    if "## Supported local workflow" not in content or not all(
        (skill / name).is_file()
        for name in (
            "scripts/calculate.py",
            "assets/rules/2025.json",
            "assets/rules/services.json",
            "references/tax-rules.md",
            "references/equity-and-benefits.md",
            "references/portal-and-routing.md",
            "references/languages.md",
            "scripts/pdf_tools.py",
            "references/pdf-workflow.md",
            "assets/templates/document-review.json",
        )
    ):
        raise ValueError("phase_coverage_mismatch")
    review = json.loads((skill / "assets/templates/document-review.json").read_text())
    if type(review) is not dict:
        raise ValueError("invalid_document_review_template")
    rules = json.loads((skill / "assets/rules/2025.json").read_text())
    if (
        type(rules) is not dict
        or rules.get("tax_year") != 2025
        or rules.get("engine_version") != "0.2.1"
        or type(rules.get("rules")) is not dict
        or not rules["rules"]
        or type(rules.get("sources")) is not dict
        or type(rules.get("coverage")) is not dict
        or rules["coverage"].get("filing_ready") is not False
    ):
        raise ValueError("invalid_rule_coverage")
    for rule in rules["rules"].values():
        if (
            type(rule) is not dict
            or rule.get("effective_year") != 2025
            or rule.get("verified") is not True
            or rule.get("source_id") not in rules["sources"]
        ):
            raise ValueError("unverified_rule")
    print(
        "Package structure, identity, templates, contained links and release scope verified."
    )


def check_archive(path, public=False):
    path = Path(path)
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > 32 * 1024 * 1024
    ):
        raise ValueError("unsafe_archive")
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory() as parent:
        members = archive.infolist()
        expected = {
            "taxtidy-israel/" + name for name in (PUBLIC_FILES if public else FILES)
        }
        if len(members) != len(expected) or {m.filename for m in members} != expected:
            raise ValueError("unexpected_archive_members")
        root = Path(parent) / "taxtidy-israel"
        for member in members:
            if (
                member.file_size > 1024 * 1024
                or member.flag_bits & 1
                or stat.S_IFMT(member.external_attr >> 16) != stat.S_IFREG
            ):
                raise ValueError("unsafe_archive_member")
            target = Path(parent) / member.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
        check(root, public=public)
    print("Archive entries, resources, limits and private-content checks verified.")


def build(root, output):
    root, output = Path(root), Path(output).absolute()
    check(root)
    if output.is_relative_to(root.resolve()) or output.is_symlink():
        raise ValueError("unsafe_archive_destination")
    return write_archive(output, package_files(root))


def build_public(root, output):
    root, output = Path(root), Path(output).absolute()
    check(root)
    if output.is_relative_to(root.resolve()) or output.is_symlink():
        raise ValueError("unsafe_archive_destination")
    files = {
        name: data for name, data in package_files(root).items() if name in PUBLIC_FILES
    }
    metadata = json.loads((SUBMISSION_ROOT / "metadata.json").read_text())
    manifest = json.loads(files["plugin.json"])
    manifest["version"] = metadata["version"]
    manifest["author"] = metadata["author"]
    manifest["description"] = PUBLIC_DESCRIPTION
    extension = manifest["extensions"]["com.openai"]
    interface = extension["interface"]
    interface.update(metadata["interface"])
    interface["longDescription"] = (
        "Organize evidence for Israeli taxes, reconcile payroll and Section 46 donations, "
        "and see which documents or acknowledgments are missing. Start with a tax year and "
        "goal. Use fictional examples or redacted inputs. A compatible private local runtime "
        "can run limited 2025 estimates and review unencrypted PDFs. The user handles any filing.\n\n"
        + interface["longDescription"]
    )
    extension["review"] = metadata["review"]
    extension["publication"] = metadata["publication"]
    files["plugin.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode()

    skill, separator, _ = (
        files[SKILL].decode().partition("\n## Setup and release evidence\n")
    )
    if not separator:
        raise ValueError("missing_release_evidence_section")
    heading = "\n## Supported local workflow\n"
    if heading not in skill:
        raise ValueError("missing_workflow_section")
    public_use = (SUBMISSION_ROOT / "public-use.md").read_text().rstrip()
    skill = skill.replace(heading, f"\n{public_use}\n{heading}", 1)
    skill = skill.replace(
        f"description: {DESCRIPTION}", f"description: {PUBLIC_DESCRIPTION}", 1
    )
    skill = skill.replace("known-password working copies", "unencrypted working copies")
    skill = skill.replace(
        "Offer existing-document upload, an explicitly authorized search of an actually "
        "available connected account, or manual retrieval.",
        "Start with manual retrieval and use only the minimum redacted or fictional inputs.",
    )
    skill = (
        skill.replace(
            "Use available connected capabilities only within the taxpayer's authorization. ",
            "",
        )
        .replace(
            "send only with explicit recipient/purpose authorization.",
            "let the taxpayer review and send it.",
        )
        .replace(
            "Before any real transmission, show taxpayer, year, form/version, amounts, "
            "attachments, signatures and outstanding judgments. Follow the user's actual "
            "authorization and the available host capabilities.",
            "Provide a checklist of the year, form/version and evidence the taxpayer should "
            "verify before filing. Leave any real submission to the taxpayer.",
        )
    )
    files[SKILL] = (
        skill
        + "\n## Setup\n\nSee [setup](../../SETUP.md) and the [privacy notice](../../PRIVACY.md).\n"
    ).encode()
    pdf = files[PDF_REFERENCE].decode()
    start = "The input may be one file"
    before, separator, rest = pdf.partition(start)
    if not separator:
        raise ValueError("missing_pdf_input_instructions")
    _, separator, after = rest.partition("\n\n")
    if not separator:
        raise ValueError("missing_pdf_input_instructions")
    files[PDF_REFERENCE] = (
        before
        + "Use one redacted, unencrypted PDF or a directory of selected redacted, "
        "unencrypted PDFs. Ask the user to confirm redaction before local processing. "
        "Use aliases for case and source identifiers. Encrypted PDFs are rejected."
        + separator
        + after.replace(
            "A wrong password, parser repair/corruption", "Parser repair/corruption"
        )
    ).encode()
    collection = files[COLLECTION_REFERENCE].decode()
    intro, heading, remainder = collection.partition("\n## Connected accounts\n")
    if not heading:
        raise ValueError("missing_collection_section")
    _, heading, following = remainder.partition(
        "\n## Closed accounts, insurance and issuer requests\n"
    )
    if not heading:
        raise ValueError("missing_manual_collection_section")
    files[COLLECTION_REFERENCE] = (
        intro
        + "\n## Manual retrieval\n\nAsk the taxpayer to obtain their own records. Use official public "
        "sources to explain the process and placeholders for any inquiry draft. "
        "Login and one-time verification stay with the taxpayer.\n"
        + heading
        + following
    ).encode()
    files["SETUP.md"] = (SUBMISSION_ROOT / "SETUP.md").read_bytes()
    files["PRIVACY.md"] = (SUBMISSION_ROOT.parent / "PRIVACY.md").read_bytes()
    files[ICON] = (SUBMISSION_ROOT / "icon.png").read_bytes()
    return write_archive(output, files, public=True)


def write_archive(output, files, public=False):
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, candidate = tempfile.mkstemp(
        prefix=".taxtidy-", suffix=".zip", dir=output.parent
    )
    os.close(fd)
    candidate = Path(candidate)
    try:
        with zipfile.ZipFile(
            candidate, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo("taxtidy-israel/" + name, (2026, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        check_archive(candidate, public=public)
        os.replace(candidate, output)
    finally:
        candidate.unlink(missing_ok=True)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "check",
            "build",
            "check-archive",
            "build-public",
            "check-public-archive",
        ],
    )
    parser.add_argument("archive", type=Path, nargs="?")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    try:
        if args.action == "check":
            check(args.root)
        elif args.action in {"check-archive", "check-public-archive"}:
            if args.archive is None:
                raise ValueError("missing_archive")
            check_archive(args.archive, public=args.action == "check-public-archive")
        else:
            public = args.action == "build-public"
            if public and args.archive is None:
                raise ValueError("missing_archive")
            output = (
                args.archive
                or DEFAULT_ROOT.parent / f"dist/taxtidy-israel-{VERSION}.zip"
            )
            digest = (build_public if public else build)(args.root, output)
            checksum = output.with_suffix(".sha256")
            if checksum.is_symlink():
                raise ValueError("unsafe_checksum")
            checksum.write_text(digest + "  " + output.name + "\n")
            print("Built and inspected " + output.name + "; SHA-256 " + digest)
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        IndexError,
        UnicodeError,
        yaml.YAMLError,
        zipfile.BadZipFile,
    ):
        print("Package check failed: invalid structure or resource.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
