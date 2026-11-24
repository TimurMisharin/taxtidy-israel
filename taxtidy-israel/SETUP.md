# TaxTidy Israel local setup

**Before installation or activation, read the [bilingual legal notice](LICENSE-NOTICE.md).** TaxTidy is a general-purpose aid provided as is. It does not replace tax, legal, financial, accounting, or other professional advice. See the [AGPL-3.0-only license](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).

## Install and start

Follow the [installation and support guide](https://github.com/TimurMisharin/taxtidy-israel/blob/main/INSTALLATION.md) for your host. Keep the packaged skill resources, license and documentation together. Start a clean conversation, invoke TaxTidy Israel and provide a tax year and goal. Hebrew is the default. Ask for English, Russian or Arabic when preferred. Use the [synthetic demo](DEMO.md) for an example and the [verification notes](VERIFICATION.md) for scope.

> Using fictional data, help me review my Israeli taxes for 2025. Answer in English and start with a document checklist.

Hosts with no compatible private executor can use the checklists and references. Run calculations and inspect PDFs manually with the CLI on a compatible private machine. Review what the host can see or retain before exposing real local files or command output.

## Prepare Python and OCR

Use Python 3.12.14 and single-user POSIX storage. Install the [pinned runtime requirements](skills/taxtidy-israel/requirements.txt) into an isolated environment. From the bundled `skills/taxtidy-israel` directory, run the following with the prepared interpreter.

```sh
python3 -m pip install -r requirements.txt
python3 scripts/taxtidy.py --help
```

For scans, separately provide Tesseract 5.5.4 and the official `heb`, `eng`, `osd` models. Pass absolute paths using `--tesseract` and `--tessdata-dir`. The tested models are from [tessdata_fast revision 87416418657359cb625c412a48b6e1d6d41c29bd](https://github.com/tesseract-ocr/tessdata_fast/tree/87416418657359cb625c412a48b6e1d6d41c29bd), with its Apache-2.0 LICENSE. Models are excluded from the archive. Verify the downloaded bytes before use:

| File | SHA-256 |
|---|---|
| heb.traineddata | 11f9e43ab227f786352a50f75c94c2e9906f1baba86d93276da19da7ce0904db |
| eng.traineddata | 7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2 |
| osd.traineddata | 9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff |
| LICENSE | cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30 |

## Keep cases private

Use an absolute, resolved path with an existing private parent for each new case. Keep cases, original documents and output outside the installed skill, its enclosing checkout and your active workspace. This also applies when the active workspace is outside Git or the skill is globally installed. The CLI blocks cases in the skill, its enclosing plugin and enclosing source checkouts it can identify from the installed script. Use a private shell and `umask 077`.

From the bundled `skills/taxtidy-israel` directory, try the CLI on a fictional case.

```sh
python3 scripts/taxtidy.py init --case-root /absolute/private/new-case --taxpayer-id fictional-taxpayer --years 2025 --language he --synthetic
python3 scripts/taxtidy.py import-evidence --case-root /absolute/private/new-case --input /absolute/private/reviewed-evidence.json
python3 scripts/taxtidy.py calculate --case-root /absolute/private/new-case --tax-year 2025
python3 scripts/taxtidy.py resume --case-root /absolute/private/new-case --language ru
```

Use the [case format](skills/taxtidy-israel/references/case-format.md) to prepare reviewed input. A blank template cannot support an estimate. The [PDF workflow](skills/taxtidy-israel/references/pdf-workflow.md) explains inspection and manual review. Enter an already known PDF password only at the concealed local terminal prompt. Compare the original with the working copy before recording review. Filing requires matched official acknowledgment evidence. The CLI records reviewed evidence locally and ships without a connector.
