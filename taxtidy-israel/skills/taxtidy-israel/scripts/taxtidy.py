"""Explicit private cases, reviewed evidence and scoped 2025 tax estimates."""

import argparse
import json
import os
import stat
import sys

import case


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"ok": False, "reason": "invalid_arguments"}), file=sys.stderr)
        raise SystemExit(2)


def main():
    parser = Parser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True, parser_class=Parser)
    init = actions.add_parser("init", help="Create a new private case; never overwrite")
    init.add_argument("--case-root", required=True)
    init.add_argument("--taxpayer-id", required=True)
    init.add_argument("--years", required=True, nargs="+", type=int)
    init.add_argument("--language", default="he")
    init.add_argument("--synthetic", action="store_true")
    imp = actions.add_parser(
        "import-evidence",
        help="Import reviewed observations and coverage facts from JSON",
    )
    imp.add_argument("--case-root", required=True)
    imp.add_argument("--input", required=True)
    calc = actions.add_parser(
        "calculate", help="Estimate a covered 2025 case; no filing"
    )
    calc.add_argument("--case-root", required=True)
    calc.add_argument("--tax-year", required=True, type=int)
    calc.add_argument(
        "--scenario", choices=["assistance_taxable", "assistance_excluded"]
    )
    event = actions.add_parser(
        "record-event", help="Record reviewed evidence; never execute a portal action"
    )
    event.add_argument("--case-root", required=True)
    event.add_argument("--input", required=True)
    pdf = actions.add_parser(
        "pdf", help="Process authorized PDFs locally; no upload or filing"
    )
    pdf.add_argument("--case-root", required=True)
    pdf.add_argument("--input", required=True)
    pdf.add_argument("--owner", required=True)
    pdf.add_argument("--tax-year", required=True, type=int)
    pdf.add_argument("--purpose", required=True)
    pdf.add_argument("--authorized", action="store_true")
    pdf.add_argument("--convert-signed", action="store_true")
    pdf.add_argument("--tesseract")
    pdf.add_argument("--tessdata-dir")
    review = actions.add_parser(
        "review-document",
        help="Record manual content/recipient review; no portal acceptance",
    )
    review.add_argument("--case-root", required=True)
    review.add_argument("--input", required=True)
    for name in ("summary", "resume"):
        view = actions.add_parser(
            name, help="Regenerate checked per-year results from the private checkpoint"
        )
        view.add_argument("--case-root", required=True)
        view.add_argument("--language")
        view.add_argument("--as-of")
        if name == "resume":
            view.add_argument(
                "--input", help="Reviewed newly available evidence import"
            )
    args = parser.parse_args()
    try:
        if args.action == "pdf":
            import pdf_tools

            value = pdf_tools.process(
                args.case_root,
                args.input,
                args.owner,
                args.tax_year,
                args.purpose,
                args.authorized,
                args.convert_signed,
                args.tesseract,
                args.tessdata_dir,
            )
            print(json.dumps(value, ensure_ascii=False))
            return 0 if value["ok"] else 1
        if args.action == "init":
            state = case.initialize(
                args.case_root,
                args.taxpayer_id,
                args.years,
                args.language,
                args.synthetic,
            )
        elif args.action in {"import-evidence", "record-event", "review-document"} or (
            args.action == "resume" and args.input is not None
        ):
            fd = os.open(args.input, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "r", encoding="utf-8") as stream:
                meta = os.fstat(stream.fileno())
                case.require(
                    stat.S_ISREG(meta.st_mode) and meta.st_size <= case.MAX_CASE_BYTES,
                    "unsafe_input_file",
                )
                batch = case.parse_json(stream.read())
            if args.action == "review-document":
                print(
                    json.dumps(
                        case.review_document(args.case_root, batch), ensure_ascii=False
                    )
                )
                return 0
            state = (
                case.record_event(args.case_root, batch)
                if args.action == "record-event"
                else case.import_evidence(args.case_root, batch)
            )
        elif args.action == "calculate":
            case.calculate_case(
                args.case_root,
                args.tax_year,
                args.scenario,
                publish=lambda value: print(json.dumps(value, ensure_ascii=False)),
            )
            return 0
        if args.action in {"summary", "resume"}:
            case.workflow_summary(
                args.case_root,
                args.language,
                args.as_of,
                publish=lambda value: print(json.dumps(value, ensure_ascii=False)),
            )
            return 0
        print(
            json.dumps(
                {
                    "ok": True,
                    "case_id": state["case_id"],
                    "revision": state["revision"],
                    "years": case.wage_summary(state),
                    "capabilities": [
                        "case_init",
                        "reviewed_wage_import",
                        "evidence_reconciliation",
                        "freshness_invalidation",
                        "scoped_2025_calculation",
                        "reviewed_event_records",
                        "checked_summary_resume",
                    ],
                    "tax_calculation_available": True,
                    "pdf_processing_available": True,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except case.CaseError as exc:
        reason = exc.code
    except FileExistsError:
        reason = "case_exists"
    except (OSError, UnicodeError):
        reason = "local_io_error"
    except (ValueError, TypeError, KeyError, RecursionError):
        reason = "invalid_input"
    print(json.dumps({"ok": False, "reason": reason}), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
