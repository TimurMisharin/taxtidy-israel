"""Pure, deliberately scoped 2025 decimal estimates; no filesystem or portal I/O."""

import re
from decimal import Decimal, localcontext

ENGINE_VERSION = "0.2.1"
NUMBER = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?\Z")


class CalculationError(ValueError):
    """Stable coverage/validation reason without source contents."""


def require(condition, reason):
    if not condition:
        raise CalculationError(reason)


def number(value):
    require(
        type(value) is str and len(value) <= 24 and NUMBER.fullmatch(value) is not None,
        "invalid_calculation_money",
    )
    return Decimal(value)


def amount(value):
    require(
        type(value) is dict
        and value.get("value_state") == "known"
        and value.get("currency") == "ILS"
        and type(value.get("tax_year")) is int
        and value["tax_year"] == 2025,
        "missing_calculation_money",
    )
    return number(value.get("amount"))


def compute(inputs, pack, scenario=None):
    """Consume validated case inputs, derive every amount, return an exact trace."""
    require(
        inputs["tax_year"] == pack.get("tax_year") == 2025
        and pack.get("currency") == "ILS"
        and pack.get("engine_version") == ENGINE_VERSION,
        "unsupported_tax_year_or_engine",
    )
    rules = pack["rules"]
    for rule in rules.values():
        require(
            rule.get("verified") is True
            and rule.get("effective_year") == 2025
            and rule.get("source_id") in pack["sources"]
            and type(rule.get("pdf_page")) is int
            and rule.get("verified_at"),
            "unverified_tax_rule",
        )

    def parameter(name):
        return rules[name]["value"]

    with localcontext() as ctx:
        ctx.prec = 48
        totals = dict.fromkeys(
            (
                "wages",
                "direct_reserve",
                "assistance",
                "gains",
                "losses",
                "institution_offsets",
                "sale_proceeds",
                "donations",
                "payroll_donation_credit",
                "withheld",
                "advances",
                "employer_reserve_in_wages",
            ),
            Decimal(0),
        )
        unresolved = False
        excluded = []
        for item in inputs["items"]:
            kind, details = item["kind"], item.get("details", {})
            value, withheld = amount(item["amount"]), amount(item["withholding"])
            if kind == "wages":
                totals["wages"] += value
                totals["withheld"] += withheld
            elif kind == "securities":
                require(
                    details["basis"] == "gross_before_institution_offsets"
                    and details["asset_class"] == "domestic_listed_shares"
                    and details["sole_owner"] is True
                    and details["material_holder"] is False
                    and details["business_or_related_party"] is False
                    and details["rate"] == parameter("securities_rate")
                    and all(
                        amount(details[k]) == 0
                        for k in (
                            "dividends",
                            "interest",
                            "foreign_tax",
                            "loss_carry_in",
                        )
                    ),
                    "unsupported_securities_facts",
                )
                loss, offset = (
                    amount(details["realized_loss"]),
                    amount(details["prior_offset"]),
                )
                require(offset <= min(value, loss), "inconsistent_institution_offset")
                totals["gains"] += value - offset
                totals["losses"] += loss - offset
                totals["institution_offsets"] += offset
                totals["sale_proceeds"] += amount(details["sale_proceeds"])
                totals["withheld"] += withheld
            elif kind == "donation":
                require(
                    details["sole_donor"] is True
                    and details["settled_same_year"] is True
                    and all(
                        item[field] is not None
                        and item[field].startswith(f"{inputs['tax_year']}-")
                        for field in ("event_date", "settlement_date")
                    )
                    and details["approval_from"]
                    <= item["event_date"]
                    <= details["approval_to"]
                    and all(
                        details[k] is False
                        for k in (
                            "cancelled",
                            "fees_or_benefit",
                            "installments",
                            "carry_in",
                        )
                    )
                    and withheld == 0,
                    "unverified_donation_eligibility",
                )
                totals["donations"] += value
                totals["payroll_donation_credit"] += amount(
                    details["payroll_applied_credit"]
                )
            elif kind == "reserve":
                if details["included_in_wages"] is True:
                    require(
                        any(
                            w["id"] == details["wage_item"]
                            and w["kind"] == "wages"
                            and value <= amount(w["amount"])
                            for w in inputs["items"]
                        ),
                        "unverified_payroll_link",
                    )
                    totals["employer_reserve_in_wages"] += value
                    excluded.append(item["id"])
                else:
                    require(
                        details["program"] == "national_insurance_employee_reserve"
                        and details["same_year_receipt_and_service"] is True
                        and all(
                            item[field] is not None
                            and item[field].startswith(f"{inputs['tax_year']}-")
                            for field in ("event_date", "settlement_date")
                        ),
                        "unsupported_reserve_program_or_allocation",
                    )
                    totals["direct_reserve"] += value
                    totals["withheld"] += withheld
            elif kind == "assistance":
                require(
                    details["program"] == "unknown" and withheld == 0,
                    "unverified_assistance_payment",
                )
                unresolved = True
                if scenario == "assistance_taxable":
                    totals["assistance"] += value
                elif scenario == "assistance_excluded":
                    excluded.append(item["id"])
            elif kind == "advance_payment":
                require(withheld == 0, "duplicated_payment")
                totals["advances"] += value
            else:
                raise CalculationError("unsupported_income_kind")
        require(
            scenario in (None, "assistance_taxable", "assistance_excluded")
            and (scenario is None or unresolved),
            "unsupported_scenario",
        )
        require(not unresolved or scenario is not None, "unresolved_assistance_program")
        ordinary = totals["wages"] + totals["direct_reserve"] + totals["assistance"]
        remaining_gain = max(Decimal(0), totals["gains"] - totals["losses"])
        taxable = ordinary + remaining_gain
        require(
            ordinary + totals["gains"] < number(parameter("surcharge_boundary")),
            "unsupported_high_income",
        )
        tax, lower = Decimal(0), Decimal(0)
        bracket_trace = []
        for bracket in parameter("brackets"):
            upper = (
                number(bracket["upper"]) if bracket["upper"] is not None else ordinary
            )
            base = max(Decimal(0), min(ordinary, upper) - lower)
            charge = base * number(bracket["rate"])
            tax += charge
            bracket_trace.append(
                {"base": str(base), "rate": bracket["rate"], "tax": str(charge)}
            )
            lower = upper
        capital_tax = remaining_gain * number(parameter("securities_rate"))
        gross = tax + capital_tax
        credit_entitlement = number(parameter("credit_point")) * number(
            parameter("resident_male_points")
        )
        personal_credit = min(gross, credit_entitlement)
        before_donations = gross - personal_credit
        eligible = Decimal(0)
        if totals["donations"] > number(parameter("donation_minimum_exclusive")):
            eligible = min(
                totals["donations"],
                taxable * number(parameter("donation_income_fraction")),
                number(parameter("donation_ceiling")),
            )
        donation_credit = min(
            before_donations, eligible * number(parameter("donation_rate"))
        )
        liability = before_donations - donation_credit
        due = liability - totals["withheld"] - totals["advances"]
        direction = (
            "estimated_additional_tax"
            if due > 0
            else "estimated_refund"
            if due < 0
            else "estimated_zero_balance"
        )
        return {
            "tax_year": 2025,
            "currency": "ILS",
            "status": "scenario_estimate" if scenario else "estimated",
            "scenario": scenario,
            "scenario_condition": parameter(scenario) if scenario else None,
            "filing_ready": False,
            "rounding": parameter("rounding"),
            "income": {k: str(v) for k, v in totals.items()},
            "taxable_ordinary_income": str(ordinary),
            "remaining_realized_gain": str(remaining_gain),
            "unabsorbed_realized_loss": str(
                max(Decimal(0), totals["losses"] - totals["gains"])
            ),
            "deductions": "0",
            "taxable_income": str(taxable),
            "brackets": bracket_trace,
            "ordinary_tax": str(tax),
            "capital_tax_before_credits": str(capital_tax),
            "liability_before_personal_credits": str(gross),
            "personal_credit_entitlement": str(credit_entitlement),
            "personal_credit_applied": str(personal_credit),
            "liability_before_donations": str(before_donations),
            "eligible_donation": str(eligible),
            "donation_credit": str(donation_credit),
            "potential_donation_carryforward": str(
                max(Decimal(0), totals["donations"] - eligible)
                if totals["donations"] > number(parameter("donation_minimum_exclusive"))
                else Decimal(0)
            ),
            "liability": str(liability),
            "israeli_tax_withheld": str(totals["withheld"]),
            "advance_tax_payments": str(totals["advances"]),
            "foreign_tax_paid": "0",
            "allowable_foreign_tax_credit": "0",
            "balance_due": str(due),
            "direction": direction,
            "balance": str(abs(due)),
            "excluded_included_items": excluded,
            "source_rule_ids": sorted(rules),
            "evidence_references": sorted(inputs["evidence_references"]),
        }
