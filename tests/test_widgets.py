"""Tests for the reusable molecules widgets."""

from empa_molecules.widgets import NodeViewWidget


def test_node_view_widget_initializes():
    widget = NodeViewWidget()
    assert len(widget.children) == 1
