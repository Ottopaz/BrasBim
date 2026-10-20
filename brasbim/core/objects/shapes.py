# SPDX-License-Identifier: LGPL-3.0-or-later
"""Peças calculadas → itens IFC do ``Body`` e do símbolo da planta
(``spec/elementos/objeto-parametrico.md`` §2.3 e §3.3).

Caixa e extrusão viram ``IfcExtrudedAreaSolid``; o cilindro é a extrusão de um
``IfcCircleProfileDef``; a revolução, um ``IfcRevolvedAreaSolid`` em torno do z local.
O espelho do objeto (``mirror``) inverte o x local da própria geometria: o posicionamento
do IFC não espelha.
"""

from __future__ import annotations

import math

from brasbim.core.objects.definition import Solid, Stroke


def _pt3(ifc, p):
    return ifc.createIfcCartesianPoint(tuple(float(c) for c in p))


def _pt2(ifc, p):
    return ifc.createIfcCartesianPoint((float(p[0]), float(p[1])))


def _dir(ifc, d):
    return ifc.createIfcDirection(tuple(float(c) for c in d))


def _place3(ifc, location, axis=None, ref=None):
    return ifc.createIfcAxis2Placement3D(
        _pt3(ifc, location), _dir(ifc, axis) if axis else None, _dir(ifc, ref) if ref else None)


def _polygon_profile(ifc, points):
    pts = [_pt2(ifc, p) for p in points]
    return ifc.createIfcArbitraryClosedProfileDef("AREA", None,
                                                  ifc.createIfcPolyline([*pts, pts[0]]))


def _area(points) -> float:
    n = len(points)
    return 0.5 * sum(points[i][0] * points[(i + 1) % n][1] - points[(i + 1) % n][0] * points[i][1]
                     for i in range(n))


def _ccw(points):
    points = [tuple(p) for p in points]
    return points if _area(points) > 0 else points[::-1]


def _box(ifc, s: Solid, m: float):
    w, d, h = s.dims["width"], s.dims["depth"], s.dims["height"]
    a = math.radians(s.rotation)
    c, sn = math.cos(a), math.sin(a)
    cx = s.origin[0] + c * w / 2 - sn * d / 2
    cy = s.origin[1] + sn * w / 2 + c * d / 2
    profile = ifc.createIfcRectangleProfileDef(
        "AREA", None,
        ifc.createIfcAxis2Placement2D(_pt2(ifc, (m * cx, cy)), _dir(ifc, (c, m * sn))), w, d)
    return ifc.createIfcExtrudedAreaSolid(profile, _place3(ifc, (0.0, 0.0, s.origin[2])),
                                          _dir(ifc, (0, 0, 1)), h)


def _cylinder(ifc, s: Solid, m: float):
    r, h = s.dims["radius"], s.dims["height"]
    x, y, z = s.origin
    axis = s.dims.get("axis", "z")
    profile = ifc.createIfcCircleProfileDef("AREA", None, None, r)
    if axis == "z":
        position = _place3(ifc, (m * x, y, z))
    elif axis == "x":
        position = _place3(ifc, (m * x, y, z), (m, 0, 0), (0, 1, 0))
    else:
        position = _place3(ifc, (m * x, y, z), (0, 1, 0), (1, 0, 0))
    return ifc.createIfcExtrudedAreaSolid(profile, position, _dir(ifc, (0, 0, 1)), h)


def _extrusion(ifc, s: Solid, m: float):
    t0, t = s.dims["offset"], s.dims["thickness"]
    dx, dy, dz = s.origin
    plane = s.dims.get("plane", "xy")
    pts = [(m * a, b) if plane in ("xy", "xz") else (a, b) for a, b in s.points]
    profile = _polygon_profile(ifc, _ccw(pts))
    if plane == "xy":
        position = _place3(ifc, (m * dx, dy, t0 + dz))
    elif plane == "xz":
        # local y = z do objeto; extrusão para −y, do fim da espessura até o deslocamento
        position = _place3(ifc, (m * dx, t0 + t + dy, dz), (0, -1, 0), (1, 0, 0))
    else:
        x0 = t0 + dx if m > 0 else -(t0 + t + dx)
        position = _place3(ifc, (x0, dy, dz), (1, 0, 0), (0, 1, 0))
    return ifc.createIfcExtrudedAreaSolid(profile, position, _dir(ifc, (0, 0, 1)), t)


def _revolution(ifc, s: Solid, m: float):
    angle = s.dims["angle"]
    x, y, z = s.origin
    full = angle >= 360 - 1e-9
    phi = 0.0 if (full or m > 0) else math.radians(180.0 - angle)
    ref = (math.cos(phi), math.sin(phi), 0.0)
    axis = (math.sin(phi), -math.cos(phi), 0.0)  # o y local do perfil fica no z do objeto
    profile = _polygon_profile(ifc, _ccw(s.points))
    position = _place3(ifc, (m * x, y, z), axis, ref)
    rev_axis = ifc.createIfcAxis1Placement(_pt3(ifc, (0, 0, 0)), _dir(ifc, (0, 1, 0)))
    return ifc.createIfcRevolvedAreaSolid(profile, position, rev_axis,
                                          math.radians(min(angle, 360.0)))


_BUILD = {"box": _box, "cylinder": _cylinder, "extrusion": _extrusion,
          "revolution": _revolution}


def solid_item(ifc, s: Solid, mirror: bool = False):
    return _BUILD[s.kind](ifc, s, -1.0 if mirror else 1.0)


def curve_items(ifc, strokes: list[Stroke], mirror: bool = False) -> list:
    """Polilinhas 2D do símbolo (``IfcPolyline``), com o x invertido no espelho."""
    m = -1.0 if mirror else 1.0
    out = []
    for st in strokes:
        pts = [_pt2(ifc, (m * x, y)) for x, y in st.points]
        if len(pts) < 2:
            continue
        if st.closed:
            pts = [*pts, pts[0]]
        out.append(ifc.createIfcPolyline(pts))
    return out


def box_item(ifc, box) -> object | None:
    """``IfcBoundingBox`` da caixa (xmin, xmax, ymin, ymax, zmin, zmax)."""
    x0, x1, y0, y1, z0, z1 = box
    if min(x1 - x0, y1 - y0, z1 - z0) <= 1e-6:
        return None
    return ifc.createIfcBoundingBox(_pt3(ifc, (x0, y0, z0)), x1 - x0, y1 - y0, z1 - z0)


def mirrored_box(box, mirror: bool):
    if not mirror or box is None:
        return box
    x0, x1, *rest = box
    return (-x1, -x0, *rest)
