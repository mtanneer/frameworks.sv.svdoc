# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-07-12

### Added
- Block diagram rendering (Phase 4): module symbol view (single-module box +
  ports) and hierarchical instance-tree diagrams, both as Mermaid flowchart
  and Graphviz dot text, with depth-collapsing for large hierarchies
  - `svdoc file.sv --out mmd|dot` — module symbol diagram
  - `svdoc hierarchy <top_module> <files...> --out-file X --format mmd|dot
    --max-depth N` — hierarchical block diagram
- CI: secret-scan (gitleaks) gates a pytest run with coverage floor
- `` `include`` resolution across directories (`--include-dir`), closing the
  last Phase 2 multi-file gap
- `--fix` now scaffolds interface body gaps (signals/modports), not just
  headers

### Known limitations
- Hierarchy diagrams render interface instances as their own nodes rather
  than collapsing them into labeled modport connections between real module
  blocks (tracked in #6)
- No diagram embedding into Markdown/HTML doc pages yet
- Classes/UVM not parsed

## [0.2.0] - 2026-07-11

### Added
- Instance hierarchy IR: `build_hierarchy(module_name, paths)` elaborates a
  module as top and walks the real instance tree, resolving per-instance
  parameter overrides (post `#(...)` override) and port connection
  expressions
- `generate`-block instance arrays expand into distinct hierarchical paths
  (e.g. `top.g[0].u_leaf2`, `top.g[1].u_leaf2`) rather than collapsing

### Known limitations
- No block diagram rendering yet from the instance hierarchy (planned,
  Phase 4)
- Classes/UVM not parsed
- Multi-file resolution covers a module + the packages/interfaces it
  directly depends on, not full `` `include`` resolution

## [0.1.0] - 2026-07-12

Initial release.

### Added
- Doc extraction for modules, interfaces (ports, signals, modports), and
  packages (typedefs, enums, structs, functions, tasks)
- Doxygen-style doc comment parsing (`/** @brief ... */`, `///< ...`)
- Markdown and HTML renderers (`svdoc file.sv --out md|html`)
- Cross-file type resolution — package- and interface-typed ports resolve
  and cross-link to their definitions
- Inline modport preview in HTML output
- `svdoc build` — generates a full linked multi-page HTML site from any
  number of files, regardless of source directory layout
- `svdoc --fix` — auto-scaffolds missing doc comments in place

### Known limitations
- Classes/UVM not parsed
- No instantiation hierarchy or block diagrams (planned, Phase 3/4)
- Multi-file resolution covers a module + the packages/interfaces it
  directly depends on, not full `` `include`` resolution
