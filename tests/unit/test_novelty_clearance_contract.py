from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs/literature/NOVELTY_CLEARANCE_v1.md"


def test_novelty_clearance_answers_all_seven_required_questions() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    for question in range(1, 8):
        assert f"## Q{question} —" in text


def test_known_results_are_explicitly_regression_only() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "used only as regression tests" in text
    assert "neural emulation of BBN abundances" in text
    assert "scalar nuclear-rate marginalization" in text
    assert "standard-BBN sensitivity rankings" in text
    assert "direct stiff-era constraints from LVK O1–O4a" in text


def test_rejection_risks_have_experiments_and_failure_actions() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    for risk in ("R1", "R2", "R3"):
        assert text.count(f"`{risk}`") >= 2
    assert "Failure action" in text
    assert "FISH-01" in text
    assert "WHY-01" in text
    assert "SOL-01" in text


def test_stop_rules_prevent_post_hoc_search_expansion() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "Pilot-10k remains" in text
    assert "unauthorized" in text
    assert "changing the primary observation compilation" in text
    assert "widening priors or adding endpoints after seeing the result" in text
    assert "speed alone also stops the new-emulator route" in text


def test_claims_and_required_signoffs_remain_uncleared() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "CLAIMS NOT CLEARED; TRACK B NOT FROZEN" in text
    assert "A00 scientific lead: **pending**" in text
    assert "A11 literature and competition: **pending**" in text
    assert "A09 independent validation and red team: **pending**" in text
    assert "Track B remains **NOT FROZEN**" in text
