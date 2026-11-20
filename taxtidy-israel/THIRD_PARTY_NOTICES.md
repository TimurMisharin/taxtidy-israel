# Third-party notices

Original TaxTidy Israel code, documentation and original overview illustration are licensed under AGPL-3.0-only; see LICENSE. Third-party materials retain their own terms. No project license grants a commercial PyMuPDF license or overrides another component's obligations.

## What is distributed

The portable plugin contains original source, references, blank templates, documentation, LICENSE and these notices. It includes no Python dependency wheels, native binaries, OCR models, signing keys or taxpayer documents. The source repository additionally includes an unmodified Noto Sans Hebrew test font and its complete `tests/resources/hebrew-font-license.txt`; those test resources are not in the plugin ZIP.

The test font is Copyright 2018 The Noto Project Authors, under SIL Open Font License 1.1. Preserve its license and notices when redistributing it; do not sell the font by itself or relicense it under AGPL. [Font source and license at the reviewed revision](https://github.com/notofonts/noto-fonts/tree/ffebf8c1ee449e544955a7e813c54f9b73848eac).

## Separately installed runtime

PyMuPDF 2.1 (including its underlying MuPDF and integrated layout/LLM code) offers GNU AGPLv3 or Artifex commercial licensing. This project uses the open-source terms and supplies no commercial license. Free commercial use under AGPL is subject to its obligations; proprietary redistribution or hosted modifications may require a different licensing decision. Review the [upstream licensing documentation](https://pymupdf.readthedocs.io/en/latest/about.html) and the actual dependency's COPYING and bundled notices.

The installed `pymupdf-layout` and `pymupdf4llm` 2.1 distributions contain compatibility metadata rather than separate code. Their empty license metadata is not a grant of additional rights. The [layout package description](https://pypi.org/project/pymupdf-layout/) and [upstream LLM repository](https://github.com/pymupdf/PyMuPDF4LLM) explain migration into PyMuPDF 2.x.

Tesseract 5.5.4 and the tested `heb`, `eng`, `osd` tessdata_fast models are separately provided under Apache-2.0, with their own notices and dependencies. Neither is bundled. [Model source and LICENSE at the reviewed revision](https://github.com/tesseract-ocr/tessdata_fast/tree/87416418657359cb625c412a48b6e1d6d41c29bd). Setup records model hashes. Python and operating-system components also retain their own licenses.

## Reviewed development environment

The table records the installed versions and declared licenses reviewed on 2026-11-20, including the locked transitive environment. These packages are **not redistributed** in this repository or plugin ZIP. A declaration is a summary; the upstream license files, notices and licenses of bundled subcomponents govern. In particular, NumPy, cryptography, ONNX Runtime and tooling can include additional notices. Retain those when separately distributing an environment. No universal compatibility certification for other packaging or deployment models is made.

| Distribution | Reviewed version | License declaration / boundary |
|---|---|---|
| aiohappyeyeballs | 2.7.1 | PSF-2.0 |
| aiohttp | 3.14.5 | Apache-2.0 AND MIT |
| aiosignal | 1.4.0 | Apache 2.0 |
| asn1crypto | 1.5.1 | MIT |
| attrs | 26.1.0 | MIT |
| boolean-py | 5.0 | BSD-2-Clause |
| cachecontrol | 0.15.0 | Apache-2.0 |
| certifi | 2026.10.23 | MPL-2.0 |
| cffi | 2.1.1 | MIT-0 |
| charset-normalizer | 3.5.2 | MIT |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| cyclonedx-python-lib | 11.12.0 | Apache-2.0 |
| defusedxml | 0.7.1 | PSF license |
| filelock | 4.2.12 | MIT |
| flatbuffers | 25.12.19 | Apache-2.0 (metadata) |
| frozenlist | 1.8.0 | Apache-2.0 |
| idna | 3.20 | BSD-3-Clause |
| license-expression | 30.4.4 | Apache-2.0 |
| lxml | 6.1.3 | BSD-3-Clause |
| markdown-it-py | 4.3.0 | MIT |
| mdurl | 0.1.2 | MIT |
| msgpack | 1.2.4 | Apache-2.0 |
| multidict | 7.2.1 | Apache-2.0 |
| networkx | 3.7 | BSD-3-Clause |
| numpy | 2.5.5 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| onnxruntime | 1.32.0 | MIT and bundled third-party notices |
| oscrypto | 1.3.0 | MIT |
| packageurl-python | 0.17.6 | MIT (metadata) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pillow | 13.0.0 | MIT-CMU |
| pip | 26.3 | MIT |
| pip-api | 0.0.35 | Apache-2.0 |
| pip-audit | 2.10.1 | Apache-2.0 |
| pip-requirements-parser | 32.0.1 | MIT |
| platformdirs | 4.14.7 | MIT |
| propcache | 0.5.4 | Apache-2.0 |
| protobuf | 7.36.2 | BSD-3-Clause |
| psutil | 7.2.2 | BSD-3-Clause |
| py-serializable | 2.2.0 | Apache-2.0 |
| pycparser | 3.12 | BSD-3-Clause |
| pygments | 2.21.0 | BSD-2-Clause |
| pyhanko | 0.38.1 | MIT |
| pyhanko-certvalidator | 0.33.0 | MIT |
| pymupdf | 2.1 | AGPL-3.0 / Artifex commercial |
| pymupdf-layout | 2.1 | Compatibility placeholder; see PyMuPDF |
| pymupdf4llm | 2.1 | Compatibility placeholder; see PyMuPDF |
| pyparsing | 3.3.3 | MIT |
| pypdf | 7.1.1 | BSD-3-Clause |
| pyyaml | 6.0.3 | MIT |
| reportlab | 5.1.0 | BSD-style (upstream license) |
| requests | 2.34.2 | Apache-2.0 |
| rich | 15.0.0 | MIT |
| ruff | 0.17.6 | MIT |
| sortedcontainers | 2.4.0 | Apache 2.0 |
| tabulate | 0.10.0 | MIT |
| tomli | 2.5.0 | MIT |
| tomli-w | 1.2.0 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| tzlocal | 5.4.5 | MIT |
| uritools | 7.0.0 | MIT |
| urllib3 | 2.8.0 | MIT |
| yarl | 1.25.1 | Apache-2.0 |

Installed license files and available upstream provenance were inspected; a missing license file in a metadata-only package is not silently treated as public domain. Dependency advisory results are separate from this license review. Users preparing another runtime must review the actual resolved versions and distribution obligations.

Official tax references are linked as sources, not relicensed as project code. No government, ChatGPT, GitHub or dependency-provider endorsement is claimed. The original overview SVG uses no stock images, third-party logos or embedded font files.
