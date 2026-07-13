Example output
===============

``svdoc`` generates documentation from a source ``.sv`` file like this one
(`spike/example.sv
<https://github.com/mtanneer/frameworks.sv.svdoc/blob/main/spike/example.sv>`_):

.. literalinclude:: ../spike/example.sv
   :language: systemverilog

Markdown output (``svdoc example.sv``)
---------------------------------------

.. literalinclude:: examples/fifo.md
   :language: markdown

HTML output
-----------

``svdoc example.sv --out html`` produces a standalone page — see the
`rendered example <fifo.html>`_.
