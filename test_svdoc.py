"""Minimal smoke test for the Phase 1 IR/renderer pipeline and --fix."""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

from svdoc.build import build_site
from svdoc.fixer import fix_file
from svdoc.parser import (
    build_hierarchy,
    parse_interface,
    parse_module,
    parse_package,
    resolve_types,
)
from svdoc.render_diagram import (
    render_hierarchy_dot,
    render_hierarchy_mermaid,
    render_module_symbol_dot,
    render_module_symbol_mermaid,
)
from svdoc.render_html import render as render_html
from svdoc.render_html import render_interface as render_html_interface
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


def test_fix_fills_interface_body_gaps_and_is_idempotent():
    """--fix originally only scaffolded a module/interface's header
    (params/ports) -- interface bodies (signals/modports) were an explicit
    scope gap (see PLAN.md). This covers both: an undocumented signal gets a
    trailing ///< TODO, an undocumented modport gets a leading /** @brief
    TODO */ stub indented to match the modport's own column, not column 0."""
    src = """\
interface my_if;
    logic a;
    logic b;

    modport consumer (
        input a,
        output b
    );
endinterface
"""
    fd, path = tempfile.mkstemp(suffix=".sv")
    os.write(fd, src.encode())
    os.close(fd)
    try:
        assert fix_file(path) is True
        iface = parse_interface(path)
        assert iface.signals[0].doc == "TODO"
        assert iface.signals[1].doc == "TODO"
        assert iface.modports[0].doc == "@brief TODO"

        with open(path) as f:
            text = f.read()
        assert "    /**\n     * @brief TODO\n     */\n    modport consumer" in text

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
    assert "[`fifo_pkg::fifo_mode_e`](fifo_pkg.md#fifo_mode_e)" in text

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
    Port symbols. Found parsing real-world RTL (riscv_cpu2's system.sv).

    Also verifies that such ports get a type_ref of "ifname::modport" (so the
    HTML renderer's existing pkg::type cross-link machinery picks them up
    too), and that the link target matches the anchor render_interface()
    actually emits for that modport."""
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
        assert mod.ports[1].type_ref == "my_if::dut"

        # inline modport quick-view: the full Modport (direction/signals/doc)
        # is attached directly, not just a link, so the HTML can show an
        # expandable ins/outs preview without navigating away
        preview = mod.ports[1].modport_preview
        assert preview is not None
        assert preview.name == "dut"
        assert [(g.direction, g.signals) for g in preview.port_groups] == [
            ("input", ["ready"]),
        ]

        html = render_html(mod)
        assert '<a href="my_if.html#dut">my_if::dut</a>' in html
        assert "<summary>modport <code>dut</code> ins/outs</summary>" in html
        assert "<code>ready</code>" in html  # preview's signal name rendered inline

        iface = parse_interface(path2)
        iface_html = render_html_interface(iface)
        assert 'id="dut"' in iface_html  # link target actually exists
    finally:
        os.remove(path1)
        os.remove(path2)


def test_resolve_types_when_module_is_not_a_top_instance():
    """resolve_types() must still resolve a module's port types even when
    that module is instantiated by another module in the same file set --
    without forcing it as an explicit top module, slang only elaborates
    modules nothing else instantiates, so a non-top module would silently
    get no type_ref/modport_preview at all. Found building a full multi-page
    site (svdoc build) over real-world RTL where most modules are
    instantiated by a top-level system module."""
    leaf_src = """\
module leaf (
    my_if.dut bus
);
endmodule
"""
    if_src = """\
interface my_if;
    logic ready;
    modport dut (input ready);
endinterface
"""
    top_src = """\
module top (
    input logic clk
);
    my_if b();
    leaf u_leaf (b.dut);
endmodule
"""
    fd1, path1 = tempfile.mkstemp(suffix=".sv")
    os.write(fd1, leaf_src.encode())
    os.close(fd1)
    fd2, path2 = tempfile.mkstemp(suffix=".sv")
    os.write(fd2, if_src.encode())
    os.close(fd2)
    fd3, path3 = tempfile.mkstemp(suffix=".sv")
    os.write(fd3, top_src.encode())
    os.close(fd3)
    try:
        leaf = parse_module(path1)
        all_paths = [path1, path2, path3]
        resolve_types(leaf, all_paths)  # `leaf` is NOT a top instance here
        assert leaf.ports[0].type_ref == "my_if::dut"
        assert leaf.ports[0].modport_preview is not None
        assert leaf.ports[0].modport_preview.name == "dut"
    finally:
        os.remove(path1)
        os.remove(path2)
        os.remove(path3)


def test_build_site_markdown_cross_links():
    with tempfile.TemporaryDirectory() as d:
        a, b, out = (os.path.join(d, n) for n in ("top.sv", "my_if.sv", "site"))
        with open(a, "w") as f:
            f.write("module top (\n    my_if.dut bus\n);\nendmodule\n")
        with open(b, "w") as f:
            f.write("interface my_if;\n    logic ready;\n    modport dut (input ready);\nendinterface\n")
        index = build_site([a, b], out, fmt="md")
        assert index.endswith("index.md")
        idx = pathlib.Path(index).read_text()
        assert "[[top]]" in idx and "[[my_if]]" in idx
        assert "[`my_if::dut`](my_if.md#dut)" in pathlib.Path(out, "top.md").read_text()
        assert "### `dut`" in pathlib.Path(out, "my_if.md").read_text()


def test_build_site_generates_working_cross_links():
    """svdoc build (build_site()) writes every construct into one flat
    directory so convention-based cross-links always resolve, unlike
    generating standalone pages into whatever directories the source files
    happen to live in (the original bug report: a module in one folder and
    its interface in another produced a link that pointed nowhere)."""
    mod_src = """\
module top (
    my_if.dut bus  ///< the bus
);
endmodule
"""
    if_src = """\
interface my_if;
    logic ready;
    modport dut (input ready);
endinterface
"""
    src_dir = tempfile.mkdtemp()
    out_dir = tempfile.mkdtemp()
    try:
        mod_path = os.path.join(src_dir, "top.sv")
        if_path = os.path.join(src_dir, "my_if.sv")
        with open(mod_path, "w") as f:
            f.write(mod_src)
        with open(if_path, "w") as f:
            f.write(if_src)

        index_path = build_site([mod_path, if_path], out_dir)
        assert os.path.exists(index_path)
        assert os.path.exists(os.path.join(out_dir, "top.html"))
        assert os.path.exists(os.path.join(out_dir, "my_if.html"))

        with open(os.path.join(out_dir, "top.html")) as f:
            top_html = f.read()
        assert 'href="my_if.html#dut"' in top_html

        # the link must resolve to a real file in the SAME output directory
        assert os.path.exists(os.path.join(out_dir, "my_if.html"))
        with open(os.path.join(out_dir, "my_if.html")) as f:
            if_html = f.read()
        assert 'id="dut"' in if_html

        with open(index_path) as f:
            index_html = f.read()
        assert 'href="top.html"' in index_html
        assert 'href="my_if.html"' in index_html
    finally:
        shutil.rmtree(src_dir)
        shutil.rmtree(out_dir)


def test_build_hierarchy_generate_and_params():
    """build_hierarchy() must resolve per-instance parameter overrides and
    port connections, and expand generate-block instance arrays into
    distinct hierarchical paths (e.g. "top.g[0].u_leaf2" vs
    "top.g[1].u_leaf2") rather than collapsing them into one node."""
    leaf_src = """\
module leaf #(parameter int W = 8) (
    input  logic [W-1:0] a,
    output logic [W-1:0] b
);
endmodule
"""
    top_src = """\
module top (input logic clk);
    logic [7:0] x, y;
    leaf #(.W(8)) u_leaf (.a(x), .b(y));
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g
            leaf #(.W(4)) u_leaf2 (.a(x[3:0]), .b(y[3:0]));
        end
    endgenerate
endmodule
"""
    fd1, path1 = tempfile.mkstemp(suffix=".sv")
    os.write(fd1, leaf_src.encode())
    os.close(fd1)
    fd2, path2 = tempfile.mkstemp(suffix=".sv")
    os.write(fd2, top_src.encode())
    os.close(fd2)
    try:
        root = build_hierarchy("top", [path1, path2])
        assert root.module == "top"
        assert root.path == "top"
        assert len(root.children) == 3

        u_leaf = next(c for c in root.children if c.name == "u_leaf")
        assert u_leaf.path == "top.u_leaf"
        assert u_leaf.module == "leaf"
        assert {p.name: p.value for p in u_leaf.params} == {"W": "8"}
        assert {c.name: c.expr for c in u_leaf.connections} == {"a": "x", "b": "y"}

        gen_paths = sorted(c.path for c in root.children if c.name == "u_leaf2")
        assert gen_paths == ["top.g[0].u_leaf2", "top.g[1].u_leaf2"]
        u_leaf2 = next(c for c in root.children if c.path == "top.g[0].u_leaf2")
        assert {p.name: p.value for p in u_leaf2.params} == {"W": "4"}
    finally:
        os.remove(path1)
        os.remove(path2)


def test_render_module_symbol_diagrams():
    mod = parse_module("spike/example.sv")

    mmd = render_module_symbol_mermaid(mod)
    assert "flowchart LR" in mmd
    assert 'subgraph fifo["fifo"]' in mmd
    assert "wr_data: input" in mmd

    dot = render_module_symbol_dot(mod)
    assert 'digraph "fifo"' in dot
    assert "<wr_data> wr_data: input" in dot


def test_render_hierarchy_diagrams():
    leaf_src = """\
module leaf (input logic a, output logic b);
endmodule
"""
    top_src = """\
module top (input logic clk);
    logic x, y;
    leaf u_leaf (.a(x), .b(y));
endmodule
"""
    fd1, path1 = tempfile.mkstemp(suffix=".sv")
    os.write(fd1, leaf_src.encode())
    os.close(fd1)
    fd2, path2 = tempfile.mkstemp(suffix=".sv")
    os.write(fd2, top_src.encode())
    os.close(fd2)
    try:
        root = build_hierarchy("top", [path1, path2])

        mmd = render_hierarchy_mermaid(root)
        assert "flowchart TD" in mmd
        assert "top --> top_u_leaf" in mmd
        assert "u_leaf\\n(leaf)" in mmd

        dot = render_hierarchy_dot(root)
        assert '"top" -> "top_u_leaf"' in dot

        # depth 0 collapses root's children into a placeholder
        collapsed = render_hierarchy_mermaid(root, max_depth=0)
        assert "1 more" in collapsed
    finally:
        os.remove(path1)
        os.remove(path2)


def test_render_hierarchy_collapses_interface_instances_into_modport_edges():
    """Interface instances (e.g. a handshake_if wiring a producer to a
    consumer) should not appear as their own diagram nodes -- instead the
    two real module instances connected via it get a direct edge labeled
    with the modports involved (issue #6)."""
    if_src = """\
interface handshake_if (input logic clk);
    logic valid;
    modport producer (output valid);
    modport consumer (input valid);
endinterface
"""
    producer_src = """\
module producer (handshake_if.producer p);
endmodule
"""
    consumer_src = """\
module consumer (handshake_if.consumer c);
endmodule
"""
    top_src = """\
module top (input logic clk);
    handshake_if hs (.clk(clk));
    producer u_prod (.p(hs.producer));
    consumer u_cons (.c(hs.consumer));
endmodule
"""
    paths = []
    for src in [if_src, producer_src, consumer_src, top_src]:
        fd, path = tempfile.mkstemp(suffix=".sv")
        os.write(fd, src.encode())
        os.close(fd)
        paths.append(path)
    try:
        root = build_hierarchy("top", paths)
        assert {c.name for c in root.children} == {"hs", "u_prod", "u_cons"}
        hs = next(c for c in root.children if c.name == "hs")
        assert hs.is_interface
        u_prod = next(c for c in root.children if c.name == "u_prod")
        assert not u_prod.is_interface
        assert u_prod.connections[0].interface_instance == "hs"
        assert u_prod.connections[0].modport == "producer"

        mmd = render_hierarchy_mermaid(root)
        assert "hs" not in mmd
        assert "top_u_prod -.producer/consumer.-> top_u_cons" in mmd

        dot = render_hierarchy_dot(root)
        assert "hs" not in dot
        assert '"top_u_prod" -> "top_u_cons" [label="producer/consumer"' in dot
    finally:
        for path in paths:
            os.remove(path)


def test_include_dirs_resolves_cross_directory_include():
    """`include targets resolve automatically when the included file lives
    next to the including file, but real projects often keep a shared
    include/ directory separate from per-module source dirs (the riscv_cpu2
    layout PLAN.md's real-RTL testing found) -- that requires explicitly
    telling the SourceManager where to look via addUserDirectories(), which
    is what the include_dirs param threads through to."""
    src_dir = tempfile.mkdtemp()
    include_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(include_dir, "defs.svh"), "w") as f:
            f.write("`define WIDTH 8\n")
        mod_path = os.path.join(src_dir, "inc_mod.sv")
        with open(mod_path, "w") as f:
            f.write('`include "defs.svh"\nmodule inc_mod (\n    input logic [`WIDTH-1:0] data\n);\nendmodule\n')

        with pytest.raises(ValueError):
            parse_module(mod_path)

        mod = parse_module(mod_path, include_dirs=[include_dir])
        assert mod.ports[0].type == "logic [8-1:0]"
    finally:
        shutil.rmtree(src_dir)
        shutil.rmtree(include_dir)


def test_parser_rejects_pre_11_pyslang():
    script = (
        "import sys, pyslang\n"
        "del pyslang.parsing\n"
        "try:\n"
        "    import svdoc.parser\n"
        "    sys.exit(1)\n"
        "except ImportError as e:\n"
        "    assert 'pyslang>=11.0.0' in str(e)\n"
        "    sys.exit(0)\n"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


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
    test_resolve_types_when_module_is_not_a_top_instance()
    test_build_site_generates_working_cross_links()
    test_build_hierarchy_generate_and_params()
    test_render_hierarchy_collapses_interface_instances_into_modport_edges()
    test_parser_rejects_pre_11_pyslang()
    print("ok")


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
def test_fix_non_ascii_and_closing_paren_same_line(tmp_path, nl):
    """Regression for #32: multibyte chars, stub before `)(`, CRLF round-trip."""
    src = "// ── box ──\nmodule b #(parameter int P = 1)(\n  input logic clk,\n  output logic q\n);\nendmodule\n"
    f = tmp_path / "b.sv"
    f.write_bytes(src.replace("\n", nl).encode())
    assert fix_file(str(f)) is True
    out = f.read_bytes().decode()
    assert "input logic clk,  ///< TODO" in out
    assert "output logic q  ///< TODO" in out
    assert "parameter int P = 1  ///< TODO" in out
    assert fix_file(str(f)) is False  # idempotent
    assert out.count("\n") == out.count(nl)


_PKG_SRC = """\
// ── pkg ──
package p;
    typedef enum logic [1:0] {
        A,
        B
    } st_t;

    typedef struct packed {
        logic x;
        logic y;
    } s_t;

    typedef logic [7:0] byte_t;

    function automatic int f(input int a, input int b);
        return a + b;
    endfunction

    task t(input int n);
    endtask
endpackage
"""


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
def test_fix_scaffolds_package(tmp_path, nl):
    """#29: packages, typedefs (enum/struct/alias), functions/tasks."""
    f = tmp_path / "p.sv"
    f.write_bytes(_PKG_SRC.replace("\n", nl).encode())
    assert fix_file(str(f)) is True
    pkg = parse_package(str(f))
    assert pkg.doc  # the non-ASCII // header already counts as a doc comment
    by = {t.name: t for t in pkg.typedefs}
    assert by["st_t"].doc == "@brief TODO"
    assert [v.doc for v in by["st_t"].values] == ["TODO", "TODO"]
    assert by["s_t"].doc == "@brief TODO"
    assert [x.doc for x in by["s_t"].fields] == ["TODO", "TODO"]
    assert by["byte_t"].doc == "@brief TODO"
    subs = {s.name: s for s in pkg.subroutines}
    assert subs["f"].doc == "@brief TODO"
    assert [a.doc for a in subs["f"].args] == ["TODO", "TODO"]
    assert subs["t"].doc == "@brief TODO"
    assert [a.doc for a in subs["t"].args] == ["TODO"]
    assert fix_file(str(f)) is False


_CLASS_SV = """\
/** A packet – naïve. */
virtual class pkt #(parameter int W = 8, type T = int) extends base;
  /** Payload. */
  rand logic [7:0] data;
  int count; ///< counter
  local int hidden;
  /** Build it. */
  function new(int a, string s = "x");
  endfunction
  /** Send. */
  virtual task send(input int n);
  endtask
  static function int get_id(); return 1; endfunction
  extern function void ext(int q);
endclass
"""


def test_parse_class_standalone_and_renderers(tmp_path):
    from svdoc import render_html, render_md
    from svdoc.ir import ClassDoc
    from svdoc.parser import parse_file

    f = tmp_path / "pkt.sv"
    f.write_text(_CLASS_SV, encoding="utf-8")
    c = parse_file(str(f))
    assert isinstance(c, ClassDoc)
    assert (c.name, c.extends, c.is_virtual) == ("pkt", "base", True)
    assert c.doc == "A packet – naïve."
    assert [(p.name, p.type, p.default) for p in c.params] == [("W", "int", "8"), ("T", "type", "int")]
    props = {p.name: p for p in c.properties}
    assert props["data"].qualifiers == ["rand"] and props["data"].doc == "Payload."
    assert props["count"].doc == "counter" and props["hidden"].doc is None
    assert props["hidden"].qualifiers == ["local"]
    m = {s.name: s for s in c.methods}
    assert m["new"].doc == "Build it." and [a.name for a in m["new"].args] == ["a", "s"]
    assert m["send"].kind == "task" and m["send"].qualifiers == ["virtual"]
    assert m["get_id"].return_type == "int" and m["get_id"].qualifiers == ["static"]
    assert m["ext"].qualifiers == ["extern"] and m["ext"].args[0].name == "q"
    md = render_md.render_class(c)
    assert "# Virtual class: `pkt`" in md and "naïve" in md and "`send`" in md
    html = render_html.render_class(c)
    assert "Extends <code>base</code>" in html and 'id="pkt.send"' in html


def test_parse_class_in_package_and_build_site(tmp_path):
    from pathlib import Path

    from svdoc.build import build_site
    from svdoc.parser import parse_file

    f = tmp_path / "p.sv"
    f.write_text("package p;\n" + _CLASS_SV + "endpackage\n", encoding="utf-8")
    pkg = parse_file(str(f))
    assert [c.name for c in pkg.classes] == ["pkt"]
    other = tmp_path / "solo.sv"
    other.write_text("class solo;\n  int x;\nendclass\n", encoding="utf-8")
    index = build_site([str(f), str(other)], str(tmp_path / "out"))
    text = Path(index).read_text(encoding="utf-8")
    assert 'href="p.html#pkt"' in text and 'href="solo.html"' in text
    assert (tmp_path / "out" / "solo.html").exists()


def _diagram_site(fmt, **kw):
    d = tempfile.mkdtemp()
    top, leaf, out = (os.path.join(d, n) for n in ("top.sv", "leaf.sv", "site"))
    pathlib.Path(leaf).write_text("module leaf (input logic a);\nendmodule\n")
    pathlib.Path(top).write_text("module top (input logic x);\n    leaf u_leaf (.a(x));\nendmodule\n")
    build_site([top, leaf], out, fmt=fmt, **kw)
    return pathlib.Path(out)


def test_build_site_embeds_diagrams_md():
    out = _diagram_site("md")
    top, leaf = (out / "top.md").read_text(), (out / "leaf.md").read_text()
    assert "## Diagram" in top and "```mermaid" in top and "flowchart LR" in top
    assert "## Hierarchy" in top and "flowchart TD" in top
    assert "## Diagram" in leaf and "## Hierarchy" not in leaf  # leaf has no children


def test_build_site_embeds_diagrams_html_and_opt_out():
    out = _diagram_site("html")
    top = (out / "top.html").read_text()
    assert '<pre class="mermaid">' in top and "mermaid@11.4.1" in top
    assert "<h2>Hierarchy</h2>" in top
    off = (_diagram_site("html", diagrams=False) / "top.html").read_text()
    assert "mermaid" not in off

# --- #28: bugs found running svdoc over ibex / OpenTitan / common_cells / axi ---


def test_fix_skips_macro_and_include_expanded_members(tmp_path):
    """Members from `include / macro expansion live in other buffers; their
    offsets must not be spliced into this file (corrupted OpenTitan *_cov_if.sv)."""
    (tmp_path / "decls.svh").write_text(
        "`define DECLARE_THINGS logic a_in_macro; logic b_in_macro;\nlogic from_include;\n"
    )
    f = tmp_path / "c.sv"
    f.write_text(
        'interface cov_if (\n  input logic clk\n);\n  `include "decls.svh"\n'
        "  logic sig;\n  `DECLARE_THINGS\nendinterface\n"
    )
    assert fix_file(str(f)) is True
    out = f.read_text()
    assert "logic sig;  ///< TODO" in out
    assert out.count("TODO") == 3  # brief + clk + sig; nothing leaked from macro/include
    parse_interface(str(f))  # still parses


def test_fix_honours_include_dirs(tmp_path):
    inc = tmp_path / "inc"
    inc.mkdir()
    (inc / "defs.svh").write_text("`define W 8\n")
    src = tmp_path / "m.sv"
    src.write_text('`include "defs.svh"\nmodule m (input logic [`W-1:0] a);\nendmodule\n')
    with pytest.raises(ValueError):
        fix_file(str(src))
    assert fix_file(str(src), [str(inc)]) is True


def test_warnings_do_not_reject_file(tmp_path):
    """IgnoredMacroPaste is warning-severity; real RTL (assert macros) triggers it."""
    f = tmp_path / "w.sv"
    f.write_text("`define M(a) a``_q\nmodule w (input logic x);\n  logic `M(y);\nendmodule\n")
    assert parse_module(str(f)).name == "w"


@pytest.mark.parametrize("body", ["program p; endprogram", "// nothing here"])
def test_file_without_documentable_construct_is_valueerror(tmp_path, body):
    """Used to leak StopIteration (programs, bind-only, ifdef'd-out files)."""
    from svdoc.parser import parse_file

    f = tmp_path / "x.sv"
    f.write_text(body + "\n")
    with pytest.raises(ValueError, match="no module"):
        parse_file(str(f))
    if "program" not in body:  # --fix scaffolds a program's header like a module's
        with pytest.raises(ValueError):
            fix_file(str(f))


def test_parse_error_message_is_readable(tmp_path):
    f = tmp_path / "bad.sv"
    f.write_text("module m(; endmodule\n")
    with pytest.raises(ValueError, match="expected"):
        parse_module(str(f))
