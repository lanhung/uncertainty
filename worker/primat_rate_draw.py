"""Safety boundary for applying one nuclear-rate draw to a PRIMAT network."""

from __future__ import annotations

from typing import Any, Iterable


def _rate_networks(target: Any) -> Iterable[Any]:
    """Yield one NetworkDefinition or both networks in UpdateNuclearRates."""
    has_mt = hasattr(target, "_mt_net")
    has_lt = hasattr(target, "_lt_net")
    if has_mt != has_lt:
        raise RuntimeError(
            "PRIMAT wrapper contract changed; expected both _mt_net and _lt_net"
        )
    if has_mt:
        yield target._mt_net
        yield target._lt_net
    else:
        yield target


def invalidate_fill_buffer_cache(network: Any) -> None:
    """Invalidate PRIMAT's one-entry rate buffer cache.

    PRIMAT v0.3.2 ``NetworkDefinition.apply_variations`` updates ``_fwd`` but
    does not invalidate the buffer memo. Reusing a network across draws can
    therefore return the preceding draw when the next evaluation uses the
    identical temperature and clamp flag.
    """
    for rate_network in _rate_networks(network):
        required = ("_cache_T_t", "_cache_clamp")
        missing = [name for name in required if not hasattr(rate_network, name)]
        if missing:
            raise RuntimeError(
                "PRIMAT cache contract changed; refusing an unguarded rate draw: "
                + ", ".join(missing)
            )
        rate_network._cache_T_t = None
        rate_network._cache_clamp = None


def apply_variations_safely(network: Any, config: Any) -> None:
    """Apply one PRIMAT rate draw and make the next buffer evaluation fresh."""
    apply_variations = getattr(network, "apply_variations", None)
    if not callable(apply_variations):
        raise RuntimeError("PRIMAT network has no callable apply_variations")
    apply_variations(config)
    invalidate_fill_buffer_cache(network)
