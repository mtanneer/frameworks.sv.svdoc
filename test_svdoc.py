"""Minimal smoke test for the Phase 1 IR/renderer pipeline."""
from svdoc.parser import parse_module
from svdoc.render_md import render


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


if __name__ == "__main__":
    test_fifo_example()
    print("ok")
