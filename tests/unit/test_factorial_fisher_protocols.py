from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_solver_factorial_protocol_forbids_unmatched_engine_claims() -> None:
    text = (ROOT / "docs/decisions/ADR-SOLVER-FACTORIAL-v1.md").read_text(encoding="utf-8")

    for factor in ("`E`", "`R`", "`W`", "`X`", "`nu`"):
        assert factor in text
    for solver_id in range(9):
        assert f"`S{solver_id}`" in text
    assert "pipeline discrepancy" in text
    lower = text.lower()
    assert "at least 20 standard points" in lower
    assert "at least 20\nnon-standard points" in lower
    assert "A00 scientific lead: pending" in text


def test_fisher_gate_protocol_and_empty_report_cannot_authorize_pilot() -> None:
    adr = (ROOT / "docs/decisions/ADR-FISHER-GATE-v1.md").read_text(encoding="utf-8")
    report = (ROOT / "artifacts/gates/FISHER_GATE_REPORT_v1.md").read_text(encoding="utf-8")

    for response in ("J_theta", "J_q", "J_a", "C_rate", "C_shape", "C_solver"):
        assert response in adr
    assert "minimum set is 64" in adr
    assert "`G0`" in adr and "`G1`" in adr and "`G2`" in adr and "`G3`" in adr
    assert "NOT EVALUATED" in report
    assert "Pilot-10k authorization: **NO**" in report
    assert "not a G0 finding" in report
