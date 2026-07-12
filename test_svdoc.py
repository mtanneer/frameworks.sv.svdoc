"""Minimal smoke test for the Phase 1 IR/renderer pipeline and --fix."""

import tempfile
import os

from svdoc.fixer import fix_file
from svdoc.parser import parse_interface, parse_module, parse_package, resolve_types
from svdoc.render_md import render, render_interface, render_package
from svdoc.render_html import render as render_html


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
        "clk",
        "rst_n",
        "wr_en",
        "wr_data",
        "full",
        "rd_en",
        "rd_data",
        "empty",
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
    assert [t.name for t in pkg.typedefs] == [
        "fifo_mode_e",
        "fifo_status_t",
        "fifo_word_t",
    ]

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


def test_fifo_util_pkg_subroutines():
    pkg = parse_package("spike/example_func_pkg.sv")
    assert pkg.name == "fifo_util_pkg"
    assert [s.name for s in pkg.subroutines] == ["next_ptr", "do_reset"]

    fn = pkg.subroutines[0]
    assert fn.kind == "function"
    assert fn.return_type == "int"
    assert "next write pointer" in fn.doc
    assert [(a.name, a.direction, a.type, a.doc) for a in fn.args] == [
        ("ptr", "input", "int", "Current pointer value"),
        ("depth", "input", "int", "FIFO depth"),
    ]

    task = pkg.subroutines[1]
    assert task.kind == "task"
    assert task.return_type is None
    assert [(a.name, a.direction, a.doc) for a in task.args] == [
        ("done", "output", "Set when reset completes"),
    ]

    text = render_package(pkg)
    assert "Function returning `int`" in text
    assert "| `ptr` | input | `int` | Current pointer value |" in text


def test_resolve_types_cross_file():
    mod = parse_module("spike/example_multi_top.sv")
    assert [p.type_ref for p in mod.ports] == [None, None, None]  # unresolved before

    resolve_types(mod, ["spike/example_multi_top.sv", "spike/example_pkg.sv"])
    assert mod.ports[0].type_ref is None  # clk: plain logic, nothing to resolve
    assert mod.ports[1].type_ref == "fifo_pkg::fifo_mode_e"
    assert mod.ports[2].type_ref == "fifo_pkg::fifo_status_t"

    text = render(mod)
    assert "`fifo_pkg::fifo_mode_e`" in text

    html = render_html(mod)
    assert '<a href="fifo_pkg.html#fifo_mode_e">fifo_pkg::fifo_mode_e</a>' in html
    assert "<code>clk</code>" in html  # unresolved port still renders plainly


def test_html_escapes_doc_text():
    mod = parse_module("spike/example.sv")
    mod.doc = "uses <script>alert(1)</script> & other stuff"
    html = render_html(mod)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html


def test_interface_typed_port():
    """A module port can itself be an interface reference (e.g. `some_if.modport
    name`), not just a plain data type -- found parsing real-world RTL
    (riscv_cpu2) where every module port was interface-typed."""
    src = """\
module dut (
    my_if.consumer aif  ///< bus connection
);
endmodule
"""
    fd, path = tempfile.mkstemp(suffix=".sv")
    os.write(fd, src.encode())
    os.close(fd)
    try:
        mod = parse_module(path)
        assert mod.ports[0].name == "aif"
        assert mod.ports[0].direction == "interface"
        assert mod.ports[0].type == "my_if.consumer"
        assert mod.ports[0].doc == "bus connection"
    finally:
        os.remove(path)


def test_modport_group_with_multiple_signals():
    """A single modport direction clause can list several signals
    (`input a, b, c`), not just one -- found parsing real-world RTL where
    modport signal lists interleave names with commas."""
    src = """\
interface my_if;
    logic a;
    logic b;
    logic c;

    modport consumer (
        input a, b, c  ///< all three
    );
endinterface
"""
    fd, path = tempfile.mkstemp(suffix=".sv")
    os.write(fd, src.encode())
    os.close(fd)
    try:
        iface = parse_interface(path)
        group = iface.modports[0].port_groups[0]
        assert group.direction == "input"
        assert group.signals == ["a", "b", "c"]
        assert group.doc == "all three"
    finally:
        os.remove(path)


def test_resolve_types_skips_interface_ports():
    """resolve_types() must not crash when a module has an interface-typed
    port (e.g. `some_if.modport name`) alongside plain data-type ports --
    elaborated InterfacePort symbols have no .type attribute, unlike plain
    Port symbols. Found parsing real-world RTL (riscv_cpu2's system.sv)."""
    top_src = """\
module top (
    input  logic  clk,
    my_if.dut     bus
);
endmodule
"""
    if_src = """\
interface my_if;
    logic ready;
    modport dut (input ready);
endinterface
"""
    fd1, path1 = tempfile.mkstemp(suffix=".sv")
    os.write(fd1, top_src.encode())
    os.close(fd1)
    fd2, path2 = tempfile.mkstemp(suffix=".sv")
    os.write(fd2, if_src.encode())
    os.close(fd2)
    try:
        mod = parse_module(path1)
        resolve_types(mod, [path1, path2])  # must not raise
        assert mod.ports[0].name == "clk"
        assert mod.ports[0].type_ref is None
        assert mod.ports[1].name == "bus"
        assert mod.ports[1].direction == "interface"
    finally:
        os.remove(path1)
        os.remove(path2)


if __name__ == "__main__":
    test_fifo_example()
    test_fix_fills_gaps_and_is_idempotent()
    test_handshake_interface()
    test_fifo_pkg()
    test_fifo_util_pkg_subroutines()
    test_resolve_types_cross_file()
    test_html_escapes_doc_text()
    test_interface_typed_port()
    test_modport_group_with_multiple_signals()
    test_resolve_types_skips_interface_ports()
    print("ok")
