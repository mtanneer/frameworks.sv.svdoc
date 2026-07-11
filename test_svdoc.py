"""Minimal smoke test for the Phase 1 IR/renderer pipeline and --fix."""
import tempfile
import os

from svdoc.fixer import fix_file
from svdoc.parser import parse_interface, parse_module, parse_package, resolve_types
from svdoc.render_md import render, render_interface, render_package


def test_fix_fills_gaps_and_is_idempotent():
    src = """\
module fifo #(
    parameter int DEPTH = 16,
    parameter int WIDTH = 8    ///< Bit width of each data word
) (
    input  logic             clk,   ///< Clock
    input  logic             rst_n,
    output logic              empty
);

endmodule
"""
    fd, path = tempfile.mkstemp(suffix=".sv")
    os.write(fd, src.encode())
    os.close(fd)
    try:
        assert fix_file(path) is True
        mod = parse_module(path)
        assert mod.doc == "@brief TODO"
        assert mod.params[0].doc == "TODO"
        assert mod.params[1].doc == "Bit width of each data word"
        assert mod.ports[0].doc == "Clock"
        assert mod.ports[1].doc == "TODO"
        assert mod.ports[2].doc == "TODO"

        assert fix_file(path) is False  # idempotent, already fully documented
    finally:
        os.remove(path)


def test_fifo_example():
    mod = parse_module("spike/example.sv")
    assert mod.name == "fifo"
    assert mod.doc and "synchronous FIFO" in mod.doc

    assert [p.name for p in mod.params] == ["DEPTH", "WIDTH"]
    assert mod.params[0].default == "16"
    assert mod.params[0].doc == "Number of entries in the FIFO"

    assert [p.name for p in mod.ports] == [
        "clk", "rst_n", "wr_en", "wr_data", "full", "rd_en", "rd_data", "empty",
    ]
    wr_data = mod.ports[3]
    assert wr_data.direction == "input"
    assert wr_data.type == "logic [WIDTH-1:0]"
    assert wr_data.doc == "Data to write"

    text = render(mod)
    assert "# Module: `fifo`" in text
    assert "| `DEPTH` | `int` | `16` |" in text


def test_handshake_interface():
    iface = parse_interface("spike/example_if.sv")
    assert iface.name == "handshake_if"
    assert iface.doc == "@brief Simple request/ack handshake interface."

    assert [p.name for p in iface.params] == ["WIDTH"]
    assert [p.name for p in iface.ports] == ["clk"]
    assert [s.name for s in iface.signals] == ["valid", "ready", "data"]
    assert iface.signals[2].type == "logic [WIDTH-1:0]"
    assert iface.signals[2].doc == "Payload data"

    assert [m.name for m in iface.modports] == ["producer", "consumer"]
    producer = iface.modports[0]
    assert producer.doc == "@brief Producer-side view of the handshake."
    assert [(g.direction, g.signals, g.doc) for g in producer.port_groups] == [
        ("output", ["valid"], "Drive valid"),
        ("input", ["ready"], "Sample ready"),
        ("output", ["data"], "Drive data"),
    ]

    text = render_interface(iface)
    assert "# Interface: `handshake_if`" in text
    assert "### `producer`" in text


def test_fifo_pkg():
    pkg = parse_package("spike/example_pkg.sv")
    assert pkg.name == "fifo_pkg"
    assert pkg.doc == "@brief Shared types for the FIFO subsystem."
    assert [t.name for t in pkg.typedefs] == ["fifo_mode_e", "fifo_status_t", "fifo_word_t"]

    mode_e = pkg.typedefs[0]
    assert mode_e.kind == "enum"
    assert mode_e.base_type == "logic [1:0]"
    assert [(v.name, v.value, v.doc) for v in mode_e.values] == [
        ("MODE_NORMAL", "0", "Standard FIFO behavior"),
        ("MODE_BYPASS", "1", "Bypass buffering entirely"),
        ("MODE_FLUSH", "2", "Drain and clear on next cycle"),
    ]

    status_t = pkg.typedefs[1]
    assert status_t.kind == "struct"
    assert [(f.name, f.type, f.doc) for f in status_t.fields] == [
        ("full", "logic", "FIFO full flag"),
        ("empty", "logic", "FIFO empty flag"),
        ("count", "logic [7:0]", "Current occupancy"),
    ]

    word_t = pkg.typedefs[2]
    assert word_t.kind == "alias"
    assert word_t.alias_type == "logic [15:0]"
    assert word_t.doc == "Single FIFO data word"

    text = render_package(pkg)
    assert "# Package: `fifo_pkg`" in text
    assert "| `MODE_FLUSH` | 2 | Drain and clear on next cycle |" in text


def test_resolve_types_cross_file():
    mod = parse_module("spike/example_multi_top.sv")
    assert [p.type_ref for p in mod.ports] == [None, None, None]  # unresolved before

    resolve_types(mod, ["spike/example_multi_top.sv", "spike/example_pkg.sv"])
    assert mod.ports[0].type_ref is None  # clk: plain logic, nothing to resolve
    assert mod.ports[1].type_ref == "fifo_pkg::fifo_mode_e"
    assert mod.ports[2].type_ref == "fifo_pkg::fifo_status_t"

    text = render(mod)
    assert "`fifo_pkg::fifo_mode_e`" in text


if __name__ == "__main__":
    test_fifo_example()
    test_fix_fills_gaps_and_is_idempotent()
    test_handshake_interface()
    test_fifo_pkg()
    test_resolve_types_cross_file()
    print("ok")
