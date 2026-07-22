from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs/compute/autodl_inventory.md"


def test_public_inventory_records_all_nodes_and_evidence_boundaries() -> None:
    text = INVENTORY.read_text(encoding="utf-8")

    for node in (
        "autodl-westb-01",
        "autodl-bjb1-01",
        "autodl-bjb1-02-spare",
    ):
        assert node in text

    assert "8af7676442b166e552e102f5520e2a08f6642c29af295e0a0c08e816ed849cd8" in text
    assert "25 logical CPUs" in text
    assert "98,784,247,808 bytes (92 GiB)" in text
    assert "49,140 MiB" in text
    assert "compute capability 8.9" in text
    assert "it is not a\nthroughput" in text
    assert "pending uncertainty hardware and environment capture" in text


def test_public_inventory_contains_no_connection_or_secret_material() -> None:
    text = INVENTORY.read_text(encoding="utf-8").lower()

    forbidden = (
        "seetacloud.com",
        "66.135.",
        "ssh -p",
        "password=",
        "tailscale_authkey",
        "research_ops_token",
        "bearer ",
        "gpu-uuid",
    )
    for value in forbidden:
        assert value not in text
