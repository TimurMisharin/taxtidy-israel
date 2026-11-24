# TaxTidy Israel public setup

**Before installation or activation, read the [bilingual legal notice](../taxtidy-israel/LICENSE-NOTICE.md).** TaxTidy is a general-purpose aid provided as is. It does not replace tax, legal, financial, accounting, or other professional advice. See the [privacy notice](../PRIVACY.md), [AGPL-3.0-only license](../taxtidy-israel/LICENSE) and [third-party notices](../taxtidy-israel/THIRD_PARTY_NOTICES.md).

## Start with a year and a goal

Ask “What documents should a fictional taxpayer gather to review their 2025 Israeli taxes?” Hebrew is the default. You can ask for English, Russian or Arabic. Keep official Hebrew labels alongside translations.

Use fictional data in hosted pilots. In later authorized use, share manually extracted totals and aliases first. Share the minimum financial excerpt or file only after removing identifiers, account numbers, signatures, barcodes and other unrelated details, including underlying PDF text and metadata. Affirm that you have redacted the material before asking TaxTidy to process it. Any PDF must be unencrypted. Keep original documents and credentials private.

The taxpayer retrieves records, handles authenticated accounts, sends messages and files through official channels. The assistant can explain public criteria and prepare checklists and drafts. Case-specific filing decisions require verification with the Israeli Tax Authority or a qualified professional.

## Optional private execution

Where private local execution is available, use Python 3.12.14 on single-user POSIX storage and the [pinned requirements](../taxtidy-israel/skills/taxtidy-israel/requirements.txt). OCR requires Tesseract 5.5.4 and the official `heb`, `eng` and `osd` models. See the [case format](../taxtidy-israel/skills/taxtidy-israel/references/case-format.md) and [PDF review procedure](../taxtidy-israel/skills/taxtidy-israel/references/pdf-workflow.md).

Use aliases and a private directory outside the installed skill, any enclosing checkout and the active workspace. From the bundled `skills/taxtidy-israel` directory, run `python3 scripts/taxtidy.py --help`. If you have no compatible executor with private storage, follow the checklists and reconcile the evidence manually.

Use fictional examples when reporting a software issue. [TaxTidy Israel GitHub Issues](https://github.com/TimurMisharin/taxtidy-israel/issues)
