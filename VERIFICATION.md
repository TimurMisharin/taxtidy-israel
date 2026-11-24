# TaxTidy verification record

## Cross-agent candidate 0.1.6

Verification ran on 24 November 2026 using the [reviewed main snapshot 7f167d6](https://github.com/TimurMisharin/taxtidy-israel/commit/7f167d6ae3ad4332117146d9b12e35b3d746ad09) plus the cross-agent changes. [GitHub release v0.1.5](https://github.com/TimurMisharin/taxtidy-israel/releases/tag/v0.1.5) was the latest published release. OpenAI Platform listed 0.1.5 as unpublished with review status “Needs attention.” Version 0.1.6 is a local candidate pending review, tagging and publication.

The full suite passed all 78 tests and the separate nine-case synthetic acceptance suite passed. Compilation, Ruff lint and formatting, the package and four archive validators all passed. The macOS arm64 test environment used Python 3.12.14, Ruff 0.17.6, the pinned Python distributions and Tesseract 5.5.4 with the [verified model hashes](taxtidy-israel/SETUP.md). Two builds of every ZIP matched byte for byte, and all checksum sidecars verified.

| Candidate ZIP | Files | Compressed bytes | Uncompressed bytes | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `taxtidy-israel-0.1.6.zip` | 28 | 106,033 | 319,461 | `417ef4f3ed72937458d46eebd5ef5eb995593a9a5f2a59acfd0b827b71288772` |
| `taxtidy-israel-0.1.6-openai.zip` | 27 | 114,362 | 326,024 | `be49826135f56c1b33832a0f47c8c48818769cbc628572a36a00a72f48ef745b` |
| `taxtidy-israel-0.1.6-skill-local.zip` | 27 | 103,769 | 316,906 | `4cbd9bd35bec514f9d482b2cb8d68cceac35e9ddd3c42824f6bfee22a22da3f5` |
| `taxtidy-israel-0.1.6-skill-hosted.zip` | 25 | 99,252 | 308,482 | `c8b290f5cdc234f90f8cbd2db6e67839e156b91b36ab491371e12493fb970e3a` |

### Installed artifacts and hosts

Both standalone ZIPs ran from isolated extraction directories with the prepared interpreter and synthetic inputs. Using [the reviewed wage fixture](tests/fixtures/cases.json), each returned the 2025 baseline refund estimate of ILS 5,098.80, suppressed missing/conflicting figures, and reported the unsupported 2024 year. The unencrypted PDF fixture preserved the original hash and required manual review. The scanned Hebrew/English fixture produced OCR text for manual verification. Both public ZIPs rejected synthetic encrypted PDFs, including empty-password encryption, with no document retained and no revision change.

| Host or runtime | Install route | Discovery | Reference access | Guidance | Estimate | PDF review | OCR | Resume |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Python 3.12.14 on macOS arm64 | Isolated local and hosted standalone ZIPs | Not applicable | Pass, archive links | Not tested | Pass | Pass | Pass | Pass |
| Codex CLI 0.171.0-alpha.13.2 | Extracted local standalone in `.agents/skills/` | Pass | Pass, installed file | Not tested | Not tested | Not tested | Not tested | Not tested |
| Codex CLI 0.171.0-alpha.13.2 | Local repository catalog and cached Agent Plugin | Pass | Pass, installed file | Not tested | Not tested | Not tested | Not tested | Not tested |
| Claude Code 2.1.150 | Extracted local standalone in `.claude/skills/` | Pass | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested |
| Claude Code 2.1.150 | Extracted Agent Plugin through `--plugin-dir` | Pass | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested |
| Claude.ai, Perplexity Computer, Grok web | Hosted skill or public wrapper | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested |
| Cursor desktop and Cloud Agents, Grok Build | Plugin or standalone | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested |
| ChatGPT desktop, web and mobile | Repository or OpenAI directory | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested |
| Grok iOS and Android | Custom skill | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested |
| VS Code Copilot, OpenCode, Cline, Antigravity CLI, Devin Local | Standalone | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested |

For Codex, the CLI reported the enabled skill and the bundled spouse-routing reference was readable from the resolved installation. For Claude Code, the loader found one skill in each test, and invocation stopped at sign-in. The native manifest validator failed on the existing Agent Plugin because it expects Claude-specific metadata. Claude.ai, Perplexity Computer, Grok web and Copilot in VS Code 1.147.0 were signed out. The Perplexity upload therefore has no acceptance result. Its compressed, uncompressed and file-count ceilings were checked locally. Refer to [installation and support](INSTALLATION.md) for each pilot procedure.

### Upgrade and rollback

The downloaded 0.1.5 Agent Plugin and OpenAI ZIPs matched the two ZIP hashes on the [published release page](https://github.com/TimurMisharin/taxtidy-israel/releases/tag/v0.1.5). Each paired 0.1.6 standalone package reopened a private schema-v1 copy and reproduced the pre-existing estimate. After a conflicting Form 106 import invalidated that estimate, both the 0.1.6 install and its paired 0.1.5 artifact resumed the updated copy at the recorded revision without a current estimate. Original checkpoint bytes were preserved.

## Interpreting the results

The calculator's coverage is limited to the documented 2025 profiles. The earlier public simulator wage-only trial differed from the exact-decimal result by ILS 0.20. Production signature trust and recipient acceptance require independent verification. In an earlier OCR trial a Hebrew scan read 2005 in place of 2025. Check each material field on the source. The tests used synthetic cases throughout. See [local workflow limits](taxtidy-israel/VERIFICATION.md) and the [synthetic demo](taxtidy-israel/DEMO.md).
