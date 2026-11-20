# TaxTidy Israel 0.1.1 setup

Install the existing TaxTidy Israel plugin from its GitHub repository marketplace. You do not need to create another plugin or upload a ZIP to Plugin Creator.

Original project materials are [AGPL-3.0-only](LICENSE), allowing commercial use subject to the license's source-sharing and notice obligations. [Third-party notices](THIRD_PARTY_NOTICES.md) cover separately licensed dependencies.

## Add the repository marketplace and install

Repository URL:

```text
https://github.com/TimurMisharin/taxtidy-israel
```

### ChatGPT desktop app

If your Plugins screen offers adding a repository marketplace, enter the URL above. Menu wording and availability depend on your host; no specific add-repository button has been verified for this release.

The documented registration route below requires the **Codex CLI already installed**. Run it once in a terminal:

```sh
codex plugin marketplace add TimurMisharin/taxtidy-israel
```

Restart the ChatGPT desktop app. Open **Plugins**, select the **TaxTidy Israel** marketplace, open the **TaxTidy Israel** plugin and install it. See [OpenAI's repository marketplace instructions](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli).

If the marketplace or plugin does not appear, stop and check the registration result, host support and workspace policy. Do not create a replacement plugin. This distribution is a repository marketplace, not a listing in OpenAI's universal public catalog. It is not available through every personal ChatGPT web account.

### Workspace-admin GitHub import (separate option)

This route requires a workspace administrator. In ChatGPT, open **Admin > Plugins > Add > Import marketplace**. Set **Source** to the repository URL above, leave **Path** empty, and leave the branch field empty for the default branch (`main`) or enter `main`. Import, review results and make TaxTidy Israel available for installation. Members then install it from their workspace's Plugins directory. Follow [OpenAI's GitHub import guide](https://learn.chatgpt.com/docs/enterprise/plugin-management) for GitHub authorization and workspace access requirements.

### Start your first conversation

1. Start a **new chat** after installation.
2. Type **@**, search for **TaxTidy Israel** and select the installed plugin.
3. Send:

> Help me review my Israeli taxes for 2025. Answer in English. Ask about my situation and give me a document checklist first. Explain what is missing before estimating a refund.

Change the answer language as needed; Hebrew is the default. Supply requested documents privately, including Form 106 from each employer where relevant. Compare extracted figures with originals and clarify missing or conflicting information. Then ask for a supported estimate, its assumptions, unresolved questions and next steps. No return is filed automatically.

### Guidance versus execution

Installation provides the skill, references, templates and bundled scripts. It does not install Python/OCR dependencies, connect accounts or grant file access. A host without execution can provide guidance and document checklists, but must not claim that it ran the local calculator or OCR. For those utilities, prepare the runtime below. Host discovery/installation and the full conversational workflow have not yet been verified for this release; package checks alone do not prove them. The [demo](DEMO.md) is a synthetic local-utility demonstration, not a host installation recording.

Portable ZIP/checksum release assets are an optional separate distribution, not required for the repository-marketplace route. GitHub's automatic source archive is the development repository. Keep the package's license and notices with any standalone copy.

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
