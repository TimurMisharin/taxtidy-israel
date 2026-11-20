# Phase-3 local case format

This is the authoritative implemented local format. No external service accepts this schema by implication. Runtime: Python 3.12+, single-user POSIX filesystem with `fcntl` locking, no shared hosted case directory. Use a private explicit absolute root **outside** this package and its source repository. Each case has directory mode 0700, files 0600 and its own opaque case ID. Do not use symlink components; on platforms with a `/var` alias choose the resolved private path. The parent must already exist. The initializer refuses any existing target.

From the skill directory, using the prepared Python interpreter:

```sh
python3 scripts/taxtidy.py --help
python3 scripts/taxtidy.py init --case-root /absolute/private/new-case --taxpayer-id opaque-person --years 2025 --language he --synthetic
python3 scripts/taxtidy.py import-evidence --case-root /absolute/private/new-case --input /absolute/private/reviewed-evidence.json
```

Paths above are placeholders for a user-owned location. `--synthetic` marks fictional development cases; omit it for a genuinely authorized private case. It does not permit another person's documents. `init`, `import-evidence`, `calculate`, `record-event`, `summary` and `resume` are the actions. Results are JSON on stdout; errors are JSON on stderr with a stable `reason`, exit 1 (invalid arguments: exit 2). No error includes document contents or credentials. Save intended financial output only in private storage, with `umask 077`; stdout is a requested result, not a diagnostic log. Never pass passwords, login credentials or one-time codes as arguments or input fields.

## Checkpoint and template

`checkpoint.json` is schema version 1. Its exact top-level keys are `schema_version`, `case_id`, `taxpayer_id`, `revision`, `preferred_language`, `participants`, `years`, `synthetic`, and the list-valued `authorized_search_scope`, `observations`, `economic_items`, `conflicts`, `requirements`, `eligibility`, `events`, `attachments`, `routes`, `results`, `assumptions`, `next_actions`. Participants have `id`, `role` (taxpayer/spouse) and boolean `authorized`. Imports are for the subject taxpayer only; spouse allocation requires later functionality. Search scopes/events/routes are preserved data, not executed actions or verified filing states. `years` contains distinct integer years. Only the narrow 2025 profile in [tax rules](tax-rules.md) enables estimates.

Use [checkpoint template](../assets/templates/checkpoint.json) as an empty schema guide, not a live case. Null IDs and empty years must be filled by `init`. Never copy an existing taxpayer's checkpoint into a shared template. `annual_estimate` references point to checked private calculation artifacts. Explicitly synthetic `synthetic_freshness_probe` records remain only for regression tests without monetary amounts; ordinary cases cannot accept probes.

## Reviewed-evidence import

Use [evidence template](../assets/templates/evidence.json). An input object has exactly `case_id`, integer `expected_revision`, and list `observations`, with optional list `eligibility`. Obtain identity/revision from the initialized/current private checkpoint. Conflicting expected revisions require rereading; they do not overwrite the newer case. Replaying identical reviewed observations is idempotent.

Each observation has exactly:

| Field | Meaning and validation |
|---|---|
| `owner`, `issuer` | Subject participant ID and explicit issuer identifier; do not conflate employers |
| `kind`, `document_type` | `wages`; one of `form_106`, `a99_5`, `payslip_ytd`, `payslip_monthly` |
| `tax_year` | Integer selected case year |
| `issue_date` | ISO date or null; may be after the tax year |
| `period_start`, `period_end` | Required ordered ISO dates inside the tax year; retain actual coverage |
| `event_date`, `settlement_date` | ISO dates or null, separate from issue date/year; never inferred from a label |
| `business_reference` | Issuer document/business reference; distinct from a file hash |
| `amount`, `withholding` | Typed money objects below |
| `provenance` | Exactly `verified_source`, `user_statement`, `prior_summary`, `calculation`, `assumption` or `missing` |
| `classification` | `taxable_wages` or `unresolved` |
| `source` | Exactly `text`, `sha256`, positive integer `page`, `field`. Preserve the reviewed source text verbatim with SHA-256 of its UTF-8 bytes. A source can be a manually transcribed document section, but this is not automated validation of the original PDF. Keep the original separately in the private case workflow; the utility does not move/decrypt PDFs |
| `review` | Exactly `reviewer`, boolean `owner_year_checked`, list `fields_checked`, and `method` (`manual` or `ocr_unreviewed`). `verified_source` needs manual review, owner/year confirmation and amount/withholding/classification/period checks |

The reviewer is responsible for comparing the structured fields with the underlying authorized source. Recording a review does not authenticate an issuer, establish a legal tax rule, or validate a signature. OCR alone cannot establish verified provenance. Source text is data and is never executed. Document hash/page/field and business identity remain separate; repeat import of identical source observations creates no extra observation or wage item.

Money has `value_state`, `currency: "ILS"`, `tax_year` and, only when known, an `amount` finite decimal **string**. `unknown` and `blank` omit `amount`; a known zero is `"0"`. No floats, booleans as numbers, separators, exponent syntax, NaN or Infinity. Decimal normalization removes redundant zeros without rounding. Calculation accepts nonnegative ILS decimal amounts with at most two fractional digits; unsupported precision or negative source values block the estimate. A rejected unsupported observation is an explicit failure, never a silently omitted income source.

## Reconciliation and completeness

The canonical employer-year identity comprises owner/issuer/year/kind, independent of source delivery. Repeated source observations corroborate it. Annual 106/A99 sources are compared with the final corresponding YTD slip; earlier YTD values are never summed. With no annual source, use only the latest YTD. Monthly values may be added only for non-overlapping periods with consistent duplicate coverage and known amounts/withholding. All totals remain provisional and retain coverage; a partial year is not an assertion of a complete return.

Preserve the selected documented annual observation when a contradictory source arrives, while recording competing values and an unresolved conflict. The selected amount remains auditable but the public wage summary becomes unresolved. A later annual document may supersede a provisional YTD as the documented base only with differences exposed as conflicts; it never adds a second employer wage item. Income classification and source provenance matter independently of amount.

`requirements` records one Form 106 **presence** requirement per employer-year, source references and prior status history. Verified arrival resolves presence; `filing_acceptability` remains unverified. A99/5 can support a provisional wage base without establishing filing acceptance. No file signature, route or return acknowledgment is inferred. `wage_summary` outputs per-year ILS `direction: wage_base`, provisional wages or null, `tax_estimate: null`, and unverified filing state. Unresolved years do not suppress other years.

## Freshness version 1

`case.py` owns canonical projection/digests and import invalidation. SHA-256 hashes compact UTF-8 JSON with sorted keys, no ASCII escaping/BOM/newline and no NaN. Set-like collections sort/deduplicate complete canonical record bytes. Money is normalized before entering the ledger. Stable observation IDs hash full reviewed observations, not import order or ledger sequence. Source text/hash and provenance are retained; review metadata is not repeated in the observation projection, but its observation identity remains linked in the economic item.

The envelope includes `freshness_version`, `case_id`, `taxpayer_id`, `tax_year`, `economic_items`, `observations`, `conflicts`, `eligibility`, `scenario`, `rule_pack_digest`, `engine_version`. All calculation-relevant disputes are included even if the selected wage amount did not change. Economy/source identities, amounts, withholding, dates, classification, counting decision and unresolved conflicts therefore affect freshness. Eligibility records are scoped by owner/year. `scenario` is explicit null or the explicit assumptions. The runtime loads only the packaged 2025 rule pack; callers cannot supply an arbitrary rate pack through the CLI.

Revision, language, events, display paths, cached results and filing-only requirements are excluded from numeric freshness. Identical replay and reordering do not invalidate; a genuinely new corroborating document can conservatively invalidate, without changing wages. Affected year result references become stale in the same locked, validated atomic checkpoint replacement as the imported evidence. Unaffected years retain their result-reference status. Preserve all old synthetic probe metadata in tests; never present it as a tax result.

If a managed `summary.md` exists, overwrite it with a neutral recalculation notice **before** committing changed evidence. Failure to clear it aborts checkpoint mutation. A later failed checkpoint replacement may leave a neutral summary beside the intact previous checkpoint. This is deliberately not a claim of a multi-file atomic transaction. Existing output copies outside the managed case cannot be recalled.

Calculate, summary and resume implement the checked artifact boundary below. Summary/resume use the same checked artifact boundary. No stored `current` flag is a permission to display an annual amount.

## Local storage checks

Checkpoint and lock files are opened relative to a validated case directory descriptor, with no-follow checks; checkpoints require private ownership, regular files, one hard link and a 50 MiB limit. JSON rejects duplicate keys and non-finite/float numbers. Writes create exclusive private temporary files, fsync, replace inside the directory and fsync the directory. The lock and expected revision protect cooperating single-user processes. Symlink/traversal/cross-source case roots are refused. These controls do not claim an OS sandbox or protection against an attacker controlling the same user account.


Monthly payroll is summed once per distinct nonoverlapping period. Compare monetary totals only for a continuous set covering exactly the selected annual/YTD interval; partial or gapped coverage is not a full-period total. Any verified monthly payslip starting before or ending after an annual certificate's stated employment interval opens an unresolved period conflict, independently of gaps, aggregate totals or known monetary values. Period conflicts link the annual certificate and the contradicting payslip observations directly. Conflicting duplicate periods or overlapping monthly sources remain unresolved even when an annual certificate exists. A monthly aggregate in monetary conflict evidence carries source observation identities so its arithmetic can be traced to each payslip. All source observations remain in the checkpoint. Conflicts suppress provisional public wages and invalidate affected result references.

The 50 MiB limit applies to serialized UTF-8 bytes on both reads and writes. Import validates and checks the complete candidate size before clearing a managed summary or replacing the checkpoint. An oversized candidate returns case_too_large and leaves both prior files unchanged. Splitting an import does not bypass the cumulative checkpoint limit.

## Additional reviewed observations

The common observation fields above are unchanged. Wages retain their original schema. Each other kind adds exactly `details`, with `review.fields_checked` including `details`. Classification is its kind or `unresolved`; unresolved classification blocks calculation except the explicitly conditional assistance scenarios. Currency and money state rules apply to every nested monetary value.

| Kind / document types | Exact details keys |
|---|---|
| `securities` / `form_867` | Typed money: `realized_loss`, `prior_offset`, `sale_proceeds`, `dividends`, `interest`, `foreign_tax`, `loss_carry_in`. Text: `basis`, `asset_class`, `rate`. Booleans: `sole_owner`, `material_holder`, `business_or_related_party`. Main `amount` is realized gross gain; `withholding` is actual Israeli withholding. Only `gross_before_institution_offsets`, `domestic_listed_shares`, rate `0.25` and the narrow ownership/income limits are supported. |
| `donation` / `donation_receipt`, `authority_donation`, `forwarded_receipt` | Typed money `payroll_applied_credit`; booleans `sole_donor`, `settled_same_year`, `cancelled`, `fees_or_benefit`, `installments`, `carry_in`; ISO dates `approval_from`, `approval_to`; text `approval_reference`. Main amount is the settled donation; withholding must be known zero. Event date and settlement evidence must be established. |
| `reserve` / `national_insurance_certificate`, `employer_benefit_certificate` | Booleans `included_in_wages`, `same_year_receipt_and_service`; text `program`; `wage_item` is the linked wage economic ID, or null for a direct payment. An included benefit adds neither wages nor withholding again. Direct taxable employee reserve income requires program `national_insurance_employee_reserve` and the annual certificate. |
| `assistance` / `payment_record` | Text `program`, currently only `unknown`; classification may stay `unresolved`. Amount is known; withholding is known zero for the two supported conditional comparisons. No complete ordinary result is produced. |
| `advance_payment` / `tax_payment_receipt` | Text `payment_id`; main amount is a distinct advance income-tax payment; withholding is known zero. |

For supported donations and direct reserve payments, both event and settlement dates must be known and inside the calculation year, in addition to a true same-year attestation. Missing or cross-year dates block the estimate even when the flag says true. A certificate may still be issued after the tax year.

Nonwage economic identity is owner/issuer/year/kind/business reference; an advance uses payment ID instead of the document reference. Use the underlying issuer and receipt/account identity even when forwarded or displayed by an authority. Do not guess a match between different issuer references. Disagreement in amounts, withholding, details or dates creates a blocking conflict. Nonwage conflict resolution beyond corroborating identical business records is not implemented. All observations are retained; a file hash alone is not the business identity.

## Coverage and source-backed resolution

`eligibility` accepts reviewed `profile` and `wage_resolution` records. Both have exactly `kind`, `owner`, `tax_year`, `source`, `review`, plus the fields below and optional `supersedes` (list of hashes of existing same-kind/owner/year/issuer eligibility records). Superseded records remain in history. Review requires manual owner/year verification and `fields_checked` containing the kind. A profile is reviewed case intake, not evidence that the government authenticated personal facts; compare its declarations against collected source evidence.

A profile adds `facts`, exactly: booleans `resident_full_year`, `adult_under_60`, `unmarried`, `all_income_declared`, `all_payments_declared`, `other_entitlements_or_deductions`, `pension_or_insurance_contributions`, `foreign_facts`, `prior_loss_or_donation_carry_in`, plus text `sex`. All first five must be true, the next four false, and sex `male`. Exactly one active profile for the taxpayer/year is required. Unknown answers cannot be replaced by those values merely to obtain a result. Multiple active profiles block calculation.

A wage resolution adds `issuer`, `selected_observation` (hash of a verified annual/latest-YTD candidate), `considered_observations` (sorted unique hashes of **all** verified observations for that employer/year). The underlying source must explain the discrepancy and support the selection; the synthetic test's resolution is not a suggested real-world override. No bare selection flag resolves a conflict. A later distinct verified wage source makes the old resolution inapplicable until reviewed again. Conflicts retain both values and link the resolution hash.

## Calculate and publish

```sh
python3 scripts/taxtidy.py calculate --case-root /absolute/private/new-case --tax-year 2025
python3 scripts/taxtidy.py calculate --case-root /absolute/private/new-case --tax-year 2025 --scenario assistance_taxable
python3 scripts/taxtidy.py calculate --case-root /absolute/private/new-case --tax-year 2025 --scenario assistance_excluded
```

The result reference has exactly `owner`, `tax_year`, `purpose: annual_estimate`, `status: current|stale`, `freshness_version: 1`, `input_digest`, `rule_pack_digest`, `engine_version`, `scenario` (null or one of the two choices), `artifact`, `artifact_sha256`, and optional stale `reason`. The artifact path is `calculations/<year>-<input-digest>.json`, with private 0700 directory and 0600 file. Its exact wrapper keys are `case_id`, `taxpayer_id`, `tax_year`, `freshness_version`, `input_digest`, `rule_pack_digest`, `engine_version`, `scenario`, `estimate`. The artifact SHA-256 covers its actual UTF-8 bytes. Old artifacts stay private for audit and are not current displays.

`estimate` contains year/currency/status/scenario/condition/filing-ready/rounding, source income totals and exclusions, ordinary/gain taxable totals, bracket trace, deductions, credits, liability before/after donations, withholding, advances, separate foreign tax/credit, signed `balance_due`, absolute `balance` and direction, evidence references and rule IDs. All financial amounts are decimal strings; no floats or desired-balance input exists. Read [tax rules](tax-rules.md) for source-to-result arithmetic.

The date-guard repair advances the engine to `0.2.1`; persisted `0.2.0` estimates cannot pass the checked current-result boundary and need recalculation.

`current_result` validates current case completeness, version, taxpayer/case/year/scenario, a recomputed input digest, the full rule-pack digest and engine version, then actual artifact bytes and envelope. Missing/legacy metadata, forged current flags, changed rules/engine, wrong identity or artifact alteration fail closed. Call it under the case lock; never display an artifact or cached summary by itself. A failed calculation clears the managed summary when private storage remains usable. Existing copies elsewhere cannot be recalled.

Calculation snapshots under lock, computes outside it, then reacquires the lock and rechecks revision, rules and digest before writing or publishing. Evidence imported during computation returns `calculation_inputs_changed`, with no monetary stdout or new result reference. CLI monetary publication occurs inside that lock. Recalculation stales earlier same-year references, including the other scenario; comparison should retain both explicitly conditional returned outputs and never label one a complete result. Import output contains provisional wage evidence only, never a cached tax estimate.

Stable blocking reasons include `unsupported_tax_year`, `missing_coverage_profile`, `unsupported_or_incomplete_profile`, `unresolved_income_conflict`, `incomplete_income_evidence`, `missing_calculation_money`, `unresolved_assistance_program`, `unsupported_securities_facts`, `unverified_donation_eligibility`, `unsupported_high_income`, `stale_calculation`, `freshness_unverifiable`, and `calculation_inputs_changed`. Resolve the particular evidence or unsupported coverage; do not retry with invented zeros or suppressed sources. Other independent years remain collectable.

## Workflow CLI and publication

```sh
python3 scripts/taxtidy.py record-event --case-root /absolute/private/new-case --input /absolute/private/reviewed-event.json
python3 scripts/taxtidy.py summary --case-root /absolute/private/new-case --as-of 2026-11-19
python3 scripts/taxtidy.py resume --case-root /absolute/private/new-case --language ru --input /absolute/private/reviewed-new-evidence.json
```

`record-event` input is exactly `case_id`, integer `expected_revision`, and `event`. It records reviewed evidence; it executes no external action. Replay is idempotent; stale revisions fail. `resume --input` uses the existing reviewed-evidence import schema, not an event. Resume reads current evidence, then produces the projection and saves the requested language. With no input it resumes the verified checkpoint. Default as-of date uses Asia/Jerusalem; explicit `--as-of` is an ISO date for reproducible historical review. No mailbox or portal capability is bundled.

Summary/resume validate and regenerate under the case lock; each ordinary/scenario amount passes `current_result`. Monetary stdout publication and summary.md replacement occur while holding the lock. JSON contains `years` and a `year_table`, both using the same checked estimates, reasons, actual filing evidence, next evidence, deadlines, `next_control_he` and `control_scope`. The assistant renders these as a plain-language year table in the preferred language, including the translated Hebrew public service label and its scope even when the calculation is blocked. An unresolved route does not authorize submission. For `unsupported_tax_year`, next actions allow document collection/reconciliation and a year-specific official/professional calculation; evidence import cannot enable local numeric coverage. Never read prior summary.md as authoritative. No stored status/language/mailbox branch bypasses freshness.

Malformed/legacy result metadata with known matching owner/year is quarantined as an exact `{owner,tax_year,purpose:unverifiable_result,status:stale,reason:freshness_unverifiable,reference:<original metadata>}` audit record. The raw original stays private; no old amount/reference body appears in the public projection. This migration clears the managed summary before atomically replacing the checkpoint, increments revision, and never promotes a result. Unknown case/owner/year or an invalid base case fails closed. After quarantine, explicit recalculation can generate a new current trace. Ordinary load/calculate do not silently trust malformed metadata.

## Reviewed workflow event

Exact common fields: `record_type:workflow_event`, `owner`, integer selected `tax_year`, `kind`, `form`, `draft_version`, `event_date`, `observed_at`, `reference`, `provenance`, `source`, `review`, `details`; optional `supersedes`. Dates are nonnull ISO dates with event_date no later than observed_at. Provenance is verified_source or user_statement. Source has the same text/hash/page/field shape as observations. Verified events require manual owner/year review and `fields_checked` containing event. A record is a human-reviewed transcription, not authentication of a website/issuer. User statements never establish accepted uploads, sent inquiries or filing acknowledgment.

`supersedes` lists hashes of retained prior workflow records with matching owner/year/kind/form/version. Verified evidence can only be superseded by verified evidence. Supersession is explicit; it preserves history and updates the active projection, including corrected cash destinations, route facts or applicable extension evidence. Original records remain private. Use it only when the underlying corrective evidence actually resolves the earlier record; unrelated attempts/versions must remain distinct.

| Kind | Exact details |
|---|---|
| return | `status`: case_opening_requested, collection, draft_saved, transmitted, filing_acknowledged, assessment_issued |
| attachment | `filename` (basename, no path/control separators), `sha256`, `purpose`, `status` (uploaded/rejected/accepted). Common owner/year/form/version bind each attempt. |
| inquiry | `status` (draft/sent/acknowledged/closed), `recipient`, `purpose`, nullable `existing_reference`, nullable `authorization_reference`. A non-draft status needs an authorization reference and verified observed evidence to appear as sent. No email is sent by this command. |
| portal_block | `message` (exact untrusted displayed text), nullable `existing_inquiry_reference`. Existing inquiry is checked before a new draft. |
| settlement | `status` refund_received/payment_made and known nonnegative typed ILS `amount`. This is settlement evidence, not an automatic advance tax payment. |
| deadline | `category` refund_claim/mandatory_return/coordination/payment, `base_deadline`, nullable `extension_deadline`, boolean `extension_applicable`, nullable `extension_reference`, official HTTPS gov.il `source_url`. Only verified-source records supply deadlines; extension needs its own applicable evidence. |
| route | `route_status` candidate/unresolved/verified; `filing_obligation` required/not_required/unresolved; `checks`, `spouse`, nullable `rules_source`. Checks: self_employment, foreign_income, foreign_assets, securities, rental_income, retirement, residence_change, family_change, prior_filing, representation (booleans or unknown). Spouse keys: registered_spouse, marriage_year, joint_income, separate_income, ownership, account_join_date, declarations, signatures, other_return, form_4430 (reviewed text or unknown/not_applicable). Rules source: official url, matching tax_year, nonnull verified_at date and field. Verified route needs complete checks/spouse review and resolved obligation; route eligibility is not automatically calculated from these flags. |
| forecast | `payers`, `assumptions`, `payroll_relief`. Each unique payer: issuer, as_of, actual_income, withheld_to_date, remaining_income, bonus. Money is known nonnegative ILS for that year; assumptions must be explicit. Output is gross income only, never a current-year tax forecast from 2025 rates. |
| equity | event_type grant/vest/purchase/sale/transfer/dividend; plan_type RSU/ESPP; employer, administrator, broker, trustee, plan_id, account, security, decimal-string quantity; typed money gross/withholding/payroll_component/adjusted_basis; nullable payroll_item/destination/from_account/to_account. Three-letter currencies are retained without conversion. Event date must match its assigned tax year. |
| dividend_match | `institution`, `payment_reference` (nonempty text), `observations` (at least two distinct dividend-event SHA-256 hashes, canonicalized in sorted order). Verified source and manual review fields `event` and `payment_link` are required. Each target must be a retained verified equity/dividend record for the same owner/year, naming that institution as broker/trustee. Source text/page/field must support the exact account/reference linkage to one payment. |

Equity records live in eligibility and affect numeric freshness; route records live in routes. Other workflow records live in events and do not alter tax-input identity. Route source-reviewed checks/spouse/provenance enter the numeric projection while route choice and filing-only status do not. Unsupported route-income facts block the narrow calculator. Equity is guidance/reconciliation only and blocks a complete annual total. No additional numeric coverage is enabled.

Filing projection groups by year/form/version and requires matched verified acknowledgment. An unacknowledged draft prevents an overall filed claim even when another version has an acknowledgment. Attachment attempts, observed statuses, settlements and inquiries remain distinct. Raw source text is not copied into normal monetary projections. Public controls are entry candidates, not eligibility or submission authorization. See [routing](portal-and-routing.md), [equity](equity-and-benefits.md) and [languages](languages.md).

`dividend_match` records live in eligibility with equity and participate in numeric freshness; they never enable equity arithmetic. Matching needs an active verified linkage to still-active observations, equal date/plan type/employer/plan/security/quantity/gross/withholding/destination and known gross/tax/destination. Financial coincidence alone leaves every record unmatched with an account/reference-specific institution question. Public dividend rows retain `source_reference`, `business_reference`, `account` and the supporting `match_evidence` hashes. Check claims globally by owner/tax_year/institution/payment_reference as well as by shared target. Different applicable observation sets for one payment remain unresolved even when disjoint or internally consistent; identical corroborating claims can coexist. Different payment identities remain independent unless they share a target. Source-backed proof supersession resolves the conflicting claim without deleting history. Superseding any target invalidates that linkage in projections without deleting its historical proof; supply a fresh reviewed linkage to the replacement. Legacy unlinked equity remains readable and unresolved.

## Phase-4 document records

`pdf --case-root ROOT --input ABSOLUTE_FILE_OR_DIRECTORY --owner ID --tax-year YEAR --purpose PURPOSE --authorized` processes one file or selected top-level PDFs. Optional `--tesseract PATH`, `--tessdata-dir PATH` configure the observed local OCR installation; `--convert-signed` authorizes a signed derivative. Passwords use a concealed terminal prompt only. See [PDF workflow](pdf-workflow.md) for limits, inspection and recipient requirements.

Checkpoint `attachments` now holds only locally generated document references: exact keys `document_id` (32 lowercase hex), `owner`, `tax_year`, `purpose`, `display_filename`, `report_sha256`. The report and unchanged original live in private `documents/<document_id>/report.json` and `original.pdf`; validated derivatives use `working.pdf`. Reports include source/copy hashes, page geometry/rotation, rendered comparisons, source/OCR text, signature-presence state, structural status and manual review. All files0600/directories0700, no symlink/hardlink acceptance. No password is stored. Workflow attachment/portal attempts stay in the existing event ledger, separate from these local references.

The exact [document-review template](../assets/templates/document-review.json) is the input to `review-document --case-root ROOT --input JSON`: case/revision/document/report identity, reviewer/date, owner/year/purpose, `content_matches` boolean, sorted complete `pages_visual_checked`, important `fields` (`page`, `field`, `value` in the existing ILS money format) and `recipient_version` (`unconfirmed`, `original`, `working`). User-supplied `attachment_ready` is forbidden. Readiness is derived; scanned text alone never suffices. A signed working copy also needs conversion authorization and exact recipient-version acceptance. Reports are hash-checked on review/summary; changed content becomes `document_unverifiable`, not ready. Review checkpoint failure restores the prior report; an interrupted multi-file write may fail closed and requires rereading, not a claim of multi-file atomicity.

Summary/resume years include a `documents` projection with local readiness, source reference and `portal_acceptance: unobserved`. Local document/review records do not enter the numeric freshness envelope, create monetary evidence, grant issuer authentication, resolve Form106 presence or change filing state. Import reviewed source observations separately. Portal acceptance/transmission/acknowledgment still require their own matched evidence. All directories/reports remain private to the case.
