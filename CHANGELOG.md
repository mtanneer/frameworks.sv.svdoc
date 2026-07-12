# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
