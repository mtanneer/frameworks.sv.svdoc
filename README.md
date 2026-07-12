# svdoc

A pydoc-style documentation generator for SystemVerilog RTL, built on
[`pyslang`](https://pypi.org/project/pyslang/) (Python bindings for the
`slang` SystemVerilog compiler).

Extracts Doxygen-style doc comments (`/** @brief ... */`, `///< ...`) from
modules, interfaces, and packages, and renders clean Markdown or HTML
documentation — no manual editing required.

## What it documents today

- **Modules** — name, parameters, ports, doc comments
- **Interfaces** — parameters, ports, signals, modports
- **Packages** — typedefs (enums, packed structs, aliases), functions, tasks
- **Cross-file type resolution** — a module's port typed from a package in
  another file resolves to its fully-qualified `package::type` name

Not yet supported: classes/UVM, instantiation hierarchy, block diagrams, full
multi-file `` `include`` resolution.

## Install

```
pip install svdoc
```

## Usage

```
# print Markdown to stdout
svdoc my_module.sv

# write a .md or .html file instead
svdoc my_module.sv --out md
svdoc my_module.sv --out html

# resolve cross-file types (e.g. a module using a package's enum/struct)
svdoc my_module.sv my_package.sv --out html

# auto-scaffold missing doc comments in place (like `ruff --fix`)
svdoc my_module.sv --fix
```

## Doc comment convention

Doxygen-style, both forms supported:

```systemverilog
/**
 * @brief A simple synchronous FIFO.
 */
module fifo #(
    parameter int DEPTH = 16  ///< Number of entries in the FIFO
) (
    input logic clk  ///< Clock
);
```

## Development

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[docs]"
python test_svdoc.py
```

## License

MIT — see `LICENSE`.
