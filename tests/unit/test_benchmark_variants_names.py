from __future__ import annotations

from bench.variants import FIFO_SAFE_VARIANT, report_variant_name


def test_report_variant_name_maps_internal_fifo_to_public_fifo_safe() -> None:
    assert report_variant_name("fifo") == FIFO_SAFE_VARIANT
    assert report_variant_name("heuristic") == "heuristic"
    assert report_variant_name("full") == "full"
