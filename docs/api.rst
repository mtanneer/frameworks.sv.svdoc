API Reference
=============

Doc IR
------

.. automodule:: svdoc.ir
   :members:

Parser
------

.. automodule:: svdoc.parser
   :members: parse_module, parse_interface, parse_package, parse_class, parse_file, resolve_types, build_hierarchy

Markdown renderer
-----------------

.. automodule:: svdoc.render_md
   :members: render, render_interface, render_package, render_class

HTML renderer
-------------

.. automodule:: svdoc.render_html
   :members: render, render_interface, render_package, render_class, page

Diagram renderer
----------------

.. automodule:: svdoc.render_diagram
   :members: render_module_symbol_mermaid, render_module_symbol_dot, render_hierarchy_mermaid, render_hierarchy_dot

Fixer
-----

.. automodule:: svdoc.fixer
   :members: fix_file

Site builder
------------

.. automodule:: svdoc.build
   :members: build_site

CLI
---

.. automodule:: svdoc.cli
   :members: main
