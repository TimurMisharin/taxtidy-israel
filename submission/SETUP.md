# TaxTidy Israel

TaxTidy Israel provides checklists, evidence reconciliation and sourced explanations for Israeli taxes. It includes a calculator for limited 2025 cases and PDF/OCR utilities for unencrypted, redacted inputs. Read the [legal notice](LICENSE-NOTICE.md) before installation and the [privacy notice](PRIVACY.md) before sharing information.

## Start with a checklist

Ask “What documents should I gather to review Israeli taxes for 2025?” A tax year and goal are enough to start. The skill defaults to Hebrew and can answer in English, Russian or Arabic. Keep official Hebrew form names alongside translations.

Use fictional examples or the minimum figures from documents you review yourself. Remove identifying details from excerpts outside the plugin before sharing. The skill can explain how to obtain documents and what to check. You handle authenticated accounts, messages, and filing yourself.

## Optional local tools

If you have a private supported local executor, the validated runtime is Python 3.12.14 on single-user POSIX storage. Install the pinned [Python requirements](skills/taxtidy-israel/requirements.txt) in an isolated environment. OCR additionally requires Tesseract 5.5.4 and the official `heb`, `eng` and `osd` models. Set their actual directory using `--tessdata-dir`. See the [case format](skills/taxtidy-israel/references/case-format.md) and [PDF checks](skills/taxtidy-israel/references/pdf-workflow.md).

Use case aliases and a private directory outside the source checkout. Keep originals outside the plugin workflow. From the skill directory, run `python3 scripts/taxtidy.py --help` for commands. Without the local environment, use the checklists and reconcile documents manually.

For software support, use [TaxTidy Israel GitHub Issues](https://github.com/TimurMisharin/taxtidy-israel/issues) with fictional test data only.
