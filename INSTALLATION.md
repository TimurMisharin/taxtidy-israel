# Install and use TaxTidy Israel

**Before installation or activation, read the [bilingual legal notice](taxtidy-israel/LICENSE-NOTICE.md).** TaxTidy is a general-purpose aid provided as is. It does not replace tax, legal, financial, accounting, or other professional advice. Keep the [license](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md) with redistributed copies.

## Choose a package

| Package | Intended use |
| --- | --- |
| Agent Plugin ZIP | Codex/ChatGPT repository catalog or a host that accepts the Agent Plugin format. The extracted plugin root contains `plugin.json` and `skills/taxtidy-israel/`. |
| OpenAI public ZIP | OpenAI directory submission and the proposed private Perplexity Computer plugin pilot. The wrapped plugin includes OpenAI listing metadata and the public-use policy. |
| Local standalone skill ZIP | Direct folder installation in coding agents. Extract the single `taxtidy-israel/` folder, which contains `SKILL.md`, the CLI and local setup. |
| Hosted standalone skill ZIP | Claude.ai upload or another compatible hosted pilot. The skill uses the public-use policy, includes the privacy notice and rejects encrypted PDFs. |

Use the ZIP and its matching SHA-256 sidecar from a reviewed [GitHub release](https://github.com/TimurMisharin/taxtidy-israel/releases) that lists the intended package. To try an unreleased build, follow the [development commands](DEVELOPMENT.md). On macOS, run `shasum -a 256 -c <package>.sha256` from the download directory. GitHub's generated source archives contain the development tree.

## Local host routes

Copy the entire extracted standalone folder into the chosen skill directory. A project path is relative to the project root. Enable only the route you are testing to avoid duplicate discovery. Reload the host and select or explicitly invoke the installed skill. Verification details and outstanding pilot results are in [Verification](VERIFICATION.md).

| Host | Installation route |
| --- | --- |
| Codex | Standalone folder in `.agents/skills/`. For the separate catalog route run `codex plugin marketplace add TimurMisharin/taxtidy-israel --ref <reviewed-tag>` and `codex plugin add taxtidy-israel@taxtidy-israel`. [Skill docs](https://learn.chatgpt.com/docs/build-skills) |
| Cursor desktop | Standalone folder in `.cursor/skills/` or `.agents/skills/`. For the plugin pilot, import the Agent Plugin from disk or copy its extracted root into `~/.cursor/plugins/local/taxtidy-israel`, where allowed. Reload and inspect **Customize**. Cloud Agents need a separate test. [Plugins](https://cursor.com/docs/plugins) · [Skills](https://cursor.com/docs/skills) |
| Claude Code | Standalone folder in `.claude/skills/`. For a session-only plugin pilot, pass the extracted Agent Plugin root to `claude --plugin-dir <plugin-root>`. Claude Code loaded its default skill directory in the pilot. Its native manifest validator requires Claude-specific metadata for native distribution. [Skills](https://code.claude.com/docs/en/skills) |
| Grok Build | Standalone folder in `.grok/skills/` or `~/.grok/skills/`. Check discovery in `/skills`. [Skill docs](https://docs.x.ai/build/features/skills-plugins-marketplaces) |
| VS Code with Copilot | Standalone folder in `.github/skills/`. [Skill docs](https://code.visualstudio.com/docs/agent-customization/agent-skills) |
| OpenCode | Standalone folder in `.opencode/skills/`. [Skill docs](https://opencode.ai/docs/skills/) |
| Cline | Standalone folder in `.cline/skills/`. [Skill docs](https://docs.cline.bot/customization/skills) |

Google Antigravity CLI and Devin Local remain candidates for standalone discovery. Consult their [Antigravity migration guide](https://antigravity.google/docs/cli/gcli-migration) and [Devin Local customization guide](https://docs.devin.ai/desktop/devin-local/customizations) before piloting.

Local calculation and PDF review require Python 3.12.14, pinned dependencies and single-user POSIX storage. OCR also requires Tesseract 5.5.4 and the pinned `heb`, `eng` and `osd` models. Keep cases and output outside the installed skill, enclosing checkout and active workspace. Review what the host can see and retain before exposing real case data. Where host execution is unavailable, follow the checklists in the host and run the CLI manually on a compatible private machine. [Local setup](taxtidy-israel/SETUP.md)

## Hosted and ChatGPT routes

Use fictional inputs in every hosted pilot. Later use requires affirmative redaction confirmation and only the minimum necessary data. Any PDF must be unencrypted. The taxpayer retrieves records, operates authenticated accounts, sends messages and files. [Privacy notice](PRIVACY.md)

| Host | Pilot or installation route |
| --- | --- |
| Claude.ai | Enable code execution and file creation. Upload the hosted standalone ZIP in **Customize → Skills** and check the enabled skill and a bundled reference. [Custom skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills) |
| Perplexity Computer | Privately try the public wrapper under **Plugins → Add custom → Upload plugin or skill** when your plan and workspace permit. The documentation expects a root or recognized manifest location, so verify whether the enclosing folder is accepted. The standalone fallback requires `SKILL.md` at the ZIP root and is conditional on the wrapped pilot. [Plugin upload](https://www.perplexity.ai/help-center/en/articles/2026100802-create-or-upload-a-custom-plugin) · [Standalone intake](https://www.perplexity.ai/help-center/en/articles/13914413-how-to-use-computer-skills) |
| Grok web, iOS and Android | Use the host's custom skill editor with public instructions and a supported attachment. Check each surface separately for reference access before making claims about the guidance pilot. [Grok Skills](https://x.ai/news/grok-skills) |
| ChatGPT | Where available, register the repository marketplace with the Codex CLI command above, restart ChatGPT desktop and install from **Plugins**. A workspace administrator can import the GitHub repository through **Admin → Plugins → Add → Import marketplace**. Enter the repository URL and leave the path empty. For public directory distribution, use the vetted OpenAI ZIP and the separate directory review. [Workspace import](https://learn.chatgpt.com/docs/enterprise/plugin-management) · [Directory submission](https://developers.openai.com/plugins/deploy/submission) |

Start a new session with a synthetic tax year and goal. Ask the host to use TaxTidy, read its bundled routing reference, and explain what facts a fictional married taxpayer would need to verify before considering separate submissions. Continue in Russian or English and ask it to preserve the Hebrew form and portal labels. If it cannot browse, it should identify the official year-specific publication the taxpayer needs.

## Upgrade, rollback and support

1. Verify the new ZIP and keep the previous verified artifact and checksum. Record the installed route and tested version.
2. Copy an existing synthetic schema-v1 case to a private test location, retaining restrictive permissions and all related files. Preserve the original case.
3. Apply the new install in a clean session and resume against one copy. Check the revision, estimate freshness and filing evidence. Switch back to the previous artifact and repeat on a checkpoint copy before replacing a real install.
4. If the old build cannot load an updated copy, keep the original checkpoint with its original verified version.

Use [GitHub Issues](https://github.com/TimurMisharin/taxtidy-israel/issues) for software support. Include the host and version, package checksum, install route, exact error and a fictional reproduction.
