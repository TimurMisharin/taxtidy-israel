[English](README.md) · [עברית](README.he.md) · [Русский](README.ru.md) · [العربية](README.ar.md)

# TaxTidy Israel

TaxTidy Israel is an open-source ChatGPT and Codex plugin for reviewing Israeli tax records. Start with a tax year and a goal. The plugin helps you collect the right documents, reconcile income and withholding, and identify the evidence still needed to choose a filing route.

**[Download TaxTidy Israel 0.1.5](https://github.com/TimurMisharin/taxtidy-israel/releases/tag/v0.1.5)** · [Setup and local tools](taxtidy-israel/SETUP.md) · [Privacy](PRIVACY.md)

## Before installing

TaxTidy Israel is provided as is. It does not replace tax, legal, financial, accounting, or other professional advice. Liability for losses is limited to the extent permitted by applicable law. Choosing to install or activate the plugin after the notice has been made available in advance constitutes acceptance of its terms, subject to applicable law. [Legal notice and limitation of liability](taxtidy-israel/LICENSE-NOTICE.md)

## What you can review

- Employer certificates (**טופס 106**), payslips, withholding, and Section 46 donation evidence. Check which figures match and which require a document or clarification.
- Annual return and refund routes for each tax year. For married spouses, version 0.1.5 distinguishes a joint return, separate tax calculation, and verified separate submissions. It checks recorded **טופס 4430** elections for the applicable year and handles written directions to correct a return already on file.
- Filing progress. Check the evidence for a draft, a filing acknowledgment, a received attachment, a correction, or an assessment. You handle signing and filing.
- Optional PDF review, Hebrew and English OCR, and an illustrative calculator for **supported 2025 cases**. These tools require a compatible private Python/POSIX runtime. [Capabilities and limits](taxtidy-israel/VERIFICATION.md)

## Install or download

| Where you want to use it | How to get started |
| --- | --- |
| **ChatGPT desktop on macOS or Windows** | Add the repository marketplace using Codex CLI, then install TaxTidy Israel from **Plugins** in the desktop app. Native Windows calculator and OCR execution have not been validated. |
| **ChatGPT web, Linux, or mobile** | Use the **Plugins** directory if TaxTidy Israel is available in your eligible workspace or catalog. A workspace admin can import the GitHub marketplace and make it available. |
| **Portable package** | Download `taxtidy-israel-0.1.5.zip` and its `.sha256` file from the release. Follow the included setup guide for local tools. |
| **OpenAI directory submission** | Download `taxtidy-israel-0.1.5-openai.zip` and its `.sha256` file. The ZIP is prepared for a separate submission, review, and publication process. |

For the desktop marketplace, install and sign in to Codex CLI, then run:

```sh
codex plugin marketplace add TimurMisharin/taxtidy-israel --ref v0.1.5
```

Restart ChatGPT desktop, open **Plugins**, and install **TaxTidy Israel** from the marketplace. A workspace admin can instead open **Admin → Plugins → Add → Import marketplace**, set the source to `https://github.com/TimurMisharin/taxtidy-israel`, leave **Path** blank, and configure member access after the import. [Desktop marketplace instructions](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli) · [Managed workspace import](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github)

## Start a review

Open a new chat, select **@TaxTidy Israel**, and try:

> Help me review my 2025 Israeli taxes. Answer in English. Give me a document checklist and tell me what would verify my filing route.

Hebrew is the default. English, Russian, and Arabic are also supported. Use fictional examples or redacted excerpts in chat, and keep originals and private case records outside the repository. [Synthetic demo](taxtidy-israel/DEMO.md) · [Privacy](PRIVACY.md)

## Project links

[Development and packaging](DEVELOPMENT.md) · [Contributing](CONTRIBUTING.md) · [Report an issue](https://github.com/TimurMisharin/taxtidy-israel/issues) · [AGPL-3.0-only](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)
