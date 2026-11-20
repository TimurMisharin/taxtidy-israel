"""Synthetic fixtures and isolated private cases, outside the source tree."""

import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "taxtidy-israel/skills/taxtidy-israel/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("taxtidy_case", SCRIPTS / "case.py")
case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(case)


def fixture():
    return json.loads((ROOT / "tests/fixtures/cases.json").read_text())


def wage(document_type, start, end, amount, withholding, reference):
    """Fictional reviewed source whose text agrees with its structured fields."""
    raw = copy.deepcopy(fixture()["baseline"][0])
    raw.update(
        document_type=document_type,
        period_start=start,
        period_end=end,
        business_reference=reference,
    )
    raw["amount"]["amount"] = amount
    raw["withholding"]["amount"] = withholding
    body = (
        f"SYNTHETIC ONLY; fictional-taxpayer; fictional-employer-a; {document_type}; "
        f"2025; {start} to {end}; taxable wages ILS {amount}; "
        f"tax withheld ILS {withholding}; reference {reference}; בדיקה."
    )
    raw["source"].update(
        text=body,
        sha256=case.hashlib.sha256(body.encode("utf-8")).hexdigest(),
        field="taxable wages and tax withheld for stated period",
    )
    return raw


def temporary():
    # Resolve platform /var symlinks before choosing an explicit private root.
    return tempfile.TemporaryDirectory(
        prefix="taxtidy-synthetic-", dir=Path(tempfile.gettempdir()).resolve()
    )


def baseline(parent):
    root = Path(parent) / "case"
    state = case.initialize(root, "fictional-taxpayer", [2024, 2025], synthetic=True)
    state = case.import_evidence(root, batch(state, fixture()["baseline"]))
    return root, state


def batch(state, observations):
    return {
        "case_id": state["case_id"],
        "expected_revision": state["revision"],
        "observations": copy.deepcopy(observations),
    }


def probe(state, tax_year):
    return {
        "owner": state["taxpayer_id"],
        "tax_year": tax_year,
        "purpose": "synthetic_freshness_probe",
        "status": "current",
        "input_digest": case.input_digest(
            state, state["taxpayer_id"], tax_year, "0" * 64, case.ENGINE_VERSION
        ),
    }


def store_probe(root, state):
    """Private non-tax reference used only by phase-1 invalidation tests."""
    state = copy.deepcopy(state)
    state["results"] = [probe(state, y) for y in state["years"]]
    case.validate(state)
    with case.locked(root) as fd:
        case.atomic_text(fd, "checkpoint.json", case.canonical(state).decode())
    return state


def cli(*args):
    import subprocess

    return subprocess.run(
        [sys.executable, str(SCRIPTS / "taxtidy.py"), *map(str, args)],
        check=False,
        capture_output=True,
        text=True,
    )


def reviewed_copy(raw, **changes):
    value = copy.deepcopy(raw)
    value.update(changes)
    review = value.pop("review")
    value.pop("source")
    body = "SYNTHETIC ONLY; independently reviewed fictional record; " + json.dumps(
        value, sort_keys=True, ensure_ascii=False
    )
    value["source"] = {
        "text": body,
        "sha256": case.hashlib.sha256(body.encode()).hexdigest(),
        "page": 1,
        "field": "reviewed synthetic fields",
    }
    value["review"] = review
    return value


def annual_baseline(parent):
    root, state = baseline(parent)
    incoming = batch(state, [])
    incoming["eligibility"] = [fixture()["phase2"]["profile"]]
    state = case.import_evidence(root, incoming)
    return root, state


def wage_resolution(state, selected):
    value = {
        "kind": "wage_resolution",
        "owner": selected["owner"],
        "tax_year": selected["tax_year"],
        "issuer": selected["issuer"],
        "selected_observation": case.digest(selected),
        "considered_observations": sorted(
            case.digest(o)
            for o in state["observations"]
            if o["issuer"] == selected["issuer"]
            and o["kind"] == "wages"
            and o["tax_year"] == selected["tax_year"]
        ),
        "review": {
            "reviewer": "synthetic-fixture-author",
            "owner_year_checked": True,
            "fields_checked": ["wage_resolution"],
            "method": "manual",
        },
        "source": {},
    }
    return reviewed_copy(value)


def cli_import(root, state, observations, eligibility=None):
    incoming = batch(state, observations)
    if eligibility is not None:
        incoming["eligibility"] = eligibility
    path = root.parent / "reviewed-import.json"
    path.write_text(json.dumps(incoming, ensure_ascii=False))
    path.chmod(0o600)
    return cli("import-evidence", "--case-root", root, "--input", path)


def observe(test, label, inputs, expected, actual):
    """Keep explicit synthetic values only; never capture locals or credentials."""
    record = json.loads(
        json.dumps(
            {
                "subcase": label,
                "input": inputs,
                "expected": expected,
                "actual": actual,
            },
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    if not hasattr(test, "observations"):
        test.observations = []
    test.observations.append(record)
