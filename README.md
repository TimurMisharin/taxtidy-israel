[English](README.md) · [עברית](README.he.md) · [Русский](README.ru.md) · [العربية](README.ar.md)

# TaxTidy Israel

**Make sense of your Israeli tax documents, one reviewed step at a time.**

![Documents move through review into a conditional estimate and a next-step checklist.](assets/overview.svg)

A ChatGPT plugin for organizing Israeli tax documents, finding missing information, and preparing **narrowly supported 2025 tax refund or balance-due estimates**. Hebrew is the default language, with multilingual tax assistance, including Russian and Arabic.

**Version 0.1.2 · Open source under AGPL-3.0-only**

## Who it helps

People checking Israeli employment income and related tax records who want a clear document checklist and an explanation of what remains unresolved. Complex cases can still receive collection and research guidance; a complete numerical estimate requires every material fact to fall within supported coverage.

## What you provide

- The tax year, your question, and relevant personal eligibility facts.
- **Form 106** from each employer: the annual certificate showing pay and tax withheld. Bank tax certificates, donation receipts and benefit statements may also be relevant.
- Reviewed documents or manually collected information. Missing information stays unknown; it is not silently treated as zero.

**OCR** means recognizing text in scanned images. Hebrew OCR can misread years, minus signs and blank fields, so a person must compare the original document with the extracted information before it is used.

## Install from this repository

Add this repository as a **plugin marketplace**, then install **TaxTidy Israel** from that marketplace:

```text
https://github.com/TimurMisharin/taxtidy-israel
```

For the **ChatGPT desktop app**, if your Plugins screen offers adding a repository marketplace, use that URL. The documented command-line registration route requires the **Codex CLI**:

```sh
codex plugin marketplace add TimurMisharin/taxtidy-israel
```

Then restart the ChatGPT desktop app, open **Plugins**, choose the **TaxTidy Israel** marketplace, open **TaxTidy Israel**, and install it. This installs the existing repository plugin. You do not need to create a new plugin or upload the ZIP. Repository marketplaces depend on the host; this is not an installation route for every personal ChatGPT web account. See [setup](taxtidy-israel/SETUP.md) for the separate workspace-admin GitHub import route and [OpenAI's marketplace guide](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli).

## Use it in a new chat

1. Start a **new chat** after installation.
2. Type **@**, search for **TaxTidy Israel**, and select the installed plugin.
3. Send this first message (change the language as desired):

> Help me review my Israeli taxes for 2025. Answer in English. Ask about my situation and give me a document checklist first. Explain what is missing before estimating a refund.

4. Provide the requested documents in that private conversation, such as **Form 106 (טופס 106)** from each employer. Review extracted figures against the originals and resolve missing or conflicting information.
5. Ask: “What can you estimate from the reviewed information, what remains unsupported, and what should I do next?”

The plugin gives guidance, checklists and explanations. Executing its bundled calculator or OCR requires a separately prepared Python/OCR runtime; installation does not install those dependencies or connect accounts. A host without execution can use the guidance but must not claim to have run the utilities. Keep local cases outside the entire checkout and never post taxpayer records or credentials in GitHub issues or PRs.

**Verification:** package/catalog checks are separate from actual host installation, which remains unverified until a successful marketplace install is observed. The [v0.1.2 ZIP and checksum](https://github.com/TimurMisharin/taxtidy-israel/releases/tag/v0.1.2) are optional portable release assets, not the marketplace installation step.

## What happens next

TaxTidy helps identify documents, reconcile duplicate or conflicting records, and prepare a list of missing evidence. Supported calculations show assumptions and an estimate; unsupported material facts block a complete result. You then review the documents and choose the appropriate official process, with professional help where needed. **No return is filed automatically.** A saved draft or accepted attachment does not mean a return was submitted.

See the [written synthetic demonstration](taxtidy-israel/DEMO.md) and [verification summary](VERIFICATION.md).

## Current limits

Numerical support is limited to reviewed 2025 resident wage profiles and specific supported donations, domestic securities, employee reserve payments and conditional assistance scenarios. Foreign income, general equity taxation, business/rental/retirement cases, special ownership and higher-income surcharge cases are outside numerical coverage. See [detailed scope](taxtidy-israel/VERIFICATION.md).

Estimates are **not filing-ready**, statutory rounding remains unresolved, and refunds are never guaranteed. Documents need manual review; production PDF signatures are not authenticated by the synthetic tests. Future-year research can revisit official Israeli legislation and rules, but **does not implement or validate calculations for another year**. There is no official endorsement.

## Questions people ask

**Is this a standalone tax application?** It is a ChatGPT plugin with guidance, templates and bundled local utilities. The separately required runtime is described in setup.

**Can I use it for another year?** Collection and official-rule research can help. Numerical validation currently covers only the documented 2025 cases; 2025 values must not be reused for another year.

**Will it log in or file for me?** No account integration or automatic filing is bundled. This publication does not validate installation, login, document submission or filing.

**Can I use it commercially for free?** Yes, under [AGPL-3.0-only](LICENSE). You may use, modify and redistribute the original project materials, including commercially, subject to its notices and source-sharing requirements, including applicable modified network use. It comes without warranty. [Third-party licenses](THIRD_PARTY_NOTICES.md) remain separate, including PyMuPDF's AGPL/commercial terms.

## Official sources and project links

- [Tax Authority: tax refund application, Form 135](https://www.gov.il/en/service/itc135).
- [Tax Authority: annual return for 2025, Form 1301](https://www.gov.il/he/service/reporting-and-payment-2025-annual-tax-report-for-individuals).
- [Year-specific rule references](taxtidy-israel/skills/taxtidy-israel/references/tax-rules.md), [setup](taxtidy-israel/SETUP.md), [demo](taxtidy-israel/DEMO.md), [verification](VERIFICATION.md), [license](LICENSE).
- [Contribute or report a problem](CONTRIBUTING.md) · [Development](DEVELOPMENT.md).

Official service pages describe filing routes, not a certification of this plugin. Check the exact year and circumstances before acting.
