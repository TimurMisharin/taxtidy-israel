# Develop and package TaxTidy Israel

The canonical skill is under `taxtidy-israel/skills/taxtidy-israel/`. The sibling plugin manifest and guides define the Agent Plugin. The repository catalog in `.agents/plugins/marketplace.json` points to `./taxtidy-israel`. The packager builds the standalone and OpenAI projections from the same allowlisted resources. Keep private cases, original documents and host logs outside the entire checkout and active workspace.

## Prepare the test environment

Use Python 3.12.14 with the development lockfile and the separately managed Tesseract 5.5.4 and models described in [setup](taxtidy-israel/SETUP.md). The existing PDF tests use `/opt/homebrew/bin/tesseract` and `.runtime/tessdata`; point the latter at the verified model directory for the suite. See [third-party notices](THIRD_PARTY_NOTICES.md) for dependency licensing.

```sh
python3 -m pip install -r requirements-dev.lock
python3 -m compileall -q taxtidy-israel/skills/taxtidy-israel/scripts tests tools
python3 -m ruff check taxtidy-israel/skills/taxtidy-israel/scripts tests tools
python3 -m ruff format --check taxtidy-israel/skills/taxtidy-israel/scripts tests tools
python3 -m unittest discover -v -s tests -t .
python3 -m tests.test_acceptance --report dist/synthetic-acceptance.json
```

The suite uses fictional fixtures. Its reports and any intermediate PDFs remain outside the distributable. A skipped or unavailable prerequisite does not establish coverage.

## Build and check the four ZIPs

```sh
python3 tools/package_skill.py check
python3 tools/package_skill.py build dist/taxtidy-israel-plugin.zip
python3 tools/package_skill.py check-archive dist/taxtidy-israel-plugin.zip
python3 tools/package_skill.py build-public dist/taxtidy-israel-openai.zip
python3 tools/package_skill.py check-public-archive dist/taxtidy-israel-openai.zip
python3 tools/package_skill.py build-skill dist/taxtidy-israel-skill-local.zip --profile local
python3 tools/package_skill.py check-skill-archive dist/taxtidy-israel-skill-local.zip --profile local
python3 tools/package_skill.py build-skill dist/taxtidy-israel-skill-hosted.zip --profile hosted
python3 tools/package_skill.py check-skill-archive dist/taxtidy-israel-skill-hosted.zip --profile hosted
```

Both standalone commands take an explicit path and profile. The ZIP contents come from the packager's allowlist. ZIPs use deterministic entry order, timestamps and modes. The builder validates the candidate before replacing the destination and writes a SHA-256 sidecar. Compare two builds using the same toolchain. Check links within each archive whenever files move.

Use the [public-use policy](submission/public-use.md), [public setup](submission/SETUP.md) and [privacy notice](PRIVACY.md) for both public projections. Only the OpenAI wrapper uses [listing metadata](submission/metadata.json) and the OpenAI icon. Both public builds exclude the local password helper and reject encrypted PDFs. Review [OpenAI's directory requirements](https://developers.openai.com/plugins/deploy/submission) before proposing a listing change.

For Perplexity, confirm the active account's compressed-upload limit and the documented 20 MB unpacked cap and 1,000-file plugin limit. Standalone intake requires a root-level skill, at most 100 files and a 20 MB cap for both sizes. The packager applies these numerical ceilings to the corresponding public ZIPs. An upload pilot still needs to verify layout, account permissions and access to bundled references. [Plugin intake](https://www.perplexity.ai/help-center/en/articles/2026100802-create-or-upload-a-custom-plugin) · [Skill intake](https://www.perplexity.ai/help-center/en/articles/13914413-how-to-use-computer-skills)

## Review and release

1. Use a reviewed `main` revision and a clean checkout. Follow the review process in [Contributing](CONTRIBUTING.md).
2. Check published GitHub and OpenAI versions before choosing the release version. Align the Agent Plugin manifest, the packaging version and the OpenAI listing metadata with the reviewed release plan.
3. Rerun checks and build from the reviewed tag. Record the source commit, tag, package version, ZIP name and SHA-256. Record each host version or account surface, route, fixture, date and capability outcome in [Verification](VERIFICATION.md).
4. Repeat clean-session discovery and synthetic guidance checks for each claimed host route. For local execution verify the supported estimate, suppressed figures for unsupported or conflicting inputs, PDF source preservation and manual review, OCR, and resume with a stale estimate. For rollback use private synthetic schema-v1 copies and the previous verified artifact's checksum.
5. Publish reviewed ZIPs and sidecars through [GitHub Releases](https://github.com/TimurMisharin/taxtidy-israel/releases). Confirm remote assets and their hashes. Record public directory submission, approval and host activation independently.
