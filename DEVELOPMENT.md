# Development and package layout

TaxTidy Israel is a ChatGPT plugin. `taxtidy-israel/` is the portable distributable; `tools/` and `tests/` are development material, not additional account integrations. Root READMEs and `assets/overview.svg` introduce the project. The plugin ZIP is built separately and distributed with a SHA-256 checksum through GitHub Releases.

## Existing environment

See [setup](taxtidy-israel/SETUP.md) for the validated Python 3.12.14/POSIX runtime and separately installed OCR prerequisites. `requirements-dev.txt` lists direct development dependencies; `requirements-dev.lock` records the validated environment. No environment or binary dependency is included. Preparing a new machine or discovering the plugin in ChatGPT has not been tested by this publication.

Keep cases and originals in a private directory outside the **entire checkout**. The runtime blocks case storage inside the plugin package, but additional development-root detection relies on private scaffolding absent from a public clone. Ignore rules are not an access-control boundary.

## Checks and package build

Run from the repository root using the prepared interpreter. The PDF tests additionally require Tesseract and the exact local models described in setup; missing prerequisites do not count as passing tests. These commands do not install anything:

```sh
python3 -m compileall -q taxtidy-israel/skills/taxtidy-israel/scripts tests tools
python3 tools/package_skill.py check
python3 -m ruff check taxtidy-israel/skills/taxtidy-israel/scripts tests tools
python3 -m ruff format --check taxtidy-israel/skills/taxtidy-israel/scripts tests tools
python3 -m unittest discover -v -s tests -t .
python3 tools/package_skill.py build
python3 tools/package_skill.py check-archive dist/taxtidy-israel-0.1.0.zip
```

The packager explicitly allowlists the deliverable. Git ignore rules do not determine ZIP contents. Review both inventories when adding resources; preserve the license and notices in the standalone package. Keep private evidence and generated files out of commits, and stage reviewed paths explicitly.

## Branches and releases

Use topic branches and fork-based pull requests to `main`; only the owner merges. The intended policy blocks direct updates, force pushes and deletion of `main`, with an owner-admin exception for PR merges only. The owner-only boundary depends on retaining the owner as the sole eligible administrator; granting another eligible admin changes it. See the final publication handoff for verified remote settings. No CI status is implied by these local commands.

Release assets are the inspected portable ZIP and checksum, built from the tagged source. GitHub's automatically generated source archives contain development files and are not the portable plugin download. See [verification](VERIFICATION.md), [license](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).
