"""The evidence page must stay a single file and must not drift from the evidence.

Rendering is opt-in (matplotlib is an extra, not a runtime dependency), so these
skip when the plotting extra is absent.
"""

import base64
import re

import pytest

# Both fixtures below render through the opt-in plotting extra, so the skip has to
# run before the modules that reach for the backend.
pytest.importorskip("matplotlib")

from v0_2.examples.phase4_figures import FIGURES, render_all
from v0_2.examples.phase4_report import page
from v0_2.examples.phase4_validation import evidence


def _page(tmp_path):
    figures = tmp_path / "figures"
    figures.mkdir()
    render_all(figures)
    return page(figures)


def test_page_is_self_contained(tmp_path):
    markup = _page(tmp_path)
    embedded = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", markup)
    assert len(embedded) == len(FIGURES)
    # A reader should be able to save this one file and open it anywhere, so no
    # asset may be referenced by path.
    assert not re.findall(r'(?:src|href)=["\'](?!data:)([^"\']+)', markup)
    for blob in embedded:
        assert base64.b64decode(blob).startswith(b"\x89PNG\r\n\x1a\n")


def test_page_publishes_the_evidence_module_values(tmp_path):
    markup = _page(tmp_path)
    reported = evidence()
    row = reported["convergence"]["two_branch"]["metrics"][0]
    # The page builds its tables from evidence() rather than a transcription, so the
    # ledger has to appear verbatim. Formatting is f"{value:.6f}" in both places.
    for key in ("pump_electrical_j", "pump_hydraulic_j", "pump_heat_liquid_j", "hx_j"):
        assert f"{float(row[key]):.6f}" in markup
    for item in reported["hydraulic"]:
        assert f"{float(item['total_flow_kg_s']):.6f}" in markup
    # And the gate status must not be softened anywhere on the page.
    assert "PASS for the declared generic numerical fixture only" in markup
