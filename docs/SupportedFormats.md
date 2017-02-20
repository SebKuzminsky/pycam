Supported formats of PyCAM
==========================

PyCAM can import and export data from and to different formats.

Read the following pages for hints about creating usable models:

-   [Hints for 2D modeling with Inkscape
    (SVG)](Hints_for_2D_modeling_with_Inkscape_(SVG) "wikilink")
-   [Hints for 2D modeling with OpenSCAD
    (DXF)](Hints_for_2D_modeling_with_OpenSCAD_(DXF) "wikilink")
-   [Hints for 3D modeling with OpenSCAD
    (STL)](Hints_for_3D_modeling_with_OpenSCAD_(STL) "wikilink")

STL
---

[STL files](wikipedia:STL_(file_format) "wikilink") describe the surface
of 3D models as a mesh of triangles. The STL format definition describes
an ascii and a binary storage format. Both are supported by PyCAM.

PyCAM can transform 3D models and save the result as an ascii STL file.

DXF
---

[DXF files](wikipedia:DXF_(file_format) "wikilink") can describe 3D or
2D models. PyCAM can import both types. The following DXF primitives are
supported:

-   LINE / POLYLINE / LWPOLYLINE
-   ARC / CIRCLE
-   TEXT / MTEXT
-   3DFACE

SVG
---

[Scalable vector files](wikipedia:Svg "wikilink") can describe 2D
models. They are supposed to be used as contour models for engravings.

You need to install *Inkscape* and *pstoedit* if you want to import SVG
files. Please take a look at the
[requirements](Requirements#Optional_external_programs "wikilink") for
more details.

Additionally you should read the [hints for
Inkscape](Hints_for_2D_modeling_with_Inkscape_(SVG) "wikilink") to avoid
common pitfalls.
