Stability and conventions (1.0)
===============================

From 1.0.0, ``svdoc`` follows `semantic versioning <https://semver.org>`_
for the surface listed under *Stable* below. Anything not listed is internal
and may change in any release.

Stable
------

* **CLI**: the commands ``svdoc <file>``, ``svdoc build``, ``svdoc hierarchy``
  and their documented flags (``--out``, ``--fix``, ``--diagrams``,
  ``--include-dir``, ``--out-dir``, ``--format``, ``--no-diagrams``,
  ``--strict``, ``--out-file``, ``--max-depth``). Exit status: non-zero on
  error.
* **Python API** (documented in :doc:`api`): ``parse_module``,
  ``parse_interface``, ``parse_package``, ``parse_class``, ``parse_file``,
  ``resolve_types``, ``build_hierarchy``, ``fix_file``, ``build_site``, the
  ``render*`` functions in ``svdoc.render_md`` / ``svdoc.render_html`` /
  ``svdoc.render_diagram``, and their documented parameters.
* **IR** (``svdoc.ir``): the dataclasses and their existing fields. In 1.x
  fields are only *added* (always with a default) -- never removed, renamed
  or retyped.

Not covered
-----------

* Names starting with ``_`` and anything not documented in :doc:`api`.
* The exact markup of generated output: HTML structure, CSS, element ids
  other than the documented ``page.html#member`` anchors, Markdown
  whitespace, Mermaid/dot text. Output may be refined in minor releases.
* The pinned Mermaid CDN version embedded in HTML pages.
* ``pyslang`` objects. ``svdoc`` pins a compatible ``pyslang`` range; the IR
  deliberately holds only plain strings and dataclasses.

Doc-comment convention (final)
------------------------------

Doxygen-style, verified against pyslang trivia:

* Leading block ``/** @brief ... @param x ... */`` above a module, interface,
  package, class, typedef, modport or subroutine.
* Trailing ``///< text`` after a port, parameter, signal, enum value, struct
  field, class property or subroutine argument.

Visibility rule (final)
-----------------------

Everything is documented: every port, parameter and member appears in the
output whether or not it has a doc comment. There is no opt-in or opt-out
marker. ``svdoc --fix`` scaffolds ``TODO`` stubs for the gaps, so
undocumented items are easy to find and fill.
