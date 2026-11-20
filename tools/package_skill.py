"""Validate and deterministically package the portable skill; never install it."""

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
import zipfile
from pathlib import Path

import yaml

DESCRIPTION = "Find your tax documents, estimate your refund or balance due, and see what still needs filing."
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "taxtidy-israel"

FILES = frozenset(
    (
        "DEMO.md",
        "SETUP.md",
        "VERIFICATION.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "plugin.json",
        "skills/taxtidy-israel/SKILL.md",
        "skills/taxtidy-israel/assets/rules/2025.json",
        "skills/taxtidy-israel/assets/rules/services.json",
        "skills/taxtidy-israel/assets/templates/checkpoint.json",
        "skills/taxtidy-israel/assets/templates/document-review.json",
        "skills/taxtidy-israel/assets/templates/evidence.json",
        "skills/taxtidy-israel/assets/templates/inquiry.md",
        "skills/taxtidy-israel/assets/templates/year-summary.md",
        "skills/taxtidy-israel/references/case-format.md",
        "skills/taxtidy-israel/references/collection.md",
        "skills/taxtidy-israel/references/equity-and-benefits.md",
        "skills/taxtidy-israel/references/languages.md",
        "skills/taxtidy-israel/references/pdf-workflow.md",
        "skills/taxtidy-israel/references/portal-and-routing.md",
        "skills/taxtidy-israel/references/tax-rules.md",
        "skills/taxtidy-israel/requirements.txt",
        "skills/taxtidy-israel/scripts/calculate.py",
        "skills/taxtidy-israel/scripts/case.py",
        "skills/taxtidy-israel/scripts/pdf_tools.py",
        "skills/taxtidy-israel/scripts/taxtidy.py",
    )
)


def package_files(root):
    files = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("package_symlink")
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        if "__pycache__" in path.parts and path.suffix == ".pyc":
            continue
        if relative not in FILES or not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("unexpected_package_file")
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("package_file_too_large")
        data = path.read_bytes()
        text = data.decode("utf-8")
        if re.search(
            r"/Users/|/home/|/private/(?:var|tmp)/|BEGIN [A-Z ]*PRIVATE KEY|(?:sk|ghp)-[A-Za-z0-9]{20,}",
            text,
        ):
            raise ValueError("private_package_content")
        files[relative] = data
    if set(files) != FILES:
        raise ValueError("missing_package_file")
    return files


def check(root):
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("unsafe_package_root")
    root = root.resolve()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("package_symlink")
    package_files(root)
    manifest = json.loads((root / "plugin.json").read_text())
    if (
        not isinstance(manifest, dict)
        or manifest.get("$schema")
        != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
        or manifest.get("name") != "taxtidy-israel"
        or manifest.get("version") != "0.1.1"
        or manifest.get("description") != DESCRIPTION
    ):
        raise ValueError("invalid_manifest")
    if set(manifest) != {"$schema", "name", "version", "description", "extensions"}:
        raise ValueError("unexpected_manifest_fields")
    interface = manifest["extensions"]["com.openai"]["interface"]
    if interface != {
        "displayName": "TaxTidy Israel",
        "shortDescription": "Israeli tax document guidance",
        "capabilities": [],
    }:
        raise ValueError("invalid_interface")
    skill = root / "skills/taxtidy-israel"
    content = (skill / "SKILL.md").read_text(encoding="utf-8")
    if len(content.encode()) > 1024 * 1024 or not content.startswith("---\n"):
        raise ValueError("invalid_skill")
    front = yaml.safe_load(content.split("---", 2)[1])
    if front != {"name": "taxtidy-israel", "description": DESCRIPTION}:
        raise ValueError("invalid_skill_frontmatter")
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


def check_archive(path):
    path = Path(path)
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > 32 * 1024 * 1024
    ):
        raise ValueError("unsafe_archive")
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory() as parent:
        members = archive.infolist()
        expected = {"taxtidy-israel/" + name for name in FILES}
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
        check(root)
    print("Archive entries, resources, limits and private-content checks verified.")


def build(root, output):
    root, output = Path(root), Path(output).absolute()
    check(root)
    if output.is_relative_to(root.resolve()) or output.is_symlink():
        raise ValueError("unsafe_archive_destination")
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
            for name, data in sorted(package_files(root).items()):
                info = zipfile.ZipInfo("taxtidy-israel/" + name, (2026, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        check_archive(candidate)
        os.replace(candidate, output)
    finally:
        candidate.unlink(missing_ok=True)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "build", "check-archive"])
    parser.add_argument("archive", type=Path, nargs="?")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    try:
        if args.action == "check":
            check(args.root)
        elif args.action == "check-archive":
            if args.archive is None:
                raise ValueError("missing_archive")
            check_archive(args.archive)
        else:
            output = (
                args.archive or DEFAULT_ROOT.parent / "dist/taxtidy-israel-0.1.1.zip"
            )
            digest = build(args.root, output)
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
