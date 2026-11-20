# TaxTidy Israel 0.1.0 setup

TaxTidy Israel is a ChatGPT plugin supplied as a portable skill package. Host installation and discovery are pending; no account plugin was created. Importing instructions does not install Python, OCR, mail access or browser access. Repository publication is not evidence of successful installation in ChatGPT.

Original project materials are [AGPL-3.0-only](LICENSE), allowing commercial use subject to the license's source-sharing and notice obligations. [Third-party notices](THIRD_PARTY_NOTICES.md) explain separately licensed dependencies; no commercial PyMuPDF license is supplied.

## Choose a deployment path

- Plain skill: retain this package tree and select `skills/taxtidy-israel/SKILL.md` using a host that supports local skills. Keep the root handoff documents with it so its relative links resolve. The exact installation location depends on the host; no host discovery has been tested for this release.
- Private plugin: where the host supports this portable manifest, import the archive containing one `taxtidy-israel/` root. This is a prepared package, not a claim that a particular host accepts it. Follow that host's current private-import instructions; no publication is needed.
- Manual use: read the skill and references, collect documents locally, and run the utility in a prepared runtime. A host without local execution can provide collection and research guidance only.

## Local runtime

The validated development runtime is Python 3.12.14 on single-user POSIX storage. Windows and shared multi-user case storage are not validated. Runtime pins are pypdf 7.1.1, cryptography 50.0.2 and PyMuPDF 2.1 in `skills/taxtidy-israel/requirements.txt`. No environment or dependency binary is included. PyMuPDF's upstream license is AGPL/commercial; this package supplies no commercial license or distribution-rights determination.

On a separately authorized machine, prepare Python and install the pinned requirements into an isolated environment using its package manager. Dependency installation was deliberately not run during this release handoff. Verify the resolved environment and audit it before real use; the retained development audit is not a fresh advisory check for another machine.

For scans, separately provide Tesseract 5.5.4 and the official `heb`, `eng`, `osd` models. Pass absolute paths using `--tesseract` and `--tessdata-dir`. The tested models are from [tessdata_fast revision 87416418657359cb625c412a48b6e1d6d41c29bd](https://github.com/tesseract-ocr/tessdata_fast/tree/87416418657359cb625c412a48b6e1d6d41c29bd), with its Apache-2.0 LICENSE. Models are excluded from the archive. Verify the downloaded bytes before use:

| File | SHA-256 |
|---|---|
| heb.traineddata | 11f9e43ab227f786352a50f75c94c2e9906f1baba86d93276da19da7ce0904db |
| eng.traineddata | 7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2 |
| osd.traineddata | 9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff |
| LICENSE | cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30 |

## Invoke the local utility

From `skills/taxtidy-israel`, use the prepared interpreter as `python3`. Replace the example paths with absolute, resolved paths in a private user-owned directory outside the package and development repository. The case parent must exist; the new case must not exist. Use a private shell with `umask 077`. These are fictional-case commands, not real-account actions:

```sh
python3 scripts/taxtidy.py --help
python3 scripts/taxtidy.py init --case-root /absolute/private/new-case --taxpayer-id fictional-taxpayer --years 2025 --language he --synthetic
python3 scripts/taxtidy.py import-evidence --case-root /absolute/private/new-case --input /absolute/private/reviewed-evidence.json
python3 scripts/taxtidy.py calculate --case-root /absolute/private/new-case --tax-year 2025
python3 scripts/taxtidy.py summary --case-root /absolute/private/new-case --as-of 2026-11-20
python3 scripts/taxtidy.py resume --case-root /absolute/private/new-case --language ru --as-of 2026-11-20
python3 scripts/taxtidy.py resume --case-root /absolute/private/new-case --language ar --as-of 2026-11-20
```

Use [case format](skills/taxtidy-israel/references/case-format.md) and the blank evidence template to prepare an input from actually reviewed sources, with current case ID/revision and a supported coverage profile. A copied template is not evidence and cannot alone enable an estimate. [The demo](DEMO.md) records which calls were actually executed.

Use [PDF workflow](skills/taxtidy-israel/references/pdf-workflow.md) for `pdf` and `review-document`. Supply a known PDF password only at the concealed local terminal prompt; never in chat, arguments, files or environment variables. If unavailable, ask the issuer for an accessible reissue. Compare rendered originals and copies, including year, minus signs and blank fields, before manually recording review. Local readiness is separate from recipient acceptance and filing.

No connector is bundled. Manual retrieval remains available. Any connected-account search or real submission requires separate explicit authorization and an actual available capability. Retain private checkpoints and originals outside the package; never put taxpayer records into templates or the release archive.

Keep every case outside the entire source checkout, including its repository root and sibling development directories. The runtime rejects paths inside the plugin package; its additional development-root detection uses private engineering scaffolding that is absent from a public clone. Do not rely on that additional guard or Git ignore rules to protect a case stored inside a checkout.
