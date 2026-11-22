"""Private POSIX cases, reviewed evidence, freshness and checked calculation publication."""

import copy
import fcntl
import hashlib
import json
import os
import re
import stat
import uuid
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal, localcontext
from itertools import pairwise
from pathlib import Path

SCHEMA_VERSION = 1
FRESHNESS_VERSION = 1
ENGINE_VERSION = "0.2.1"
MAX_CASE_BYTES = 50 * 1024 * 1024
PROVENANCE = {
    "verified_source",
    "user_statement",
    "prior_summary",
    "calculation",
    "assumption",
    "missing",
}
ID = re.compile(r"[A-Za-z0-9_-]{1,80}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
MONEY = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


class CaseError(ValueError):
    """Errors expose stable codes, never document contents."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code="invalid_case_data"):
    if not condition:
        raise CaseError(code)


def exact(obj, keys):
    require(type(obj) is dict and set(obj) == set(keys), "invalid_fields")


def text(value):
    require(type(value) is str and 0 < len(value) <= 10000)
    return value


def identifier(value):
    require(type(value) is str and ID.fullmatch(value) is not None)
    return value


def year(value):
    require(type(value) is int and 1900 <= value <= 2200, "invalid_tax_year")
    return value


def no_floats(value):
    require(not isinstance(value, float), "float_not_allowed")
    if isinstance(value, dict):
        require(all(type(k) is str for k in value))
        require(
            not {k.lower() for k in value} & {"password", "otp", "credential", "token"},
            "secret_field_forbidden",
        )
        for v in value.values():
            no_floats(v)
    elif isinstance(value, list):
        for v in value:
            no_floats(v)
    else:
        require(value is None or type(value) in (str, bool, int))


def canonical(value):
    no_floats(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def records(values):
    require(type(values) is list)
    return [json.loads(b) for b in sorted({canonical(v) for v in values})]


def money(value, expected_year=None):
    require(type(value) is dict)
    known = value.get("value_state") == "known"
    exact(
        value,
        {"value_state", "currency", "tax_year"} | ({"amount"} if known else set()),
    )
    require(value["value_state"] in {"known", "unknown", "blank"})
    year(value["tax_year"])
    require(
        expected_year is None or value["tax_year"] == expected_year, "year_mismatch"
    )
    require(value["currency"] == "ILS", "unsupported_currency")
    out = dict(value)
    if known:
        amount = value["amount"]
        require(
            type(amount) is str
            and len(amount) <= 50
            and MONEY.fullmatch(amount) is not None,
            "invalid_money",
        )
        n = Decimal(amount)
        require(n.is_finite(), "invalid_money")
        out["amount"] = (
            "0"
            if n == 0
            else (
                format(n, "f").rstrip("0").rstrip(".")
                if "." in format(n, "f")
                else format(n, "f")
            )
        )
    return out


def date_field(value, tax_year=None):
    if value is None:
        return
    require(type(value) is str)
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise CaseError("invalid_date") from None
    require(parsed.isoformat() == value, "invalid_date")
    require(tax_year is None or parsed.year == tax_year, "period_year_mismatch")


def reviewed_source(source, review, required_fields, verified=True):
    exact(source, {"text", "sha256", "page", "field"})
    text(source["text"])
    text(source["field"])
    require(type(source["page"]) is int and source["page"] > 0)
    require(
        source["sha256"] == hashlib.sha256(source["text"].encode("utf-8")).hexdigest(),
        "source_hash_mismatch",
    )
    exact(review, {"reviewer", "owner_year_checked", "fields_checked", "method"})
    text(review["reviewer"])
    require(type(review["owner_year_checked"]) is bool)
    require(
        type(review["fields_checked"]) is list
        and all(type(f) is str for f in review["fields_checked"])
    )
    require(review["method"] in {"manual", "ocr_unreviewed"})
    if verified:
        require(
            review["owner_year_checked"]
            and review["method"] == "manual"
            and required_fields <= set(review["fields_checked"]),
            "review_required",
        )


def details(kind, raw, tax_year):
    money_fields = {
        "securities": {
            "realized_loss",
            "prior_offset",
            "sale_proceeds",
            "dividends",
            "interest",
            "foreign_tax",
            "loss_carry_in",
        },
        "donation": {"payroll_applied_credit"},
        "reserve": set(),
        "assistance": set(),
        "advance_payment": set(),
    }
    fields = {
        "securities": {
            "basis",
            "asset_class",
            "sole_owner",
            "material_holder",
            "business_or_related_party",
            "rate",
        },
        "donation": {
            "sole_donor",
            "settled_same_year",
            "approval_from",
            "approval_to",
            "approval_reference",
            "cancelled",
            "fees_or_benefit",
            "installments",
            "carry_in",
        },
        "reserve": {
            "included_in_wages",
            "wage_item",
            "program",
            "same_year_receipt_and_service",
        },
        "assistance": {"program"},
        "advance_payment": {"payment_id"},
    }
    exact(raw, fields[kind] | money_fields[kind])
    out = copy.deepcopy(raw)
    for key in money_fields[kind]:
        out[key] = money(raw[key], tax_year)
    bool_fields = {
        "sole_owner",
        "material_holder",
        "business_or_related_party",
        "sole_donor",
        "settled_same_year",
        "cancelled",
        "fees_or_benefit",
        "installments",
        "carry_in",
        "included_in_wages",
        "same_year_receipt_and_service",
    }
    for key in fields[kind]:
        if key in bool_fields:
            require(type(raw[key]) is bool)
        elif key == "wage_item" and raw[key] is None:
            continue
        else:
            text(raw[key])
    if kind == "donation":
        date_field(raw["approval_from"])
        date_field(raw["approval_to"])
        require(raw["approval_from"] <= raw["approval_to"])
    return out


def reviewed_fact(raw, state):
    require(type(raw) is dict and raw.get("kind") in {"profile", "wage_resolution"})
    keys = {"kind", "owner", "tax_year", "source", "review"}
    keys |= (
        {"facts"}
        if raw["kind"] == "profile"
        else {"issuer", "selected_observation", "considered_observations"}
    )
    exact(raw, keys | ({"supersedes"} if "supersedes" in raw else set()))
    if "supersedes" in raw:
        require(type(raw["supersedes"]) is list)
        for identity in raw["supersedes"]:
            previous = next(
                (v for v in state["eligibility"] if digest(v) == identity), None
            )
            require(
                previous is not None
                and all(
                    previous.get(k) == raw.get(k)
                    for k in ("kind", "owner", "tax_year", "issuer")
                ),
                "invalid_fact_supersession",
            )
    require(
        raw["owner"] == state["taxpayer_id"] and raw["tax_year"] in state["years"],
        "owner_year_mismatch",
    )
    reviewed_source(raw["source"], raw["review"], {raw["kind"]})
    if raw["kind"] == "profile":
        exact(
            raw["facts"],
            {
                "resident_full_year",
                "sex",
                "adult_under_60",
                "unmarried",
                "all_income_declared",
                "all_payments_declared",
                "other_entitlements_or_deductions",
                "pension_or_insurance_contributions",
                "foreign_facts",
                "prior_loss_or_donation_carry_in",
            },
        )
        for key, value in raw["facts"].items():
            require(type(value) is str if key == "sex" else type(value) is bool)
    else:
        identifier(raw["issuer"])
        require(
            type(raw["considered_observations"]) is list
            and raw["considered_observations"]
            == sorted(set(raw["considered_observations"]))
        )
        for value in [raw["selected_observation"], *raw["considered_observations"]]:
            require(type(value) is str and HEX.fullmatch(value) is not None)
        require(raw["selected_observation"] in raw["considered_observations"])
    return copy.deepcopy(raw)


def active_facts(state, kind):
    superseded = {
        identity
        for record in state["eligibility"]
        for identity in record.get("supersedes", [])
    }
    return [
        r
        for r in state["eligibility"]
        if r.get("kind") == kind and digest(r) not in superseded
    ]


def observation(raw, state):
    keys = {
        "owner",
        "issuer",
        "kind",
        "document_type",
        "issue_date",
        "period_start",
        "period_end",
        "event_date",
        "settlement_date",
        "tax_year",
        "business_reference",
        "amount",
        "withholding",
        "provenance",
        "classification",
        "source",
        "review",
    }
    exact(raw, keys | ({"details"} if raw.get("kind") != "wages" else set()))
    out = copy.deepcopy(raw)
    require(raw["owner"] in {p["id"] for p in state["participants"]}, "owner_mismatch")
    require(raw["owner"] == state["taxpayer_id"], "owner_allocation_required")
    identifier(raw["issuer"])
    require(year(raw["tax_year"]) in state["years"], "year_mismatch")
    documents = {
        "wages": {"form_106", "a99_5", "payslip_ytd", "payslip_monthly"},
        "securities": {"form_867"},
        "donation": {"donation_receipt", "authority_donation", "forwarded_receipt"},
        "reserve": {"national_insurance_certificate", "employer_benefit_certificate"},
        "assistance": {"payment_record"},
        "advance_payment": {"tax_payment_receipt"},
    }
    require(raw["kind"] in documents, "unsupported_evidence_kind")
    require(raw["document_type"] in documents[raw["kind"]])
    require(raw["provenance"] in PROVENANCE)
    require(
        raw["classification"]
        in (
            {"taxable_wages", "unresolved"}
            if raw["kind"] == "wages"
            else {raw["kind"], "unresolved"}
        )
    )
    text(raw["business_reference"])
    date_field(raw["issue_date"])
    for k in ("event_date", "settlement_date"):
        date_field(raw[k])
    for k in ("period_start", "period_end"):
        require(raw[k] is not None)
        date_field(raw[k], raw["tax_year"])
    require(raw["period_start"] <= raw["period_end"], "invalid_period")
    for k in ("amount", "withholding"):
        out[k] = money(raw[k], raw["tax_year"])
    required_fields = {"amount", "withholding", "classification", "period"}
    if raw["kind"] != "wages":
        out["details"] = details(raw["kind"], raw["details"], raw["tax_year"])
        required_fields.add("details")
    reviewed_source(
        raw["source"],
        raw["review"],
        required_fields,
        raw["provenance"] == "verified_source",
    )
    return out


def economic_key(obs):
    keys = ("owner", "issuer", "tax_year", "kind")
    if obs["kind"] != "wages":
        keys += ("business_reference",)
    identity = {k: obs[k] for k in keys}
    if obs["kind"] == "advance_payment":
        identity.pop("business_reference")
        identity["payment_id"] = obs["details"]["payment_id"]
    return digest(identity)


def exact_sum(values):
    values = list(values)
    with localcontext() as ctx:
        ctx.prec = (
            max(
                (len(v.as_tuple().digits) + abs(v.as_tuple().exponent) for v in values),
                default=1,
            )
            + len(str(len(values)))
            + 2
        )
        return sum(values, Decimal(0))


def reconcile(state):
    """Retain observations; select one annual base or safe non-overlapping months."""
    old = {i["id"]: i for i in state["economic_items"]}
    grouped = {}
    for obs in state["observations"]:
        if obs["kind"] == "wages":
            grouped.setdefault(economic_key(obs), []).append(obs)
    items, conflicts, requirements = [], [], []
    for key, observations in sorted(grouped.items()):
        ordered = sorted(observations, key=digest)
        verified = [o for o in ordered if o["provenance"] == "verified_source"]
        annual = [o for o in verified if o["document_type"] in {"form_106", "a99_5"}]
        ytd = [o for o in verified if o["document_type"] == "payslip_ytd"]
        candidates = annual or (
            [o for o in ytd if o["period_end"] == max(v["period_end"] for v in ytd)]
            if ytd
            else []
        )
        resolutions = (
            [
                r
                for r in active_facts(state, "wage_resolution")
                if r["owner"] == verified[0]["owner"]
            ]
            if verified
            else []
        )
        resolutions = [
            r
            for r in resolutions
            if r["tax_year"] == verified[0]["tax_year"]
            and r["issuer"] == verified[0]["issuer"]
            and set(r["considered_observations"]) == {digest(o) for o in verified}
            and r["selected_observation"] in {digest(o) for o in candidates}
        ]
        require(len(resolutions) <= 1, "conflicting_resolutions")
        previous = old.get(key)
        if resolutions:
            previous = {"selected_observation": resolutions[0]["selected_observation"]}
        selected = next(
            (
                o
                for o in candidates
                if previous and digest(o) == previous.get("selected_observation")
            ),
            candidates[0] if candidates else None,
        )
        first = ordered[0]
        item = {
            "id": key,
            "owner": first["owner"],
            "issuer": first["issuer"],
            "tax_year": first["tax_year"],
            "kind": "wages",
            "classification": "unresolved",
            "amount": {
                "value_state": "unknown",
                "currency": "ILS",
                "tax_year": first["tax_year"],
            },
            "withholding": {
                "value_state": "unknown",
                "currency": "ILS",
                "tax_year": first["tax_year"],
            },
            "selected_observation": None,
            "observations": sorted({digest(o) for o in ordered}),
            "counting_decision": "unresolved",
            "exclusion_reason": None,
        }
        monthly = [
            o
            for o in verified
            if o["document_type"] == "payslip_monthly"
            and (
                not selected
                or annual
                or (
                    o["period_start"] >= selected["period_start"]
                    and o["period_end"] <= selected["period_end"]
                )
            )
        ]
        # Employment-period evidence does not require a complete payroll total.
        for certificate in annual:
            for field in ("period_start", "period_end"):
                outside = [
                    o
                    for o in monthly
                    if (
                        o[field] < certificate[field]
                        if field == "period_start"
                        else o[field] > certificate[field]
                    )
                ]
                if outside:
                    conflicts.append(
                        {
                            "economic_id": key,
                            "tax_year": first["tax_year"],
                            "field": field,
                            "status": "unresolved",
                            "observations": records(
                                [
                                    {"identity": digest(o), "value": o[field]}
                                    for o in [certificate, *outside]
                                ]
                            ),
                        }
                    )
        monthly_total = {}
        # Monthly duplicates corroborate only when period and figures agree.
        by_period = {}
        for o in monthly:
            by_period.setdefault((o["period_start"], o["period_end"]), []).append(o)
        unique = [values[0] for _, values in sorted(by_period.items())]
        clean = bool(unique) and all(
            len(
                {
                    canonical(
                        {k: o[k] for k in ("amount", "withholding", "classification")}
                    )
                    for o in values
                }
            )
            == 1
            for values in by_period.values()
        )
        clean = clean and all(
            a["period_end"] < b["period_start"] for a, b in pairwise(unique)
        )
        if clean and all(
            o["amount"]["value_state"] == "known"
            and o["withholding"]["value_state"] == "known"
            and o["classification"] == "taxable_wages"
            for o in unique
        ):
            for field in ("amount", "withholding"):
                monthly_total[field] = money(
                    {
                        "value_state": "known",
                        "amount": str(
                            exact_sum(Decimal(o[field]["amount"]) for o in unique)
                        ),
                        "currency": "ILS",
                        "tax_year": first["tax_year"],
                    }
                )
            monthly_total.update(
                classification="taxable_wages",
                counting_decision="once",
                period_start=unique[0]["period_start"],
                period_end=unique[-1]["period_end"],
            )
        elif monthly:
            conflicts.append(
                {
                    "economic_id": key,
                    "tax_year": first["tax_year"],
                    "field": "monthly_coverage",
                    "status": "unresolved",
                    "observations": sorted(digest(o) for o in monthly),
                }
            )
        if selected:
            item.update(
                {
                    k: selected[k]
                    for k in (
                        "classification",
                        "amount",
                        "withholding",
                        "period_start",
                        "period_end",
                        "event_date",
                        "settlement_date",
                    )
                }
            )
            item["selected_observation"] = digest(selected)
            item["counting_decision"] = "once"
            # Compare annual sources with the last YTD, never each successive YTD.
            comparators = annual + (
                [o for o in ytd if o["period_end"] == selected["period_end"]]
                if ytd
                else []
            )
            if (
                monthly_total
                and monthly_total["period_start"] == selected["period_start"]
                and monthly_total["period_end"] == selected["period_end"]
                and all(
                    date.fromisoformat(a["period_end"]) + timedelta(days=1)
                    == date.fromisoformat(b["period_start"])
                    for a, b in pairwise(unique)
                )
            ):
                comparators.append(
                    {
                        **monthly_total,
                        "source_observations": sorted(digest(o) for o in monthly),
                    }
                )
            for field in (
                "amount",
                "withholding",
                "classification",
                "period_start",
                "period_end",
            ):
                values = {canonical(o[field]) for o in comparators}
                if len(values) > 1:
                    conflicts.append(
                        {
                            "economic_id": key,
                            "tax_year": first["tax_year"],
                            "field": field,
                            "status": "unresolved",
                            "observations": records(
                                [
                                    {
                                        "identity": digest(o),
                                        "value": o[field],
                                        **(
                                            {
                                                "source_observations": o[
                                                    "source_observations"
                                                ]
                                            }
                                            if "source_observations" in o
                                            else {}
                                        ),
                                    }
                                    for o in comparators
                                ]
                            ),
                        }
                    )
        elif monthly_total:
            item.update(monthly_total)
        if resolutions:
            for conflict in conflicts:
                if conflict["economic_id"] == key:
                    conflict["status"] = "resolved"
                    conflict["resolution"] = digest(resolutions[0])
        item["calculation_completeness"] = (
            "conflict"
            if any(
                c["economic_id"] == key and c["status"] == "unresolved"
                for c in conflicts
            )
            else (
                "provisional"
                if item["amount"]["value_state"] == "known"
                and item["classification"] == "taxable_wages"
                else "incomplete"
            )
        )
        items.append(item)
        requirement = {
            "economic_id": key,
            "tax_year": first["tax_year"],
            "purpose": "filing_document_presence",
            "document_type": "form_106",
            "status": "missing",
            "source_references": [],
        }
        present = [digest(o) for o in verified if o["document_type"] == "form_106"]
        if present:
            requirement.update(status="resolved", source_references=sorted(present))
        prior = next(
            (r for r in state["requirements"] if r["economic_id"] == key), None
        )
        requirement["history"] = (prior or {}).get("history", [])
        if prior and prior["status"] != requirement["status"]:
            requirement["history"] = requirement["history"] + [
                {
                    "status": prior["status"],
                    "source_references": prior["source_references"],
                }
            ]
        requirement["filing_acceptability"] = "unverified"
        requirements.append(requirement)
    other = {}
    for obs in state["observations"]:
        if obs["kind"] != "wages":
            other.setdefault(economic_key(obs), []).append(obs)
    for key, observations in sorted(other.items()):
        verified = sorted(
            (o for o in observations if o["provenance"] == "verified_source"),
            key=digest,
        )
        selected = verified[0] if verified else min(observations, key=digest)
        item = {
            k: copy.deepcopy(selected[k])
            for k in (
                "owner",
                "issuer",
                "tax_year",
                "kind",
                "classification",
                "amount",
                "withholding",
                "period_start",
                "period_end",
                "event_date",
                "settlement_date",
                "details",
            )
        }
        item.update(
            id=key,
            observations=sorted(digest(o) for o in observations),
            selected_observation=digest(selected),
            counting_decision="once",
            exclusion_reason=None,
        )
        for field in (
            "amount",
            "withholding",
            "classification",
            "details",
            "event_date",
            "settlement_date",
            "period_start",
            "period_end",
        ):
            if len({canonical(o[field]) for o in verified}) > 1:
                conflicts.append(
                    {
                        "economic_id": key,
                        "tax_year": selected["tax_year"],
                        "field": field,
                        "status": "unresolved",
                        "observations": records(
                            [
                                {"identity": digest(o), "value": o[field]}
                                for o in verified
                            ]
                        ),
                    }
                )
        item["calculation_completeness"] = (
            "conflict"
            if any(c["economic_id"] == key for c in conflicts)
            else "provisional"
            if verified
            else "incomplete"
        )
        items.append(item)
    state.update(
        economic_items=items, conflicts=records(conflicts), requirements=requirements
    )


def validate_reference(result, state):
    require(
        type(result) is dict
        and result.get("tax_year") in state["years"]
        and result.get("owner") == state["taxpayer_id"],
        "result_owner_year_mismatch",
    )
    if result.get("purpose") == "unverifiable_result":
        exact(result, {"owner", "tax_year", "purpose", "status", "reason", "reference"})
        require(
            result["status"] == "stale"
            and result["reason"] == "freshness_unverifiable"
            and type(result["reference"]) is dict,
            "freshness_unverifiable",
        )
        return
    if result.get("purpose") == "annual_estimate":
        exact(
            result,
            {
                "owner",
                "tax_year",
                "purpose",
                "status",
                "freshness_version",
                "input_digest",
                "rule_pack_digest",
                "engine_version",
                "scenario",
                "artifact",
                "artifact_sha256",
            }
            | ({"reason"} if "reason" in result else set()),
        )
        require(
            result["freshness_version"] == FRESHNESS_VERSION
            and type(result["freshness_version"]) is int,
            "freshness_unverifiable",
        )
        for field in ("input_digest", "rule_pack_digest", "artifact_sha256"):
            require(
                type(result[field]) is str and HEX.fullmatch(result[field]) is not None,
                "freshness_unverifiable",
            )
        text(result["engine_version"])
        require(
            result["status"] in {"current", "stale"}
            and result["scenario"]
            in {None, "assistance_taxable", "assistance_excluded"}
            and result["artifact"]
            == f"calculations/{result['tax_year']}-{result['input_digest']}.json",
            "freshness_unverifiable",
        )
        return
    exact(
        result,
        {"owner", "tax_year", "purpose", "status", "input_digest"}
        | ({"reason"} if "reason" in result else set()),
    )
    require(
        type(result["input_digest"]) is str
        and HEX.fullmatch(result["input_digest"]) is not None,
        "freshness_unverifiable",
    )
    require(
        result.get("purpose") == "synthetic_freshness_probe" and state["synthetic"],
        "calculation_unavailable",
    )
    require(result.get("status") in {"current", "stale"})


def validate(state):
    no_floats(state)
    exact(
        state,
        {
            "schema_version",
            "case_id",
            "taxpayer_id",
            "revision",
            "preferred_language",
            "participants",
            "years",
            "authorized_search_scope",
            "observations",
            "economic_items",
            "conflicts",
            "requirements",
            "eligibility",
            "events",
            "attachments",
            "routes",
            "results",
            "assumptions",
            "next_actions",
            "synthetic",
        },
    )
    require(
        type(state["schema_version"]) is int
        and state["schema_version"] == SCHEMA_VERSION
    )
    identifier(state["case_id"])
    identifier(state["taxpayer_id"])
    require(type(state["revision"]) is int and state["revision"] >= 0)
    require(type(state["synthetic"]) is bool)
    text(state["preferred_language"])
    require(type(state["participants"]) is list and bool(state["participants"]))
    ids = []
    for p in state["participants"]:
        exact(p, {"id", "role", "authorized"})
        identifier(p["id"])
        require(
            p["role"] in {"taxpayer", "spouse"} and p["authorized"] is True,
            "authorization_required",
        )
        ids.append(p["id"])
    require(len(set(ids)) == len(ids) and state["taxpayer_id"] in ids)
    require(
        type(state["years"]) is list
        and state["years"]
        and len(set(state["years"])) == len(state["years"])
    )
    for y in state["years"]:
        year(y)
    for name in (
        "authorized_search_scope",
        "observations",
        "economic_items",
        "conflicts",
        "requirements",
        "eligibility",
        "events",
        "attachments",
        "routes",
        "results",
        "assumptions",
        "next_actions",
    ):
        require(type(state[name]) is list)
    for document in state["attachments"]:
        validate_document_reference(document, state)
    for collection in ("events", "routes", "eligibility"):
        for event in state[collection]:
            if type(event) is dict and event.get("record_type") == "workflow_event":
                require(workflow_event(event, state) == event, "noncanonical_event")
                expected = (
                    "eligibility"
                    if event["kind"] in {"equity", "dividend_match"}
                    else "routes"
                    if event["kind"] == "route"
                    else "events"
                )
                require(collection == expected, "event_collection_mismatch")
    for obs in state["observations"]:
        require(observation(obs, state) == obs, "noncanonical_observation")
    require(
        len({digest(o) for o in state["observations"]}) == len(state["observations"]),
        "duplicate_observation",
    )
    for record in state["eligibility"]:
        require(type(record) is dict, "invalid_eligibility")
        if record.get("kind") in {"profile", "wage_resolution"}:
            reviewed_fact(record, state)
    derived = copy.deepcopy(state)
    reconcile(derived)
    for name in ("economic_items", "conflicts", "requirements"):
        require(derived[name] == state[name], "derived_state_mismatch")
    for name in ("eligibility", "assumptions"):
        for value in state[name]:
            require(
                type(value) is dict
                and value.get("owner") in ids
                and value.get("tax_year") in state["years"],
                "owner_year_mismatch",
            )
    for result in state["results"]:
        validate_reference(result, state)
    return state


def projection(
    state, taxpayer, tax_year, rule_pack_digest, engine_version, scenario=None
):
    validate(state)
    require(
        taxpayer == state["taxpayer_id"] and tax_year in state["years"],
        "owner_year_mismatch",
    )
    require(
        type(rule_pack_digest) is str and HEX.fullmatch(rule_pack_digest) is not None,
        "freshness_unverifiable",
    )
    text(engine_version)

    def relevant(values):
        return [
            v
            for v in values
            if v.get("tax_year") == tax_year and v.get("owner", taxpayer) == taxpayer
        ]

    # Review metadata is audited in the ledger; numeric identity uses source data/provenance.
    observations = [
        {k: v for k, v in o.items() if k != "review"}
        for o in relevant(state["observations"])
    ]
    return {
        "freshness_version": FRESHNESS_VERSION,
        "case_id": state["case_id"],
        "taxpayer_id": taxpayer,
        "tax_year": tax_year,
        "economic_items": records(relevant(state["economic_items"])),
        "observations": records(observations),
        "conflicts": records(relevant(state["conflicts"])),
        "eligibility": records(
            relevant(state["eligibility"])
            + [
                {
                    "owner": r["owner"],
                    "tax_year": r["tax_year"],
                    "kind": "route_facts",
                    "checks": r["details"]["checks"],
                    "spouse": r["details"]["spouse"],
                    "provenance": r["provenance"],
                }
                for r in workflow_records(state, "route", tax_year, False)
                if r.get("record_type") == "workflow_event" and r["kind"] == "route"
            ]
        ),
        "scenario": scenario,
        "rule_pack_digest": rule_pack_digest,
        "engine_version": engine_version,
    }


def input_digest(
    state, taxpayer, tax_year, rule_pack_digest, engine_version, scenario=None
):
    return digest(
        projection(
            state, taxpayer, tax_year, rule_pack_digest, engine_version, scenario
        )
    )


def wage_summary(state):
    """Reconciliation output only; never a tax/refund estimate."""
    validate(state)
    output = []
    for y in sorted(state["years"]):
        items = [
            i
            for i in state["economic_items"]
            if i["tax_year"] == y and i["kind"] == "wages"
        ]
        ready = bool(items) and all(
            i["calculation_completeness"] == "provisional" for i in items
        )
        output.append(
            {
                "tax_year": y,
                "currency": "ILS",
                "direction": "wage_base",
                "wage_base": str(
                    exact_sum(Decimal(i["amount"]["amount"]) for i in items)
                )
                if ready
                else None,
                "status": "provisional_evidence_total" if ready else "unresolved",
                "filing_state": "unverified",
                "tax_estimate": None,
                "next_action": "Reconcile conflicting or incomplete wage evidence"
                if not ready
                else "Review calculation coverage, then use calculate for a supported 2025 case",
            }
        )
    return output


def safe_root(path):
    p = Path(path)
    require(p.is_absolute() and ".." not in p.parts, "unsafe_case_path")
    for ancestor in (p, *p.parents):
        require(not ancestor.is_symlink(), "unsafe_case_path")
    source = Path(__file__).resolve()
    forbidden = [source.parents[1], source.parents[3]]
    forbidden += [
        a for a in source.parents if (a / ".docs/plans/taxtidy-israel.md").is_file()
    ]
    require(
        not any(p == a or a in p.parents for a in forbidden),
        "case_inside_shared_source",
    )
    return p


@contextmanager
def case_directory(path):
    p = safe_root(path)
    fd = os.open(p, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        require(
            st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o700,
            "unsafe_case_permissions",
        )
        yield fd
    finally:
        os.close(fd)


@contextmanager
def private_target(fd, name, create=False):
    """Allow only managed files and the plan's private calculation path grammar."""
    if name in {"checkpoint.json", "summary.md"}:
        yield fd, name
        return
    if type(name) is str and re.fullmatch(
        r"documents/[0-9a-f]{32}/(?:report\.json|original\.pdf|working\.pdf)", name
    ):
        with document_target(fd, name) as target:
            yield target, name.split("/")[-1]
        return
    require(
        type(name) is str
        and re.fullmatch(r"calculations/[0-9]{4}-[0-9a-f]{64}\.json", name) is not None,
        "unsafe_case_path",
    )
    if create:
        try:
            os.mkdir("calculations", 0o700, dir_fd=fd)
            os.fsync(fd)
        except FileExistsError:
            pass
    child = os.open(
        "calculations", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
    )
    try:
        st = os.fstat(child)
        require(
            st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o700,
            "unsafe_case_permissions",
        )
        yield child, name.split("/")[1]
    finally:
        os.close(child)


def read_private(fd, name):
    with private_target(fd, name) as (target, filename):
        f = os.open(
            filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=target
        )
        with os.fdopen(f, "r", encoding="utf-8") as stream:
            st = os.fstat(stream.fileno())
            require(
                stat.S_ISREG(st.st_mode)
                and st.st_uid == os.getuid()
                and stat.S_IMODE(st.st_mode) == 0o600
                and st.st_nlink == 1,
                "unsafe_case_permissions",
            )
            require(st.st_size <= MAX_CASE_BYTES, "case_too_large")
            return stream.read()


def reject_constant(_):
    raise CaseError("invalid_json_number")


def unique_object(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, "duplicate_json_key")
        result[k] = v
    return result


def parse_json(content):
    try:
        result = json.loads(
            content, parse_constant=reject_constant, object_pairs_hook=unique_object
        )
    except (ValueError, TypeError, RecursionError):
        raise CaseError("invalid_json") from None
    no_floats(result)
    return result


def atomic_text(fd, name, content):
    require(len(content.encode("utf-8")) <= MAX_CASE_BYTES, "case_too_large")
    with private_target(fd, name, create=True) as (target, filename):
        try:
            st = os.stat(filename, dir_fd=target, follow_symlinks=False)
            require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, "unsafe_case_path")
        except FileNotFoundError:
            pass
        tmp = ".checkpoint." + uuid.uuid4().hex + ".tmp"
        f = os.open(
            tmp,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=target,
        )
        try:
            with os.fdopen(f, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, filename, src_dir_fd=target, dst_dir_fd=target)
            os.fsync(target)
        finally:
            try:
                os.unlink(tmp, dir_fd=target)
            except FileNotFoundError:
                pass


def initialize(path, taxpayer_id, years, language="he", synthetic=False):
    identifier(taxpayer_id)
    require(type(years) is list and years)
    for y in years:
        year(y)
    require(len(set(years)) == len(years))
    text(language)
    require(type(synthetic) is bool)
    p = safe_root(path)
    # Existing directories are never adopted or overwritten.
    p.mkdir(mode=0o700, parents=False, exist_ok=False)
    state = {
        "schema_version": SCHEMA_VERSION,
        "case_id": uuid.uuid4().hex,
        "taxpayer_id": taxpayer_id,
        "revision": 0,
        "preferred_language": language,
        "participants": [{"id": taxpayer_id, "role": "taxpayer", "authorized": True}],
        "years": sorted(years),
        "synthetic": synthetic,
    }
    for key in (
        "authorized_search_scope",
        "observations",
        "economic_items",
        "conflicts",
        "requirements",
        "eligibility",
        "events",
        "attachments",
        "routes",
        "results",
        "assumptions",
        "next_actions",
    ):
        state[key] = []
    validate(state)
    with case_directory(p) as fd:
        atomic_text(fd, "checkpoint.json", canonical(state).decode())
    return state


def load(path):
    with case_directory(path) as fd:
        return validate(parse_json(read_private(fd, "checkpoint.json")))


@contextmanager
def document_directory(path, create=False):
    with case_directory(path) as fd:
        if create:
            try:
                os.mkdir("documents", 0o700, dir_fd=fd)
            except FileExistsError:
                pass
        child = os.open(
            "documents", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
        )
        try:
            st = os.fstat(child)
            require(
                st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o700,
                "unsafe_case_permissions",
            )
            yield Path(path) / "documents"
        finally:
            os.close(child)


@contextmanager
def document_target(fd, name):
    opened = []
    try:
        for part in name.split("/")[:2]:
            child = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=opened[-1] if opened else fd,
            )
            opened.append(child)
            st = os.fstat(child)
            require(
                st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o700,
                "unsafe_case_permissions",
            )
        yield opened[-1]
    finally:
        for child in reversed(opened):
            os.close(child)


def validate_document_reference(record, state):
    exact(
        record,
        {
            "document_id",
            "owner",
            "tax_year",
            "purpose",
            "display_filename",
            "report_sha256",
        },
    )
    require(
        type(record["document_id"]) is str
        and re.fullmatch(r"[0-9a-f]{32}", record["document_id"]),
        "invalid_document_reference",
    )
    require(
        type(record["report_sha256"]) is str and HEX.fullmatch(record["report_sha256"]),
        "invalid_document_reference",
    )
    require(
        record["owner"] in {p["id"] for p in state["participants"]}
        and record["tax_year"] in state["years"],
        "owner_year_mismatch",
    )
    text(record["purpose"])
    text(record["display_filename"])


def document_content(fd, name):
    with private_target(fd, name) as (target, filename):
        child = os.open(
            filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=target
        )
        with os.fdopen(child, "rb") as stream:
            st = os.fstat(stream.fileno())
            require(
                stat.S_ISREG(st.st_mode)
                and st.st_uid == os.getuid()
                and stat.S_IMODE(st.st_mode) == 0o600
                and st.st_nlink == 1,
                "unsafe_case_permissions",
            )
            require(st.st_size <= MAX_CASE_BYTES, "document_too_large")
            data = stream.read(MAX_CASE_BYTES + 1)
            require(len(data) <= MAX_CASE_BYTES, "document_too_large")
            return data


def checked_document(fd, record):
    prefix = "documents/" + record["document_id"] + "/"
    data = document_content(fd, prefix + "report.json")
    require(
        hashlib.sha256(data).hexdigest() == record["report_sha256"], "document_changed"
    )
    report = parse_json(data.decode())
    require(
        all(
            report[k] == record[k]
            for k in ("document_id", "owner", "tax_year", "purpose", "display_filename")
        ),
        "document_identity_mismatch",
    )
    require(
        hashlib.sha256(document_content(fd, prefix + "original.pdf")).hexdigest()
        == report["original_sha256"],
        "document_changed",
    )
    if report["working_sha256"] is not None:
        require(
            hashlib.sha256(document_content(fd, prefix + "working.pdf")).hexdigest()
            == report["working_sha256"],
            "document_changed",
        )
    report["attachment_ready"] = document_ready(report)
    return report


def document_ready(report):
    review = report.get("review")
    if not report.get("structural_checks_passed") or not review:
        return False
    if (
        not review["content_matches"]
        or review["pages_visual_checked"] != list(range(1, report["page_count"] + 1))
        or not review["fields"]
    ):
        return False
    if report.get("signature_count", 0):
        expected = "working" if report["working_sha256"] else "original"
        return review["recipient_version"] == expected and (
            expected == "original" or report["conversion_authorized"]
        )
    return report["working_sha256"] is not None


def register_document(path, expected, report):
    record = {
        k: report[k]
        for k in ("document_id", "owner", "tax_year", "purpose", "display_filename")
    }
    record["report_sha256"] = digest(report)
    with locked(path) as fd:
        state = validate(parse_json(read_private(fd, "checkpoint.json")))
        require(
            state["case_id"] == expected["case_id"]
            and state["revision"] == expected["revision"],
            "revision_conflict",
        )
        validate_document_reference(record, state)
        checked_document(fd, record)
        require(
            not any(
                r["document_id"] == record["document_id"] for r in state["attachments"]
            ),
            "duplicate_document",
        )
        state["attachments"].append(record)
        state["revision"] += 1
        validate(state)
        atomic_text(fd, "checkpoint.json", canonical(state).decode())
        return state


def review_document(path, batch):
    exact(
        batch,
        {"case_id", "expected_revision", "document_id", "report_sha256", "review"},
    )
    with locked(path) as fd:
        state = validate(parse_json(read_private(fd, "checkpoint.json")))
        require(
            batch["case_id"] == state["case_id"]
            and type(batch["expected_revision"]) is int
            and batch["expected_revision"] == state["revision"],
            "revision_conflict",
        )
        record = next(
            (
                r
                for r in state["attachments"]
                if r["document_id"] == batch["document_id"]
            ),
            None,
        )
        require(
            record is not None and record["report_sha256"] == batch["report_sha256"],
            "document_changed",
        )
        report = checked_document(fd, record)
        old = canonical(report).decode()
        review = batch["review"]
        exact(
            review,
            {
                "reviewer",
                "reviewed_at",
                "owner",
                "tax_year",
                "purpose",
                "content_matches",
                "pages_visual_checked",
                "fields",
                "recipient_version",
            },
        )
        text(review["reviewer"])
        date_field(review["reviewed_at"])
        require(review["reviewed_at"] is not None, "review_required")
        require(
            all(review[k] == record[k] for k in ("owner", "tax_year", "purpose")),
            "owner_year_mismatch",
        )
        require(
            type(review["content_matches"]) is bool
            and type(review["pages_visual_checked"]) is list
            and all(
                type(p) is int and 1 <= p <= report.get("page_count", 0)
                for p in review["pages_visual_checked"]
            ),
            "review_required",
        )
        require(
            review["recipient_version"] in {"unconfirmed", "original", "working"},
            "review_required",
        )
        require(type(review["fields"]) is list, "review_required")
        for field in review["fields"]:
            exact(field, {"page", "field", "value"})
            require(
                type(field["page"]) is int
                and field["page"] in review["pages_visual_checked"],
                "review_required",
            )
            text(field["field"])
            money(field["value"], record["tax_year"])
        report["review"] = copy.deepcopy(review)
        report["recipient_acceptance"] = review["recipient_version"]
        report["attachment_ready"] = document_ready(report)
        name = "documents/" + record["document_id"] + "/report.json"
        record["report_sha256"] = digest(report)
        state["revision"] += 1
        validate(state)
        atomic_text(fd, name, canonical(report).decode())
        try:
            atomic_text(fd, "checkpoint.json", canonical(state).decode())
        except Exception:
            atomic_text(fd, name, old)
            raise
        return {"ok": True, "revision": state["revision"], "document": report}


@contextmanager
def locked(path):
    with case_directory(path) as fd:
        lock = os.open(
            "checkpoint.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=fd
        )
        try:
            st = os.fstat(lock)
            require(
                stat.S_ISREG(st.st_mode)
                and st.st_nlink == 1
                and st.st_uid == os.getuid()
                and stat.S_IMODE(st.st_mode) == 0o600,
                "unsafe_case_permissions",
            )
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield fd
        finally:
            os.close(lock)


def import_evidence(path, batch):
    exact(
        batch,
        {"case_id", "expected_revision", "observations"}
        | ({"eligibility"} if "eligibility" in batch else set()),
    )
    require(
        type(batch["expected_revision"]) is int and type(batch["observations"]) is list
    )
    with locked(path) as fd:
        before = validate(parse_json(read_private(fd, "checkpoint.json")))
        require(batch["case_id"] == before["case_id"], "case_mismatch")
        require(batch["expected_revision"] == before["revision"], "revision_conflict")
        state = copy.deepcopy(before)
        incoming = [observation(o, state) for o in batch["observations"]]
        state["observations"] = records(state["observations"] + incoming)
        if "eligibility" in batch:
            require(type(batch["eligibility"]) is list)
            facts = [reviewed_fact(raw, state) for raw in batch["eligibility"]]
            state["eligibility"] = records(state["eligibility"] + facts)
        reconcile(state)
        changed_years = []
        for y in state["years"]:
            # Pure comparison context, never an enabled tax rule pack or tax estimate.
            marker = "0" * 64
            if input_digest(
                before, before["taxpayer_id"], y, marker, ENGINE_VERSION
            ) != input_digest(state, state["taxpayer_id"], y, marker, ENGINE_VERSION):
                changed_years.append(y)
        for result in state["results"]:
            if (
                result["tax_year"] in changed_years
                and result.get("purpose") != "unverifiable_result"
            ):
                result["status"] = "stale"
                result["reason"] = "stale_calculation"
        if state != before:
            state["revision"] += 1
            validate(state)
            serialized = canonical(state)
            require(len(serialized) <= MAX_CASE_BYTES, "case_too_large")
            if changed_years:
                try:
                    read_private(fd, "summary.md")
                except FileNotFoundError:
                    pass
                else:
                    atomic_text(
                        fd,
                        "summary.md",
                        "Recalculation required. Previous estimates are unavailable.\n",
                    )
            atomic_text(fd, "checkpoint.json", serialized.decode())
        return state


def load_rules():
    path = Path(__file__).resolve().parents[1] / "assets/rules/2025.json"
    pack = parse_json(path.read_text(encoding="utf-8"))
    require(
        pack.get("schema_version") == 1
        and pack.get("tax_year") == 2025
        and pack.get("engine_version") == ENGINE_VERSION,
        "freshness_unverifiable",
    )
    return pack


def calculation_inputs(state, tax_year):
    validate(state)
    require(
        type(tax_year) is int and tax_year == 2025 and tax_year in state["years"],
        "unsupported_tax_year",
    )
    require(
        not any(
            c["tax_year"] == tax_year and c["status"] == "unresolved"
            for c in state["conflicts"]
        ),
        "unresolved_income_conflict",
    )
    require(
        not any(
            e.get("record_type") == "workflow_event"
            and e.get("kind") in {"equity", "dividend_match"}
            and e.get("tax_year") == tax_year
            for e in state["eligibility"]
        ),
        "unsupported_equity_facts",
    )
    for route in workflow_records(state, "route", tax_year, False):
        if (
            route.get("record_type") == "workflow_event"
            and route["tax_year"] == tax_year
        ):
            require(
                all(
                    route["details"]["checks"][k] is False
                    for k in (
                        "self_employment",
                        "foreign_income",
                        "foreign_assets",
                        "rental_income",
                        "retirement",
                        "residence_change",
                        "family_change",
                    )
                ),
                "unsupported_or_incomplete_route_facts",
            )
    profiles = [
        v
        for v in active_facts(state, "profile")
        if v["tax_year"] == tax_year and v["owner"] == state["taxpayer_id"]
    ]
    require(len(profiles) == 1, "missing_coverage_profile")
    expected = {
        "resident_full_year": True,
        "sex": "male",
        "adult_under_60": True,
        "unmarried": True,
        "all_income_declared": True,
        "all_payments_declared": True,
        "other_entitlements_or_deductions": False,
        "pension_or_insurance_contributions": False,
        "foreign_facts": False,
        "prior_loss_or_donation_carry_in": False,
    }
    require(profiles[0]["facts"] == expected, "unsupported_or_incomplete_profile")
    items = [i for i in state["economic_items"] if i["tax_year"] == tax_year]
    require(
        items and all(i["calculation_completeness"] == "provisional" for i in items),
        "incomplete_income_evidence",
    )
    require(
        all(
            i["classification"]
            == ("taxable_wages" if i["kind"] == "wages" else i["kind"])
            or (i["kind"] == "assistance" and i["classification"] == "unresolved")
            for i in items
        ),
        "unresolved_income_classification",
    )
    return {
        "case_id": state["case_id"],
        "taxpayer_id": state["taxpayer_id"],
        "tax_year": tax_year,
        "items": copy.deepcopy(items),
        "evidence_references": [
            digest(o) for o in state["observations"] if o["tax_year"] == tax_year
        ]
        + [digest(profiles[0])],
    }


def current_result(fd, state, tax_year, pack, scenario=None):
    """Only monetary publication/read boundary; recompute, never trust a current flag."""
    calculation_inputs(state, tax_year)
    references = [
        r
        for r in state["results"]
        if r["tax_year"] == tax_year
        and r.get("purpose") == "annual_estimate"
        and r.get("scenario") == scenario
        and r.get("status") == "current"
    ]
    require(len(references) == 1, "stale_calculation")
    ref = references[0]
    fingerprint = input_digest(
        state, state["taxpayer_id"], tax_year, digest(pack), ENGINE_VERSION, scenario
    )
    require(
        ref["freshness_version"] == FRESHNESS_VERSION
        and ref["input_digest"] == fingerprint
        and ref["rule_pack_digest"] == digest(pack)
        and ref["engine_version"] == ENGINE_VERSION,
        "stale_calculation",
    )
    try:
        content = read_private(fd, ref["artifact"])
        artifact = parse_json(content)
    except (OSError, ValueError, UnicodeError):
        raise CaseError("freshness_unverifiable") from None
    require(
        hashlib.sha256(content.encode("utf-8")).hexdigest() == ref["artifact_sha256"],
        "freshness_unverifiable",
    )
    exact(
        artifact,
        {
            "case_id",
            "taxpayer_id",
            "tax_year",
            "freshness_version",
            "input_digest",
            "rule_pack_digest",
            "engine_version",
            "scenario",
            "estimate",
        },
    )
    for key, value in {
        "case_id": state["case_id"],
        "taxpayer_id": state["taxpayer_id"],
        "tax_year": tax_year,
        "freshness_version": FRESHNESS_VERSION,
        "input_digest": fingerprint,
        "rule_pack_digest": digest(pack),
        "engine_version": ENGINE_VERSION,
        "scenario": scenario,
    }.items():
        require(artifact[key] == value, "freshness_unverifiable")
    require(
        artifact["estimate"].get("tax_year") == tax_year
        and artifact["estimate"].get("scenario") == scenario
        and artifact["estimate"].get("currency") == "ILS",
        "freshness_unverifiable",
    )
    return artifact["estimate"]


def _calculate_case(path, tax_year, scenario=None, publish=None):
    """Compute outside lock, then recheck and publish within the case lock."""
    import calculate as calculator

    pack = load_rules()
    with locked(path) as fd:
        snapshot = validate(parse_json(read_private(fd, "checkpoint.json")))
        inputs = calculation_inputs(snapshot, tax_year)
        fingerprint = input_digest(
            snapshot,
            snapshot["taxpayer_id"],
            tax_year,
            digest(pack),
            ENGINE_VERSION,
            scenario,
        )
    try:
        estimate = calculator.compute(inputs, pack, scenario)
    except calculator.CalculationError as exc:
        raise CaseError(str(exc)) from None
    with locked(path) as fd:
        state = validate(parse_json(read_private(fd, "checkpoint.json")))
        current_pack = load_rules()
        require(
            state["revision"] == snapshot["revision"]
            and digest(current_pack) == digest(pack)
            and input_digest(
                state,
                state["taxpayer_id"],
                tax_year,
                digest(current_pack),
                ENGINE_VERSION,
                scenario,
            )
            == fingerprint,
            "calculation_inputs_changed",
        )
        calculation_inputs(state, tax_year)
        artifact = {
            "case_id": state["case_id"],
            "taxpayer_id": state["taxpayer_id"],
            "tax_year": tax_year,
            "freshness_version": FRESHNESS_VERSION,
            "input_digest": fingerprint,
            "rule_pack_digest": digest(pack),
            "engine_version": ENGINE_VERSION,
            "scenario": scenario,
            "estimate": estimate,
        }
        artifact_bytes = canonical(artifact)
        artifact_hash = hashlib.sha256(artifact_bytes).hexdigest()
        name = f"calculations/{tax_year}-{fingerprint}.json"
        for ref in state["results"]:
            if ref.get("purpose") == "annual_estimate" and ref["tax_year"] == tax_year:
                ref["status"] = "stale"
                ref["reason"] = "superseded_calculation"
        reference = {
            "owner": state["taxpayer_id"],
            "tax_year": tax_year,
            "purpose": "annual_estimate",
            "status": "current",
            "freshness_version": FRESHNESS_VERSION,
            "input_digest": fingerprint,
            "rule_pack_digest": digest(pack),
            "engine_version": ENGINE_VERSION,
            "scenario": scenario,
            "artifact": name,
            "artifact_sha256": artifact_hash,
        }
        state["results"].append(reference)
        state["revision"] += 1
        validate(state)
        serialized = canonical(state)
        require(len(serialized) <= MAX_CASE_BYTES, "case_too_large")
        atomic_text(fd, name, artifact_bytes.decode("utf-8"))
        atomic_text(
            fd,
            "summary.md",
            "Recalculation required. Previous estimates are unavailable.\n",
        )
        atomic_text(fd, "checkpoint.json", serialized.decode("utf-8"))
        checked = current_result(fd, state, tax_year, current_pack, scenario)
        public = {
            "ok": True,
            "case_id": state["case_id"],
            "revision": state["revision"],
            "result_reference": copy.deepcopy(reference),
            "estimate": checked,
        }
        atomic_text(
            fd, "summary.md", json.dumps(public, ensure_ascii=False, indent=2) + "\n"
        )
        if publish is not None:
            publish(public)
        return public


def calculate_case(path, tax_year, scenario=None, publish=None):
    try:
        return _calculate_case(path, tax_year, scenario, publish)
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        # A failed freshness/coverage check cannot leave a managed amount visible.
        with locked(path) as fd:
            atomic_text(
                fd,
                "summary.md",
                "Recalculation required. Previous estimates are unavailable.\n",
            )
        raise


ROUTE_CHECKS = {
    "self_employment",
    "foreign_income",
    "foreign_assets",
    "securities",
    "rental_income",
    "retirement",
    "residence_change",
    "family_change",
    "prior_filing",
    "representation",
}
SPOUSE_CHECKS = {
    "registered_spouse",
    "marriage_year",
    "joint_income",
    "separate_income",
    "ownership",
    "account_join_date",
    "declarations",
    "signatures",
    "other_return",
    "form_4430",
}


def workflow_event(raw, state):
    exact(
        raw,
        {
            "record_type",
            "owner",
            "tax_year",
            "kind",
            "form",
            "draft_version",
            "event_date",
            "observed_at",
            "reference",
            "provenance",
            "source",
            "review",
            "details",
        }
        | ({"supersedes"} if "supersedes" in raw else set()),
    )
    require(raw["record_type"] == "workflow_event")
    require(
        raw["owner"] == state["taxpayer_id"] and raw["tax_year"] in state["years"],
        "owner_year_mismatch",
    )
    require(type(raw["tax_year"]) is int)
    for key in ("form", "draft_version", "reference"):
        text(raw[key])
    for key in ("event_date", "observed_at"):
        require(raw[key] is not None)
        date_field(raw[key])
    require(raw["event_date"] <= raw["observed_at"], "unobserved_future_event")
    require(raw["provenance"] in {"verified_source", "user_statement"})
    reviewed_source(
        raw["source"], raw["review"], {"event"}, raw["provenance"] == "verified_source"
    )
    if "supersedes" in raw:
        require(type(raw["supersedes"]) is list)
        for identity in raw["supersedes"]:
            previous = next(
                (
                    e
                    for collection in ("events", "routes", "eligibility")
                    for e in state[collection]
                    if digest(e) == identity
                ),
                None,
            )
            require(
                previous is not None
                and all(
                    previous.get(k) == raw[k]
                    for k in ("owner", "tax_year", "kind", "form", "draft_version")
                ),
                "invalid_event_supersession",
            )
            if raw["kind"] in {"donation_registry", "filed_donation", "payroll_relief"}:
                keys = (
                    ("payer", "relief", "status")
                    if raw["kind"] == "payroll_relief"
                    else ("issuer", "receipt_id")
                )
                require(
                    type(raw["details"]) is dict
                    and all(
                        previous["details"][key] == raw["details"].get(key)
                        for key in keys
                    ),
                    "invalid_event_supersession",
                )
            require(
                previous.get("provenance") != "verified_source"
                or raw["provenance"] == "verified_source",
                "review_required",
            )
    out = copy.deepcopy(raw)
    d = out["details"]
    kind = raw["kind"]
    if kind == "return":
        exact(d, {"status"})
        require(
            d["status"]
            in {
                "case_opening_requested",
                "collection",
                "draft_saved",
                "validation_passed",
                "transmitted",
                "filing_acknowledged",
                "cancelled",
                "assessment_issued",
            }
        )
    elif kind in {"donation_registry", "filed_donation"}:
        filed = kind == "filed_donation"
        exact(
            d,
            {"issuer", "receipt_id", "status"}
            | ({"field", "reported_total"} if filed else set()),
        )
        identifier(d["issuer"])
        text(d["receipt_id"])
        if filed:
            require(raw["form"] in {"135", "1301"})
            require(d["status"] in {"included", "omitted"})
            text(d["field"])
            d["reported_total"] = money(d["reported_total"], raw["tax_year"])
            require(
                d["reported_total"]["value_state"] == "known"
                and Decimal(d["reported_total"]["amount"]) >= 0
            )
        else:
            require(raw["form"] == "donations")
            require(
                d["status"] in {"associated", "missing", "wrong_taxpayer", "cancelled"}
            )
        reviewed_source(
            raw["source"],
            raw["review"],
            {"event", "receipt_match", "filed_calculation"}
            if filed
            else {"event", "registry_entry"},
        )
        require(raw["provenance"] == "verified_source", "review_required")
    elif kind == "payroll_relief":
        exact(d, {"payer", "relief", "status"})
        require(raw["form"] in {"coordination", "relief"})
        identifier(d["payer"])
        text(d["relief"])
        require(
            d["status"] in {"eligibility_verified", "certificate_issued", "applied"}
        )
    elif kind == "attachment":
        exact(d, {"filename", "sha256", "purpose", "status"})
        text(d["filename"])
        require(
            not any(c in d["filename"] for c in ("/", "\\", "\n", "\r", "\x00")),
            "unsafe_filename",
        )
        require(type(d["sha256"]) is str and HEX.fullmatch(d["sha256"]) is not None)
        text(d["purpose"])
        require(d["status"] in {"uploaded", "rejected", "accepted"})
    elif kind == "inquiry":
        exact(
            d,
            {
                "status",
                "recipient",
                "purpose",
                "existing_reference",
                "authorization_reference",
            },
        )
        for key in ("recipient", "purpose"):
            text(d[key])
        require(d["status"] in {"draft", "sent", "acknowledged", "closed"})
        for key in ("existing_reference", "authorization_reference"):
            if d[key] is not None:
                text(d[key])
        if d["status"] != "draft":
            require(
                d["authorization_reference"] is not None, "send_authorization_required"
            )
    elif kind == "portal_block":
        exact(d, {"message", "existing_inquiry_reference"})
        text(d["message"])
        if d["existing_inquiry_reference"] is not None:
            text(d["existing_inquiry_reference"])
    elif kind == "settlement":
        exact(d, {"status", "amount"})
        require(d["status"] in {"refund_received", "payment_made"})
        d["amount"] = money(d["amount"], raw["tax_year"])
        require(
            d["amount"]["value_state"] == "known"
            and Decimal(d["amount"]["amount"]) >= 0
        )
    elif kind == "deadline":
        exact(
            d,
            {
                "category",
                "base_deadline",
                "extension_deadline",
                "extension_applicable",
                "extension_reference",
                "source_url",
            },
        )
        require(
            d["category"]
            in {"refund_claim", "mandatory_return", "coordination", "payment"}
        )
        require(d["base_deadline"] is not None)
        date_field(d["base_deadline"])
        official_url(d["source_url"])
        require(type(d["extension_applicable"]) is bool)
        if d["extension_deadline"] is not None:
            date_field(d["extension_deadline"])
            text(d["extension_reference"])
            require(d["extension_deadline"] >= d["base_deadline"])
        else:
            require(not d["extension_applicable"] and d["extension_reference"] is None)
    elif kind == "route":
        exact(
            d, {"route_status", "filing_obligation", "checks", "spouse", "rules_source"}
        )
        require(raw["form"] in {"135", "1301", "coordination", "relief", "correction"})
        require(d["route_status"] in {"candidate", "unresolved", "verified"})
        require(d["filing_obligation"] in {"required", "not_required", "unresolved"})
        exact(d["checks"], ROUTE_CHECKS)
        require(all(type(v) is bool or v == "unknown" for v in d["checks"].values()))
        exact(d["spouse"], SPOUSE_CHECKS)
        for value in d["spouse"].values():
            text(value)
        if d["rules_source"] is not None:
            exact(d["rules_source"], {"url", "tax_year", "verified_at", "field"})
            official_url(d["rules_source"]["url"])
            require(d["rules_source"]["tax_year"] == raw["tax_year"])
            require(d["rules_source"]["verified_at"] is not None)
            date_field(d["rules_source"]["verified_at"])
            require(d["rules_source"]["verified_at"] <= raw["observed_at"])
            text(d["rules_source"]["field"])
        if d["route_status"] == "verified":
            require(
                raw["provenance"] == "verified_source"
                and d["rules_source"] is not None
                and "unknown" not in d["checks"].values()
                and "unknown" not in d["spouse"].values()
                and d["filing_obligation"] != "unresolved",
                "route_verification_required",
            )
    elif kind == "forecast":
        exact(d, {"payers", "assumptions", "payroll_relief"})
        require(type(d["payers"]) is list and d["payers"])
        for payer in d["payers"]:
            exact(
                payer,
                {
                    "issuer",
                    "as_of",
                    "actual_income",
                    "withheld_to_date",
                    "remaining_income",
                    "bonus",
                },
            )
            identifier(payer["issuer"])
            require(payer["as_of"] is not None)
            date_field(payer["as_of"], raw["tax_year"])
            for field in (
                "actual_income",
                "withheld_to_date",
                "remaining_income",
                "bonus",
            ):
                payer[field] = money(payer[field], raw["tax_year"])
                require(
                    payer[field]["value_state"] == "known"
                    and Decimal(payer[field]["amount"]) >= 0
                )
        require(
            len({p["issuer"] for p in d["payers"]}) == len(d["payers"]),
            "duplicate_payer",
        )
        for field in ("assumptions", "payroll_relief"):
            require(type(d[field]) is list)
            for value in d[field]:
                text(value)
        require(bool(d["assumptions"]), "forecast_assumptions_required")
    elif kind == "dividend_match":
        exact(d, {"institution", "payment_reference", "observations"})
        text(d["institution"])
        text(d["payment_reference"])
        require(
            raw["provenance"] == "verified_source"
            and "payment_link" in raw["review"]["fields_checked"],
            "review_required",
        )
        require(type(d["observations"]) is list and len(d["observations"]) >= 2)
        require(all(type(h) is str and HEX.fullmatch(h) for h in d["observations"]))
        require(len(set(d["observations"])) == len(d["observations"]))
        d["observations"] = sorted(d["observations"])
        for identity in d["observations"]:
            linked = next(
                (
                    e
                    for e in state["eligibility"]
                    if type(e) is dict
                    and e.get("record_type") == "workflow_event"
                    and e.get("kind") == "equity"
                    and digest(e) == identity
                ),
                None,
            )
            require(linked is not None, "invalid_dividend_link")
            linked = workflow_event(linked, state)
            require(
                linked["owner"] == raw["owner"]
                and linked["tax_year"] == raw["tax_year"]
                and linked["provenance"] == "verified_source"
                and linked["details"]["event_type"] == "dividend"
                and d["institution"]
                in {linked["details"]["broker"], linked["details"]["trustee"]},
                "invalid_dividend_link",
            )
    elif kind == "equity":
        date_field(raw["event_date"], raw["tax_year"])
        exact(
            d,
            {
                "event_type",
                "plan_type",
                "employer",
                "administrator",
                "broker",
                "trustee",
                "plan_id",
                "account",
                "security",
                "quantity",
                "gross",
                "withholding",
                "payroll_component",
                "adjusted_basis",
                "payroll_item",
                "destination",
                "from_account",
                "to_account",
            },
        )
        require(
            d["event_type"]
            in {"grant", "vest", "purchase", "sale", "transfer", "dividend"}
        )
        require(d["plan_type"] in {"RSU", "ESPP"})
        for field in (
            "employer",
            "administrator",
            "broker",
            "trustee",
            "plan_id",
            "account",
            "security",
        ):
            text(d[field])
        require(
            type(d["quantity"]) is str
            and MONEY.fullmatch(d["quantity"]) is not None
            and len(d["quantity"]) <= 50
            and Decimal(d["quantity"]) >= 0
        )
        for field in ("payroll_item", "destination", "from_account", "to_account"):
            if d[field] is not None:
                text(d[field])
        for field in ("gross", "withholding", "payroll_component", "adjusted_basis"):
            value = d[field]
            require(
                type(value) is dict
                and type(value.get("currency")) is str
                and re.fullmatch(r"[A-Z]{3}", value["currency"]) is not None
            )
            currency = value["currency"]
            d[field] = money({**value, "currency": "ILS"}, raw["tax_year"])
            d[field]["currency"] = currency
    else:
        raise CaseError("unsupported_event_kind")
    return out


def official_url(value):
    from urllib.parse import urlsplit

    text(value)
    parsed = urlsplit(value)
    require(
        parsed.scheme == "https"
        and parsed.hostname in {"www.gov.il", "gov.il"}
        and parsed.username is None
        and parsed.password is None,
        "official_source_required",
    )


def record_event(path, batch):
    exact(batch, {"case_id", "expected_revision", "event"})
    require(type(batch["expected_revision"]) is int)
    with locked(path) as fd:
        before = validate(parse_json(read_private(fd, "checkpoint.json")))
        require(batch["case_id"] == before["case_id"], "case_mismatch")
        require(batch["expected_revision"] == before["revision"], "revision_conflict")
        event = workflow_event(batch["event"], before)
        state = copy.deepcopy(before)
        collection = (
            "eligibility"
            if event["kind"] in {"equity", "dividend_match"}
            else "routes"
            if event["kind"] == "route"
            else "events"
        )
        state[collection] = records(state[collection] + [event])
        if state == before:
            return state
        changed = [
            y
            for y in state["years"]
            if input_digest(before, before["taxpayer_id"], y, "0" * 64, ENGINE_VERSION)
            != input_digest(state, state["taxpayer_id"], y, "0" * 64, ENGINE_VERSION)
        ]
        for result in state["results"]:
            if (
                result["tax_year"] in changed
                and result.get("purpose") != "unverifiable_result"
            ):
                result.update(status="stale", reason="stale_calculation")
        state["revision"] += 1
        validate(state)
        serialized = canonical(state)
        require(len(serialized) <= MAX_CASE_BYTES, "case_too_large")
        atomic_text(
            fd,
            "summary.md",
            "Recalculation required. Previous estimates are unavailable.\n",
        )
        atomic_text(fd, "checkpoint.json", serialized.decode())
        return state


def workflow_records(state, kind, tax_year, verified=True):
    values = [
        r
        for collection in ("events", "routes", "eligibility")
        for r in state[collection]
        if type(r) is dict
        and r.get("record_type") == "workflow_event"
        and r["kind"] == kind
        and r["tax_year"] == tax_year
    ]
    superseded = {identity for r in values for identity in r.get("supersedes", [])}
    return [
        r
        for r in values
        if digest(r) not in superseded
        and (not verified or r["provenance"] == "verified_source")
    ]


def event_projection(event):
    return {
        k: copy.deepcopy(v) for k, v in event.items() if k not in {"source", "review"}
    } | {"source_reference": digest(event)}


def filing_projection(state, tax_year):
    events = workflow_records(state, "return", tax_year)
    contexts = {(e["form"], e["draft_version"]) for e in events}
    rows = []
    for form, version in sorted(contexts):
        matching = [
            e for e in events if e["form"] == form and e["draft_version"] == version
        ]
        statuses = {e["details"]["status"] for e in matching}
        status = (
            "cancelled"
            if "cancelled" in statuses
            else "filing_completed"
            if "filing_acknowledged" in statuses
            else (
                "transmitted_acknowledgment_unverified"
                if "transmitted" in statuses
                else "validated"
                if "validation_passed" in statuses
                else "draft"
                if "draft_saved" in statuses
                else "assessment_issued_filing_unverified"
                if "assessment_issued" in statuses
                else "case_opening_requested"
                if "case_opening_requested" in statuses
                else "collection"
            )
        )
        rows.append(
            {
                "form": form,
                "draft_version": version,
                "status": status,
                "observed_statuses": sorted(statuses),
                "evidence": [digest(e) for e in matching],
                "acknowledgments": [
                    event_projection(e)
                    for e in matching
                    if e["details"]["status"] == "filing_acknowledged"
                ],
            }
        )
    overall = "unverified"
    active = [r for r in rows if r["status"] != "cancelled"]
    if rows:
        overall = (
            "cancelled"
            if not active
            else "filing_completed"
            if all(r["status"] == "filing_completed" for r in active)
            else (
                "draft"
                if any(r["status"] in {"draft", "validated"} for r in active)
                else "incomplete_filing_evidence"
            )
        )
    attachments = [
        {
            "tax_year": tax_year,
            "form": e["form"],
            "draft_version": e["draft_version"],
            **e["details"],
            "observed_at": e["observed_at"],
            "reference": e["reference"],
            "source_reference": digest(e),
        }
        for e in workflow_records(state, "attachment", tax_year)
    ]
    return {
        "state": overall,
        "returns": rows,
        "attachments": attachments,
        "settlements": [
            event_projection(e) for e in workflow_records(state, "settlement", tax_year)
        ],
        "inquiries": [
            event_projection(e) for e in workflow_records(state, "inquiry", tax_year)
        ],
        "user_statements": [
            digest(e)
            for e in workflow_records(state, "return", tax_year, False)
            if e["provenance"] == "user_statement"
        ],
    }


def donation_projection(state, tax_year, filing):
    registry = workflow_records(state, "donation_registry", tax_year)
    filed = workflow_records(state, "filed_donation", tax_year)
    observations = {
        digest(o): o
        for o in state["observations"]
        if o["kind"] == "donation" and o["tax_year"] == tax_year
    }
    rows = []
    for item in state["economic_items"]:
        obs = observations.get(item["selected_observation"])
        if obs is None:
            continue
        issuer, receipt = obs["issuer"], obs["business_reference"]
        checks = [
            e
            for e in registry
            if (e["details"]["issuer"], e["details"]["receipt_id"]) == (issuer, receipt)
        ]
        latest = max((e["observed_at"] for e in checks), default=None)
        current = {e["details"]["status"] for e in checks if e["observed_at"] == latest}
        returns = []
        for row in filing["returns"]:
            if row["status"] != "filing_completed":
                continue
            matches = [
                e
                for e in filed
                if (e["form"], e["draft_version"])
                == (row["form"], row["draft_version"])
                and (e["details"]["issuer"], e["details"]["receipt_id"])
                == (issuer, receipt)
            ]
            findings = {canonical(e["details"]) for e in matches}
            returns.append(
                {
                    "form": row["form"],
                    "draft_version": row["draft_version"],
                    "status": matches[0]["details"]["status"]
                    if len(findings) == 1
                    else "unresolved",
                    "evidence": [event_projection(e) for e in matches],
                }
            )
        rows.append(
            {
                "issuer": issuer,
                "receipt_id": receipt,
                "amount": item["amount"],
                "evidence_status": item["calculation_completeness"],
                "payroll_applied_credit": (
                    item["details"]["payroll_applied_credit"]
                    if item["calculation_completeness"] == "provisional"
                    else None
                ),
                "registry_status": next(iter(current))
                if len(current) == 1
                else "unverified"
                if not current
                else "unresolved",
                "registry_evidence": [event_projection(e) for e in checks],
                "filed_returns": returns,
            }
        )
    return rows


def equity_projection(state, tax_year):
    events = workflow_records(state, "equity", tax_year, False)
    rows, questions, dividends = [], [], {}
    for e in events:
        d = e["details"]
        row = {
            "event_type": d["event_type"],
            "plan_type": d["plan_type"],
            "event_date": e["event_date"],
            "source_reference": digest(e),
            "wage_component_counted_again": False,
            "status": "recorded_guidance_only",
        }
        if d["event_type"] == "sale":
            wage = next(
                (
                    i
                    for i in state["economic_items"]
                    if i["id"] == d["payroll_item"]
                    and i["tax_year"] == tax_year
                    and i["kind"] == "wages"
                ),
                None,
            )
            linked = (
                e["provenance"] == "verified_source"
                and wage is not None
                and d["payroll_component"]["value_state"] == "known"
                and d["payroll_component"]["currency"] == "ILS"
                and Decimal(d["payroll_component"]["amount"])
                <= Decimal(wage["amount"].get("amount", "-1"))
            )
            row["status"] = (
                "payroll_component_already_in_wages"
                if linked
                else "payroll_link_unresolved"
            )
            questions.append(
                {
                    "institution": d["trustee"],
                    "question": "Confirm payroll inclusion, adjusted cost basis and separate capital gain/loss for this sale.",
                    "event": digest(e),
                }
            )
        elif d["event_type"] == "vest":
            row["status"] = "vesting_does_not_prove_sale"
        elif d["event_type"] == "dividend":
            dividends[digest(e)] = e
            row.update(
                business_reference=e["reference"],
                account=d["account"],
                match_evidence=[],
            )
        elif d["event_type"] == "transfer" and (
            d["from_account"] is None or d["to_account"] is None
        ):
            questions.append(
                {
                    "institution": d["broker"],
                    "question": "Identify old/new accounts and reconcile holdings and cash during migration.",
                    "event": digest(e),
                }
            )
        rows.append(row)
    links, claims, payments = [], {}, {}
    for link in workflow_records(state, "dividend_match", tax_year):
        d = link["details"]
        if not all(h in dividends for h in d["observations"]):
            continue
        identity = digest(d)
        payment = (
            link["owner"],
            link["tax_year"],
            d["institution"],
            d["payment_reference"],
        )
        payments.setdefault(payment, set()).add(identity)
        links.append((link, payment))
        for h in d["observations"]:
            claims.setdefault(h, set()).add(identity)
    matched = {}
    for link, payment in links:
        d = link["details"]
        matching = [dividends[h] for h in d["observations"]]
        values = {
            digest(
                {
                    "date": e["event_date"],
                    **{
                        k: e["details"][k]
                        for k in (
                            "plan_type",
                            "employer",
                            "plan_id",
                            "security",
                            "quantity",
                            "gross",
                            "withholding",
                            "destination",
                        )
                    },
                }
            )
            for e in matching
        }
        if (
            len(values) == 1
            and len(payments[payment]) == 1
            and all(len(claims[h]) == 1 for h in d["observations"])
            and all(e["details"]["destination"] is not None for e in matching)
            and all(
                e["details"][k]["value_state"] == "known"
                for e in matching
                for k in ("gross", "withholding")
            )
        ):
            for h in d["observations"]:
                matched.setdefault(h, []).append(digest(link))
    for row in rows:
        identity = row["source_reference"]
        if identity not in dividends:
            continue
        e = dividends[identity]
        d = e["details"]
        row["match_evidence"] = matched.get(identity, [])
        row["status"] = (
            "matched_dividend_one_event"
            if row["match_evidence"]
            else "unmatched_dividend"
        )
        if not row["match_evidence"]:
            questions.append(
                {
                    "institution": d["trustee"],
                    "question": "Match dividend date, gross currency/amount, tax and destination of net cash across broker and trustee; was this one payment?",
                    "event": identity,
                    "business_reference": e["reference"],
                    "account": d["account"],
                }
            )
    return {
        "events": rows,
        "questions": questions,
        "complete_annual_calculation": False if events else None,
    }


def deadline_projection(state, tax_year, as_of):
    rows = []
    for e in workflow_records(state, "deadline", tax_year):
        d = e["details"]
        effective = (
            d["extension_deadline"] if d["extension_applicable"] else d["base_deadline"]
        )
        rows.append(
            {
                **d,
                "effective_deadline": effective,
                "reference": e["reference"],
                "observed_at": e["observed_at"],
                "days_remaining": (date.fromisoformat(effective) - as_of).days,
            }
        )
    if tax_year == 2020 and not any(r["category"] == "refund_claim" for r in rows):
        services = parse_json(
            (
                Path(__file__).resolve().parents[1] / "assets/rules/services.json"
            ).read_text()
        )
        source = next(r for r in services["refund_claims"] if r["refund_year"] == 2020)
        rows.append(
            {
                "category": "refund_claim",
                "base_deadline": source["claim_deadline"],
                "effective_deadline": source["claim_deadline"],
                "extension_deadline": None,
                "extension_applicable": False,
                "extension_reference": None,
                "source_url": source["url"],
                "observed_at": source["observed_at"],
                "days_remaining": (
                    date.fromisoformat(source["claim_deadline"]) - as_of
                ).days,
            }
        )
    return sorted(rows, key=lambda r: r["effective_deadline"])


def forecast_projection(state, tax_year):
    forecasts = workflow_records(state, "forecast", tax_year, False)
    if not forecasts:
        return None
    latest_date = max(e["event_date"] for e in forecasts)
    current = [e for e in forecasts if e["event_date"] == latest_date]
    if len(current) != 1:
        return {"status": "conflicting_forecasts", "gross_income": None}
    d = current[0]["details"]
    gross = exact_sum(
        Decimal(p[field]["amount"])
        for p in d["payers"]
        for field in ("actual_income", "remaining_income", "bonus")
    )
    return {
        "status": "gross_forecast_only",
        "tax_year": tax_year,
        "currency": "ILS",
        "direction": "forecast_gross_income",
        "gross_income": str(gross),
        "payers": d["payers"],
        "assumptions": d["assumptions"],
        "payroll_relief": d["payroll_relief"],
        "annual_tax_forecast": None,
        "source_reference": digest(current[0]),
    }


def route_projection(state, tax_year, current_year, filing):
    recorded = workflow_records(state, "route", tax_year, False)
    latest = max((e["event_date"] for e in recorded), default=None)
    current = [e for e in recorded if e["event_date"] == latest]
    reviewed = (
        len(current) == 1
        and current[0]["provenance"] == "verified_source"
        and current[0]["details"]["route_status"] == "verified"
    )
    pending = any(
        r["status"] == "transmitted_acknowledgment_unverified"
        for r in filing["returns"]
    )
    prior = any(r["status"] == "filing_completed" for r in filing["returns"])
    if tax_year == current_year:
        candidates = ["coordination", "relief"]
    elif tax_year > current_year or pending:
        candidates = []
    elif prior:
        candidates = ["correction"]
    else:
        candidates = ["135", "1301"]
    prior_unverified = (
        reviewed
        and not prior
        and current[0]["details"]["checks"]["prior_filing"]
        and tax_year < current_year
    )
    if prior_unverified:
        candidates = []
    obligation = (
        current[0]["details"]["filing_obligation"] if reviewed else "unresolved"
    )
    if obligation == "required" and "135" in candidates:
        candidates.remove("135")
    verified = reviewed and current[0]["form"] in candidates
    return {
        "recorded": [event_projection(e) for e in recorded],
        "route_status": "verified" if verified else "unresolved",
        "candidate_forms": candidates,
        "verified_form": current[0]["form"] if verified else None,
        "filing_obligation": obligation,
        "pending_acknowledgment": pending,
        "prior_filing_unverified": prior_unverified,
        "notice": "Candidates only unless source-backed year-specific review is recorded; employment/security ownership and balance do not establish the route.",
    }


def display_state(raw):
    """Quarantine unverifiable result metadata without deleting its audit history."""
    state = copy.deepcopy(raw)
    results = state["results"]
    state["results"] = []
    validate(state)
    for ref in results:
        try:
            validate_reference(ref, state)
        except CaseError:
            require(
                type(ref) is dict
                and ref.get("owner") == state["taxpayer_id"]
                and type(ref.get("tax_year")) is int
                and ref["tax_year"] in state["years"],
                "result_owner_year_mismatch",
            )
            state["results"].append(
                {
                    "owner": ref["owner"],
                    "tax_year": ref["tax_year"],
                    "purpose": "unverifiable_result",
                    "status": "stale",
                    "reason": "freshness_unverifiable",
                    "reference": ref,
                }
            )
        else:
            state["results"].append(ref)
    return validate(state)


def summary_projection(fd, state, as_of):
    pack = load_rules()
    years = []
    for tax_year in state["years"]:
        estimate, reference, scenarios, reasons = None, None, [], []
        try:
            estimate = current_result(fd, state, tax_year, pack)
            reference = next(
                r
                for r in state["results"]
                if r.get("purpose") == "annual_estimate"
                and r["tax_year"] == tax_year
                and r["scenario"] is None
                and r["status"] == "current"
            )
        except CaseError as exc:
            reasons.append(exc.code)
        for ref in state["results"]:
            if ref["tax_year"] != tax_year:
                continue
            if ref["purpose"] == "unverifiable_result":
                reasons.append("freshness_unverifiable")
            if (
                ref.get("purpose") == "annual_estimate"
                and ref.get("scenario") is not None
                and ref["status"] == "current"
            ):
                try:
                    scenarios.append(
                        current_result(fd, state, tax_year, pack, ref["scenario"])
                    )
                except CaseError as exc:
                    reasons.append(exc.code)
        conflicts = [
            c
            for c in state["conflicts"]
            if c["tax_year"] == tax_year and c["status"] == "unresolved"
        ]
        conflict_ids = {c["economic_id"] for c in conflicts}
        requests = []
        for issuer in sorted(
            {
                i["issuer"]
                for i in state["economic_items"]
                if i["tax_year"] == tax_year
                and i["kind"] == "wages"
                and i["id"] in conflict_ids
            }
        ):
            requests.append(
                {
                    "document_he": "טופס 106",
                    "issuer": issuer,
                    "uncertainty": "Reconcile the conflicting amount, withholding or employment period with the retained observations.",
                    "manual_step": "Ask payroll for a corrected Form 106 or a written field-specific reconciliation.",
                    "conflict_references": [digest(c) for c in conflicts],
                }
            )
        for r in state["requirements"]:
            if r["tax_year"] == tax_year and r["status"] == "missing" and not conflicts:
                item = next(
                    i for i in state["economic_items"] if i["id"] == r["economic_id"]
                )
                requests.append(
                    {
                        "document_he": "טופס 106",
                        "issuer": item["issuer"],
                        "uncertainty": "Signed annual certificate needed for filing acceptability; provisional income may already be known.",
                        "manual_step": "Ask this employer's payroll department for Form 106 for the tax year.",
                    }
                )
        equity = equity_projection(state, tax_year)
        for question in equity["questions"]:
            requests.append(
                {
                    "document_he": "דוח נאמן / ברוקר",
                    "issuer": question["institution"],
                    "uncertainty": question["question"],
                    "manual_step": "Request the event-specific trustee/broker statement.",
                    "event": question["event"],
                }
            )
        if estimate is None and not requests:
            requests.append(
                {
                    "document_he": "מסמכי הכנסה ואישורי מס",
                    "issuer": "taxpayer / relevant issuer",
                    "uncertainty": ", ".join(sorted(set(reasons))),
                    "manual_step": "Collect and reconcile this year's documents for a year-specific official or professional calculation; importing evidence does not enable local numeric coverage."
                    if "unsupported_tax_year" in reasons
                    else "Review the stated coverage/completeness blocker; recalculate after verified evidence is imported.",
                }
            )
        blockers = workflow_records(state, "portal_block", tax_year)
        inquiries = []
        for blocker in blockers:
            d = blocker["details"]
            inquiries.append(
                {
                    "status": "unsent_draft",
                    "form": blocker["form"],
                    "draft_version": blocker["draft_version"],
                    "exact_portal_message": d["message"],
                    "next_action": "Check existing inquiry status"
                    if d["existing_inquiry_reference"]
                    else "Draft inquiry to the tax office about the blocked proper reporting route",
                    "existing_inquiry_reference": d["existing_inquiry_reference"],
                    "question": "What is the official next step or alternative for this message, year, form and version?",
                }
            )
        deadlines = deadline_projection(state, tax_year, as_of)
        filing = filing_projection(state, tax_year)
        route = route_projection(state, tax_year, as_of.year, filing)
        donations = donation_projection(state, tax_year, filing)
        for receipt in donations:
            if receipt["registry_status"] in {"missing", "wrong_taxpayer"}:
                inquiries.append(
                    {
                        "status": "unsent_draft",
                        "recipient": receipt["issuer"],
                        "receipt_id": receipt["receipt_id"],
                        "question": "Please report this receipt or correct its taxpayer association in תרומות ישראל, and confirm the registration reference.",
                        "next_action": "Check for an existing inquiry, then verify the registry entry after the issuer replies.",
                    }
                )
        next_control = None
        control_scope = (
            "Use the observed portal or official instructions for the verified route."
        )
        if tax_year == as_of.year:
            next_control = "לעריכת תיאום מס"
        elif route["verified_form"] == "135" or (
            route["verified_form"] is None and "135" in route["candidate_forms"]
        ):
            next_control = "להגשת הבקשה"
        elif route["pending_acknowledgment"] or route["prior_filing_unverified"]:
            control_scope = "Retrieve the filing acknowledgment for the exact year, form and version before starting a new submission."
        elif "correction" in route["candidate_forms"]:
            control_scope = "Review the exact filed version and confirm the correction procedure with the tax office if an omission is verified."
        if next_control:
            control_scope = "Public service entry only; route eligibility must be reviewed before submission."
        years.append(
            {
                "tax_year": tax_year,
                "currency": "ILS",
                "estimate": estimate,
                "result_reference": reference,
                "scenarios": scenarios,
                "reasons": sorted(set(reasons)) if estimate is None else [],
                "conflicts": conflicts,
                "filing": filing,
                "documents": document_projection(fd, state, tax_year),
                "route": route,
                "deadlines": deadlines,
                "donations": donations,
                "payroll_relief": [
                    event_projection(e)
                    for e in workflow_records(state, "payroll_relief", tax_year)
                ],
                "equity": equity,
                "gross_forecast": forecast_projection(state, tax_year),
                "can_finish_now": "Review the checked estimate and filing requirements"
                if estimate
                else "Collect and reconcile documents; local numeric calculation is unavailable for this year"
                if "unsupported_tax_year" in reasons
                else "Reconcile listed evidence and continue independent years",
                "next_evidence": requests,
                "inquiry_drafts": inquiries,
                "next_control_he": next_control,
                "control_scope": control_scope,
            }
        )
    years.sort(
        key=lambda y: (
            y["deadlines"][0]["effective_deadline"] if y["deadlines"] else "9999-12-31",
            y["tax_year"],
        )
    )
    return {
        "ok": True,
        "case_id": state["case_id"],
        "revision": state["revision"],
        "preferred_language": state["preferred_language"],
        "as_of": as_of.isoformat(),
        "mailbox_connected": False,
        "portal_actions_available": False,
        "years": years,
        "year_table": [
            {
                "tax_year": y["tax_year"],
                "currency": "ILS",
                "estimate": y["estimate"],
                "scenarios": y["scenarios"],
                "reasons": y["reasons"],
                "filing_state": y["filing"]["state"],
                "can_finish_now": y["can_finish_now"],
                "next_evidence": y["next_evidence"],
                "deadlines": y["deadlines"],
                "next_control_he": y["next_control_he"],
                "control_scope": y["control_scope"],
            }
            for y in years
        ],
    }


def document_projection(fd, state, tax_year):
    result = []
    for record in state["attachments"]:
        if record["tax_year"] != tax_year:
            continue
        try:
            report = checked_document(fd, record)
            result.append(
                {
                    **record,
                    "attachment_ready": report["attachment_ready"],
                    "status": report["status"],
                    "copy_kind": report.get("copy_kind"),
                    "portal_acceptance": "unobserved",
                }
            )
        except (CaseError, OSError, ValueError, KeyError, TypeError):
            result.append(
                {
                    **record,
                    "attachment_ready": False,
                    "status": "document_unverifiable",
                    "portal_acceptance": "unobserved",
                }
            )
    return result


def workflow_summary(path, language=None, as_of=None, publish=None):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    try:
        observed = (
            date.fromisoformat(as_of)
            if as_of is not None
            else datetime.now(ZoneInfo("Asia/Jerusalem")).date()
        )
        with locked(path) as fd:
            raw = parse_json(read_private(fd, "checkpoint.json"))
            state = display_state(raw)
            if language is not None:
                state["preferred_language"] = text(language)
            if state != raw:
                state["revision"] += 1
                validate(state)
                serialized = canonical(state)
                require(len(serialized) <= MAX_CASE_BYTES, "case_too_large")
                atomic_text(
                    fd,
                    "summary.md",
                    "Recalculation required. Previous estimates are unavailable.\n",
                )
                atomic_text(fd, "checkpoint.json", serialized.decode())
            public = summary_projection(fd, state, observed)
            atomic_text(
                fd,
                "summary.md",
                json.dumps(public, ensure_ascii=False, indent=2) + "\n",
            )
            if publish is not None:
                publish(public)
            return public
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        with locked(path) as fd:
            atomic_text(
                fd,
                "summary.md",
                "Recalculation required. Previous estimates are unavailable.\n",
            )
        raise
