from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/R0_reference_adapter.py"
PROTOCOL = ROOT / "configs/benchmarks/R0_reference_fast_track_v1.yaml"
TABLES = ROOT / "artifacts/priors/ETR25-R0-TABLES-v1/package.json"


def load_module():
    spec = importlib.util.spec_from_file_location("R0_reference_adapter", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fast_track_protocol_and_sigma_nodes_are_frozen() -> None:
    module = load_module()
    protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    module.validate_protocol(protocol, ROOT)

    nodes = protocol["sigma_point_design"]["nodes"]
    assert len(nodes) == 9
    assert nodes[0] == {"id": "center", "q": [0.0, 0.0, 0.0, 0.0]}
    assert len(protocol["plusminus_acceptance"]["check_ids"]) == 12


def test_scalar_and_asymmetric_curves_are_coherent_and_quantile_matched() -> None:
    module = load_module()
    rows = module.load_etr25_rows(TABLES)

    for reaction in module.REACTIONS:
        scalar = module.representation_arrays(
            rows,
            "R0_P0_ETR25_scalar_lognormal",
            reaction.canonical_id,
            1.0,
        )
        assert len(set(scalar["exp_sigma"])) >= 1
        assert module.drawn_curve(scalar, 1.0) != scalar["median"]

        lower = module.representation_arrays(
            rows,
            "R0_P1_ETR25_asymmetric_quantile_rank1",
            reaction.canonical_id,
            -0.9944578832097528,
        )
        upper = module.representation_arrays(
            rows,
            "R0_P1_ETR25_asymmetric_quantile_rank1",
            reaction.canonical_id,
            0.9944578832097528,
        )
        source = rows[reaction.canonical_id]
        assert np.allclose(
            module.drawn_curve(lower, -0.9944578832097528),
            [record["low_p16"] for record in source],
            rtol=2e-15,
            atol=0.0,
        )
        assert np.allclose(
            module.drawn_curve(upper, 0.9944578832097528),
            [record["high_p84"] for record in source],
            rtol=2e-15,
            atol=0.0,
        )


def test_solver_vectors_and_tau_mapping_are_unique() -> None:
    module = load_module()
    q = [-1.0, 0.5, 1.0]
    linx = module.linx_q_vector(q)
    prymordial = module.prymordial_constructor_args(q)

    assert linx[1:4] == q
    assert prymordial[1:4] == q
    assert sum(value != 0.0 for value in linx) == 3
    assert sum(value != 0.0 for value in prymordial) == 3
    assert (
        module.tau_n_seconds(
            {"tau_n_seconds": 878.3, "tau_n_sigma_seconds": 0.5},
            -1.0,
        )
        == 877.8
    )


class FakeReaction:
    def __init__(self, name: str):
        self.name = name
        self.T9_vec = np.asarray([0.1, 1.0])
        self.mu_median_vec = np.asarray([1.0, 2.0])
        self.expsigma_vec = np.asarray([1.0, 1.0])
        self.interp_type = "linear"


class FakeNetwork:
    def __init__(
        self,
        *,
        nuclear_net=None,
        interp_type="linear",
        reactions=None,
        max_i_species=None,
    ):
        del nuclear_net
        self.reactions = reactions or [
            FakeReaction("npdg"),
            FakeReaction("dpHe3g"),
            FakeReaction("ddHe3n"),
            FakeReaction("ddtp"),
            FakeReaction("tpag"),
        ]
        self.max_i_species = max_i_species or 8
        self.interp_type = interp_type


def test_linx_injection_replaces_only_three_in_memory_reactions() -> None:
    module = load_module()
    rows = module.load_etr25_rows(TABLES)
    modules = {
        "NuclearRates": FakeNetwork,
        "jnp": SimpleNamespace(asarray=np.asarray, float64=np.float64),
    }
    network = module.patch_linx_network(
        modules,
        rows,
        "R0_P0_ETR25_scalar_lognormal",
        [-1.0, 0.0, 1.0],
    )

    by_name = {reaction.name: reaction for reaction in network.reactions}
    assert len(by_name["npdg"].T9_vec) == 2
    for reaction in module.REACTIONS:
        injected = by_name[reaction.native_id]
        assert len(injected.T9_vec) == len(rows[reaction.canonical_id])
        assert math.isclose(
            float(injected.mu_median_vec[0]),
            float(rows[reaction.canonical_id][0]["median_p50"]),
        )


def test_prymordial_install_restores_global_arrays() -> None:
    module = load_module()
    rows = module.load_etr25_rows(TABLES)
    init = SimpleNamespace()
    originals = {}
    for reaction in module.REACTIONS:
        for suffix in ("T9", "median", "expsigma"):
            name = f"{reaction.native_id}_{suffix}"
            value = np.asarray([1.0, 2.0])
            originals[name] = value
            setattr(init, name, value)

    saved = module.install_prymordial_arrays(
        init,
        rows,
        "R0_P0_ETR25_scalar_lognormal",
        [0.0, 0.0, 0.0],
    )
    assert all(len(getattr(init, name)) > 2 for name in originals)
    module.restore_prymordial_arrays(init, saved)
    assert all(getattr(init, name) is value for name, value in originals.items())
