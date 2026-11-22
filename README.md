[English](README.md) · [עברית](README.he.md) · [Русский](README.ru.md) · [العربية](README.ar.md)

# TaxTidy Israel

TaxTidy Israel is an open-source ChatGPT plugin for reviewing Israeli tax records. It helps you choose a route for each year, reconcile salary and withholding, check Section 46 donations, and identify the evidence needed to confirm a filing. The bundled calculator supports a limited set of **2025** cases.

**Version 0.1.2** · [GitHub release and checksum](https://github.com/TimurMisharin/taxtidy-israel/releases/tag/v0.1.2) · [AGPL-3.0-only](LICENSE)

## Install by platform

| Platform | Installation |
| --- | --- |
| **ChatGPT on macOS** | Install [ChatGPT desktop](https://chatgpt.com/download/), then follow the [repository marketplace steps](#repository-marketplace-on-desktop). |
| **ChatGPT on Windows** | Install [ChatGPT desktop](https://chatgpt.com/download/), then follow the same [marketplace steps](#repository-marketplace-on-desktop) in PowerShell. The native Windows calculator and OCR runtime have not been validated. |
| **Linux** | Open [ChatGPT in your browser](https://chatgpt.com/) and use the web instructions below. OpenAI's native ChatGPT desktop downloads cover macOS and Windows. Codex CLI can register the repository, but that does not give the browser access to it. |
| **ChatGPT web** | Open **Plugins** in the sidebar. If your workspace admin has [imported the GitHub marketplace](#managed-chatgpt-workspaces), select the workspace directory, search for **TaxTidy Israel**, and choose **Install plugin** when offered. |
| **ChatGPT on iPhone or Android** | Install or update the official [ChatGPT mobile app](https://chatgpt.com/download/). Sign in to your eligible workspace, open **Plugins**, search for **TaxTidy Israel** and choose **Install plugin** when offered. The plugin must be visible in that workspace or in the public directory. |

**Public ChatGPT directory status:** The GitHub release provides the portable package. Public listing in ChatGPT requires [OpenAI submission, review and publication](https://developers.openai.com/plugins/deploy/submission). Until then, personal web and mobile accounts cannot install this GitHub release from the public directory. Workspace, plan and region can affect access. [OpenAI plugin availability](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt)

### Repository marketplace on desktop

1. Install and sign in to [Codex CLI](https://learn.chatgpt.com/docs/codex/cli). Run this in Terminal on macOS or PowerShell on Windows:

   ```sh
   codex plugin marketplace add TimurMisharin/taxtidy-israel
   ```

2. Restart the ChatGPT desktop app. Open **Plugins**, select the **TaxTidy Israel** marketplace, open **TaxTidy Israel**, and choose **Install plugin**.
3. If the marketplace is missing, check that the command succeeded and your desktop client and workspace allow local marketplaces. [OpenAI marketplace instructions](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli)

### Managed ChatGPT workspaces

A workspace admin opens **Admin → Plugins → Add → Import marketplace**, enters `https://github.com/TimurMisharin/taxtidy-israel` as **Source**, leaves **Path** blank, and leaves the Git reference blank to follow `main`. Authorize GitHub access if prompted, review the import, then make TaxTidy Israel available for members to install. [OpenAI workspace import guide](https://learn.chatgpt.com/docs/enterprise/plugin-management)

## Start a case

1. Start a new chat and select **@TaxTidy Israel**. Hebrew is the default. You can ask in English, Russian or Arabic.
2. Name the tax year and goal. For example: “Help me review my 2025 Israeli taxes. Answer in English. Start with the documents I need and what they establish.”
3. Review the original documents the plugin requests, such as **טופס 106** (Form 106), bank certificates, and donation receipts. Ask which items are reconciled, which are missing, and which official step is next.

Chat guidance can work without a local executor. The **2025** calculator and PDF/OCR tools require a compatible private Python/POSIX runtime with separate dependencies. Review extracted amounts against the originals. The plugin neither connects to your tax account by default nor files returns. Keep case records and credentials out of GitHub. [Runtime and setup](taxtidy-israel/SETUP.md)

## Project resources

- [Synthetic example](taxtidy-israel/DEMO.md) · [Verified capabilities and limits](taxtidy-israel/VERIFICATION.md)
- [Development and packaging](DEVELOPMENT.md) · [Report an issue](https://github.com/TimurMisharin/taxtidy-israel/issues) · [Third-party notices](THIRD_PARTY_NOTICES.md)
