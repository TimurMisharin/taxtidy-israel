[English](README.md) · [עברית](README.he.md) · [Русский](README.ru.md) · [العربية](README.ar.md)

# TaxTidy Israel

**Make sense of your Israeli tax documents, one reviewed step at a time.**

![Documents move through review into a conditional estimate and a next-step checklist.](assets/overview.svg)

A ChatGPT plugin for organizing Israeli tax documents, finding missing information, and preparing **narrowly supported 2025 tax refund or balance-due estimates**. Hebrew is the default language, with multilingual tax assistance, including Russian and Arabic.

**Version 0.1.0 · Open source under AGPL-3.0-only**

## Who it helps

People checking Israeli employment income and related tax records who want a clear document checklist and an explanation of what remains unresolved. Complex cases can still receive collection and research guidance; a complete numerical estimate requires every material fact to fall within supported coverage.

## What you provide

- The tax year, your question, and relevant personal eligibility facts.
- **Form 106** from each employer: the annual certificate showing pay and tax withheld. Bank tax certificates, donation receipts and benefit statements may also be relevant.
- Reviewed documents or manually collected information. Missing information stays unknown; it is not silently treated as zero.

**OCR** means recognizing text in scanned images. Hebrew OCR can misread years, minus signs and blank fields, so a person must compare the original document with the extracted information before it is used.

## Get started

1. Read the [setup guide](taxtidy-israel/SETUP.md). The plugin instructions and local Python/OCR runtime are separate: importing a plugin does not install its runtime or connect accounts.
2. Obtain the portable plugin ZIP and checksum from [release v0.1.0](https://github.com/TimurMisharin/taxtidy-israel/releases/tag/v0.1.0). GitHub's automatic source ZIP contains the development repository and is a different download.
3. Use a ChatGPT environment that supports this package format and, for executable utilities, the required local runtime. **Host installation/import/discovery has not been tested.** Follow your host's verified instructions; this repository does not establish that a particular import method works.
4. Start with: “Help me check my 2025 Israeli tax documents. Explain what is missing before estimating a refund.” Keep local cases outside the entire source checkout. Never post taxpayer records or credentials in GitHub issues or PRs.

A host without local execution can use the guidance and templates, but cannot claim to have run Python or OCR. No mailbox, bank or Tax Authority account access is bundled.

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
