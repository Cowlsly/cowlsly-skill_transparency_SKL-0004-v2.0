from pathlib import Path

import pytest

from tests.fixtures.corpus import CASES, materialize
from transparency_assurance.validator import inspect_asset


def test_corpus_has_at_least_thirty_fixtures():
    assert len(CASES) >= 30
    ids = [case.id for case in CASES]
    assert len(ids) == len(set(ids)), "Fixture ids must be unique"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_corpus_case(case, tmp_path: Path):
    dest = tmp_path / case.output_name()
    path = case.builder(dest)
    report = inspect_asset(path, case.profile)
    assert report["target_compliant"] is case.expected_compliant, (
        f"{case.id}: expected compliant={case.expected_compliant}, "
        f"got {report['target_compliant']} state={report.get('capability_state')} "
        f"gates={{k: v['status'] for k, v in report['gates'].items()}}"
    )
    if case.expected_compliant:
        assert str(report["capability_state"]).startswith("VERIFIED")
    else:
        assert not str(report["capability_state"]).startswith("VERIFIED")
    for gate, status in case.expected_gates.items():
        actual = report["gates"][gate]["status"]
        assert actual == status, f"{case.id}: {gate} expected {status}, got {actual} ({report['gates'][gate]['reason']})"
    if case.expected_edge_mode is not None:
        mode = report["gates"]["EDGE_QUALITY"]["metrics"].get("edge_mode")
        assert mode == case.expected_edge_mode, f"{case.id}: edge_mode expected {case.expected_edge_mode}, got {mode}"


def test_materialize_writes_unique_files(tmp_path: Path):
    built = materialize(tmp_path / "corpus")
    assert len(built) == len(CASES)
    assert len({path.resolve() for _case, path in built}) == len(CASES)
    assert all(path.is_file() and path.stat().st_size > 0 for _case, path in built)
