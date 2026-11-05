# SPDX-License-Identifier: LGPL-3.0-or-later
"""Exportar IFC 2x3 e IFC 4 (spec/ui 47).

O projeto (IFC 4.3) não muda: a exportação trabalha numa cópia, tira o que as opções
deixam de fora, adapta ao 2x3 o que ele não tem (§3), converte com o
``ifcopenshell.util.schema.Migrator`` (4.3 → 4 → 2x3) e confere o resultado com o
validador do esquema antes de gravar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import ifcopenshell
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.util.element
import ifcopenshell.util.schema
import ifcopenshell.validate

from brasbim.core.document import Document, OpError

VERSIONS = ("IFC2X3", "IFC4", "IFC4X3")
VERSION_LABEL = {"IFC2X3": "IFC 2x3", "IFC4": "IFC 4", "IFC4X3": "IFC 4.3"}
TARGETS = ("coordination", "engineering")
TARGET_LABEL = {"coordination": "Coordenação (todo o modelo)",
                "engineering": "Estrutura e instalações"}
# Destino Estrutura e instalações (§2): o que o engenheiro usa.
ENGINEERING = ("IfcWall", "IfcColumn", "IfcBeam", "IfcSlab", "IfcRoof", "IfcStair",
               "IfcStairFlight", "IfcRailing", "IfcDoor", "IfcWindow", "IfcOpeningElement",
               "IfcSpace", "IfcGrid")
# Classes do IFC 4 que o 2x3 não tem e o equivalente nele (§3).
CLASS_2X3 = {"IfcFurniture": "IfcFurnishingElement",
             "IfcSanitaryTerminal": "IfcFlowTerminal",
             "IfcElectricAppliance": "IfcFlowTerminal",
             "IfcGeographicElement": "IfcBuildingElementProxy",
             "IfcDoorType": "IfcDoorStyle", "IfcWindowType": "IfcWindowStyle"}
APPLICATION = "BrasBim"


@dataclass
class Options:
    version: str = "IFC2X3"
    target: str = "coordination"
    visible_only: bool = False
    drawings: bool = False  # desenhos 2D (só IFC 4 e 4.3)
    own_properties: bool = True  # Psets BrasBim_*


@dataclass
class Report:
    version: str
    elements: int = 0
    adapted: dict[str, int] = field(default_factory=dict)

    def count(self, what: str, n: int = 1) -> None:
        if n:
            self.adapted[what] = self.adapted.get(what, 0) + n

    def text(self, path: str) -> str:
        out = f"{VERSION_LABEL[self.version]} exportado ({self.elements} elementos): {path}"
        if self.adapted:
            out += "; adaptado: " + ", ".join(f"{n} {k}" for k, n in sorted(
                self.adapted.items()))
        return out


# --- filtro ------------------------------------------------------------------------------


def _wanted(doc: Document, element, options: Options, hidden: set[str]) -> bool:
    if element.GlobalId in hidden:
        return False
    if element.is_a("IfcAnnotation"):
        return options.drawings and options.version != "IFC2X3"
    if options.target == "engineering":
        from brasbim.core.structure import stairs

        if stairs.stair_of(element) is not None:
            return True
        return any(element.is_a(c) for c in ENGINEERING)
    return True


def _hidden(doc: Document) -> set[str]:
    """Ocultos na janela: camadas, filtro de situação e ocultos só dela."""
    from brasbim.core import display_layers

    return set(display_layers.hidden_ids(doc))


def _strip(doc: Document, f, options: Options) -> None:
    """Tira da cópia os produtos que não vão e, se pedido, os Psets do BrasBim."""
    hidden = _hidden(doc) if options.visible_only else set()
    gone = []
    for element in f.by_type("IfcProduct"):
        if element.is_a("IfcSpatialStructureElement") and not element.is_a("IfcSpace"):
            continue
        original = doc.find(element.GlobalId)
        if original is not None and not _wanted(doc, original, options, hidden):
            gone.append(element)
    keep = {e.GlobalId for e in f.by_type("IfcProduct")} - {e.GlobalId for e in gone}
    # vão e esquadria saem com a parede que sai
    for element in list(gone):
        for rel in getattr(element, "HasOpenings", ()) or ():
            opening = rel.RelatedOpeningElement
            gone.append(opening)
            for fill in opening.HasFillings or ():
                gone.append(fill.RelatedBuildingElement)
    seen = set()
    for element in gone:
        if element.id() in seen or element.GlobalId in keep - {element.GlobalId}:
            continue
        seen.add(element.id())
        try:
            ifcopenshell.api.root.remove_product(f, product=element)
        except RuntimeError:
            continue
    if not options.own_properties:
        for pset in list(f.by_type("IfcPropertySet")):
            if (pset.Name or "").startswith("BrasBim_"):
                owners = [o for rel in pset.DefinesOccurrence or ()
                          for o in rel.RelatedObjects] if hasattr(pset, "DefinesOccurrence") \
                    else []
                owners += list(getattr(pset, "DefinesType", ()) or ())
                for owner in owners:
                    ifcopenshell.api.pset.remove_pset(f, product=owner, pset=pset)
                    break
                else:
                    f.remove(pset)
    # relações que ficaram sem um dos lados (lista vazia ou elemento apagado) saem
    for rel in list(f.by_type("IfcRelationship")):
        info = rel.get_info(recursive=False)
        if any(v == () for v in info.values()):
            f.remove(rel)


# --- adaptações do 2x3 (na cópia em 4.3, antes de converter) -----------------------------


def _replace(f, old, new) -> None:
    for inverse in f.get_inverse(old):
        for i, value in enumerate(inverse):
            if value == old:
                inverse[i] = new
            elif isinstance(value, tuple) and old in value:
                inverse[i] = tuple(new if v == old else v for v in value)


def _polylines(f, report: Report) -> None:
    for curve in list(f.by_type("IfcIndexedPolyCurve")):
        coords = curve.Points.CoordList
        order = list(range(len(coords)))
        if curve.Segments:
            order = []
            for seg in curve.Segments:
                for i in seg.wrappedValue:
                    if not order or order[-1] != i - 1:
                        order.append(i - 1)
        points = [f.createIfcCartesianPoint(tuple(float(c) for c in coords[i])) for i in order]
        new = f.createIfcPolyline(points)
        _replace(f, curve, new)
        point_list = curve.Points
        f.remove(curve)
        if not f.get_inverse(point_list):
            f.remove(point_list)
        report.count("curvas indexadas em polilinha")


def _closed(faces) -> bool:
    edges = {}
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1], strict=True):
            key = (min(a, b), max(a, b))
            edges[key] = edges.get(key, 0) + 1
    return bool(edges) and all(n == 2 for n in edges.values())


def _breps(f, report: Report) -> None:
    for mesh in list(f.by_type("IfcTriangulatedFaceSet")) + list(
            f.by_type("IfcPolygonalFaceSet")):
        coords = mesh.Coordinates.CoordList
        if mesh.is_a("IfcTriangulatedFaceSet"):
            faces = [[i - 1 for i in tri] for tri in mesh.CoordIndex]
        else:
            faces = [[i - 1 for i in face.CoordIndex] for face in mesh.Faces]
        points = [f.createIfcCartesianPoint(tuple(float(c) for c in p)) for p in coords]
        ifc_faces = [f.createIfcFace([f.createIfcFaceOuterBound(
            f.createIfcPolyLoop([points[i] for i in face]), True)]) for face in faces]
        if _closed(faces):
            new = f.createIfcFacetedBrep(f.createIfcClosedShell(ifc_faces))
            kind = "Brep"
        else:
            new = f.createIfcShellBasedSurfaceModel([f.createIfcOpenShell(ifc_faces)])
            kind = "SurfaceModel"
        for rep in [r for r in f.get_inverse(mesh) if r.is_a("IfcShapeRepresentation")]:
            rep.RepresentationType = kind
        _replace(f, mesh, new)
        point_list = mesh.Coordinates
        f.remove(mesh)
        if not f.get_inverse(point_list):
            f.remove(point_list)
        report.count("malhas em faces")


def _material_names(material) -> list:
    if material.is_a("IfcMaterial"):
        return [material]
    if material.is_a("IfcMaterialProfileSetUsage"):
        material = material.ForProfileSet
    if material.is_a("IfcMaterialProfileSet"):
        found = [p.Material for p in material.MaterialProfiles or () if p.Material]
    elif material.is_a("IfcMaterialConstituentSet"):
        found = [c.Material for c in material.MaterialConstituents or () if c.Material]
    else:
        return []
    return list(dict.fromkeys(found))


def _materials(f, report: Report) -> None:
    """Perfil e constituintes viram o material (ou a lista deles), como no 2x3."""
    for rel in f.by_type("IfcRelAssociatesMaterial"):
        material = rel.RelatingMaterial
        if not material.is_a() in ("IfcMaterialProfileSet", "IfcMaterialProfileSetUsage",
                                   "IfcMaterialConstituentSet"):
            continue
        found = _material_names(material)
        if not found:
            f.remove(rel)
            continue
        rel.RelatingMaterial = found[0] if len(found) == 1 else f.createIfcMaterialList(found)
        report.count("materiais de perfil ou de partes em lista")
    for cls in ("IfcMaterialProfileSetUsage", "IfcMaterialProfileSet",
                "IfcMaterialConstituentSet", "IfcMaterialProfile", "IfcMaterialConstituent"):
        for e in list(f.by_type(cls)):
            if not f.get_inverse(e) or all(i.is_a() in (
                    "IfcMaterialProfileSet", "IfcMaterialProfileSetUsage",
                    "IfcMaterialConstituentSet", "IfcMaterialProfile",
                    "IfcMaterialConstituent") for i in f.get_inverse(e)):
                try:
                    f.remove(e)
                except RuntimeError:
                    pass
    # o que sobrou pendurado (ex.: o CompositeProfile do perfil só no conjunto) fica: o
    # corpo ainda usa o perfil


def _cleanup_material_sets(f) -> None:
    for cls in ("IfcMaterialProfileSetUsage", "IfcMaterialProfileSet",
                "IfcMaterialConstituentSet", "IfcMaterialProfile", "IfcMaterialConstituent"):
        for e in list(f.by_type(cls)):
            f.remove(e)


def _prepare_2x3(f, report: Report) -> dict[str, tuple]:
    """Adapta a cópia em 4.3; devolve {GlobalId: (classe de origem, operação)} das que
    mudam de classe no 2x3."""
    for rel in list(f.by_type("IfcRelInterferesElements")):
        f.remove(rel)
        report.count("recortes (já no corpo)")
    for cls in ("IfcMapConversion", "IfcProjectedCRS"):
        for e in list(f.by_type(cls)):
            f.remove(e)
    _polylines(f, report)
    _breps(f, report)
    _materials(f, report)
    _cleanup_material_sets(f)
    origin = {}
    for cls in CLASS_2X3:
        for e in f.by_type(cls, include_subtypes=False):
            # a operação do estilo: a da porta, ou a divisão da janela (mesmos nomes)
            operation = getattr(e, "OperationType", None) if cls == "IfcDoorType" else                 getattr(e, "PartitioningType", None) if cls == "IfcWindowType" else None
            origin[e.GlobalId] = (cls, operation)
    return origin


# Tipos de valor do IFC 4 sem igual no 2x3 (ou que ficaram restritos nele).
VALUE_2X3 = {"IfcNonNegativeLengthMeasure": "IfcLengthMeasure",
             "IfcPositiveInteger": "IfcInteger", "IfcDate": "IfcLabel",
             "IfcDateTime": "IfcLabel", "IfcTime": "IfcLabel", "IfcDuration": "IfcLabel",
             "IfcURIReference": "IfcLabel", "IfcBinary": "IfcLabel",
             "IfcCardinalPointReference": "IfcInteger"}


def _values_2x3(f) -> None:
    """Troca, no arquivo em IFC 4, os valores de tipos que o 2x3 não tem."""
    for e in list(f):
        for i, value in enumerate(e):
            if isinstance(value, ifcopenshell.entity_instance) and value.id() == 0                     and value.is_a() in VALUE_2X3:
                e[i] = f.create_entity(VALUE_2X3[value.is_a()], _plain(value))
            elif isinstance(value, tuple) and any(
                    isinstance(v, ifcopenshell.entity_instance) and v.id() == 0
                    and v.is_a() in VALUE_2X3 for v in value):
                e[i] = tuple(f.create_entity(VALUE_2X3[v.is_a()], _plain(v))
                             if isinstance(v, ifcopenshell.entity_instance) and v.id() == 0
                             and v.is_a() in VALUE_2X3 else v for v in value)


def _plain(value):
    v = value.wrappedValue
    target = VALUE_2X3[value.is_a()]
    if target == "IfcLabel":
        return str(v)
    if target == "IfcInteger":
        return int(v)
    return float(v)


# --- depois de converter -----------------------------------------------------------------


def _owner_history(f):
    person = f.createIfcPerson(None, None, "BrasBim", None, None, None, None, None)
    org = f.createIfcOrganization(None, "BrasBim", None, None, None)
    user = f.createIfcPersonAndOrganization(person, org, None)
    from brasbim import __version__ as version

    app = f.createIfcApplication(org, str(version), APPLICATION, APPLICATION)
    return f.createIfcOwnerHistory(user, app, None, "ADDED", None, None, None,
                                   int(time.time()))


def _finish_2x3(f, origin: dict[str, tuple], report: Report) -> None:
    found = f.by_type("IfcOwnerHistory")
    history = found[0] if found else _owner_history(f)
    for e in f.by_type("IfcRoot"):
        if e.OwnerHistory is None:
            e.OwnerHistory = history
    for gid, (cls, operation) in origin.items():
        try:
            e = f.by_guid(gid)
        except RuntimeError:
            continue
        target = CLASS_2X3[cls]
        if e.is_a("IfcBuildingElementProxyType") or e.is_a("IfcTypeObject"):
            e = ifcopenshell.util.schema.reassign_class(f, e, target)
            if target in ("IfcDoorStyle", "IfcWindowStyle"):
                e.ConstructionType = "NOTDEFINED"
                e.ParameterTakesPrecedence = False
                e.Sizeable = False
                e.OperationType = _style_operation(target, operation)
            report.count("tipos de esquadria em estilos" if target.endswith("Style")
                         else "tipos adaptados")
            continue
        if target != "IfcBuildingElementProxy":
            e = ifcopenshell.util.schema.reassign_class(f, e, target)
        if hasattr(e, "ObjectType") and not e.ObjectType:
            e.ObjectType = cls[3:]
        report.count({"IfcFurnishingElement": "móveis", "IfcFlowTerminal": "louças e aparelhos",
                      "IfcBuildingElementProxy": "terrenos como peça genérica"}[target])
    # paredes de camadas com eixo: IfcWallStandardCase (visão de coordenação 2.0)
    for wall in list(f.by_type("IfcWall", include_subtypes=False)):
        material = ifcopenshell.util.element.get_material(wall, should_inherit=False)
        reps = {r.RepresentationIdentifier for r in (
            wall.Representation.Representations if wall.Representation else ())}
        if material is not None and material.is_a("IfcMaterialLayerSetUsage") \
                and "Axis" in reps:
            ifcopenshell.util.schema.reassign_class(f, wall, "IfcWallStandardCase")
            report.count("paredes como IfcWallStandardCase")
    _styles_2x3(f)
    _required_enums(f)


def _style_operation(target: str, operation) -> str:
    import ifcopenshell.ifcopenshell_wrapper as wrapper

    enum = wrapper.schema_by_name("IFC2X3").declaration_by_name(
        "IfcDoorStyleOperationEnum" if target == "IfcDoorStyle"
        else "IfcWindowStyleOperationEnum")
    return operation if operation in enum.enumeration_items() else "NOTDEFINED"


def _required_enums(f) -> None:
    """Enumerados obrigatórios no 2x3 que o IFC 4 deixa vazios: ``NOTDEFINED``."""
    import ifcopenshell.ifcopenshell_wrapper as wrapper

    schema = wrapper.schema_by_name(f.schema_identifier)
    cache = {}
    for e in f:
        cls = e.is_a()
        if cls not in cache:
            fields = []
            for i, attr in enumerate(schema.declaration_by_name(cls).all_attributes()):
                kind = attr.type_of_attribute()
                while hasattr(kind, "declared_type") and not isinstance(
                        kind.declared_type(), wrapper.enumeration_type):
                    kind = kind.declared_type()
                    if not hasattr(kind, "declared_type"):
                        break
                enum = kind.declared_type() if hasattr(kind, "declared_type") else None
                if not attr.optional() and isinstance(enum, wrapper.enumeration_type)                         and "NOTDEFINED" in enum.enumeration_items():
                    fields.append(i)
            cache[cls] = fields
        for i in cache[cls]:
            if e[i] is None:
                e[i] = "NOTDEFINED"


def _styles_2x3(f) -> None:
    """No 2x3 o ``IfcStyledItem`` aponta para ``IfcPresentationStyleAssignment``."""
    for item in f.by_type("IfcStyledItem"):
        styles = list(item.Styles or ())
        loose = [s for s in styles if not s.is_a("IfcPresentationStyleAssignment")]
        if loose:
            kept = [s for s in styles if s.is_a("IfcPresentationStyleAssignment")]
            item.Styles = [*kept, f.createIfcPresentationStyleAssignment(loose)]


# --- conversão ---------------------------------------------------------------------------


def _migrate(src, schema: str, proxies: bool):
    import contextlib
    import io

    out = ifcopenshell.file(schema=schema)
    migrator = ifcopenshell.util.schema.Migrator(fallback_element_to_proxy=proxies)
    # o conversor imprime cada atributo sem equivalente (estilo de hachura, número de
    # degraus do 2x3): não é erro, e o arquivo é conferido no fim
    with contextlib.redirect_stdout(io.StringIO()):
        for e in src:
            migrator.migrate(e, out)
    return out


def errors(f) -> list[str]:
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(f, log)
    return [s.get("message", str(s)) for s in log.statements]


def build(doc: Document, options: Options | None = None) -> tuple[object, Report]:
    """O arquivo exportado (em memória) e o relatório do que foi adaptado."""
    options = options or Options()
    if options.version not in VERSIONS:
        raise OpError(f"versão de IFC inválida: {options.version!r}")
    if options.target not in TARGETS:
        raise OpError(f"destino inválido: {options.target!r}")
    report = Report(options.version)
    src = ifcopenshell.file.from_string(doc.ifc.to_string())
    _strip(doc, src, options)
    if options.version == "IFC4X3":
        out = src
    elif options.version == "IFC4":
        out = _migrate(src, "IFC4", False)
    else:
        origin = _prepare_2x3(src, report)
        mid = _migrate(src, "IFC4", False)
        _values_2x3(mid)
        history = _owner_history(mid)  # um só, senão o conversor cria um por entidade
        for e in mid.by_type("IfcRoot"):
            if e.OwnerHistory is None:
                e.OwnerHistory = history
        out = _migrate(mid, "IFC2X3", True)
        _finish_2x3(out, origin, report)
    report.elements = len([e for e in out.by_type("IfcProduct")
                           if not e.is_a("IfcSpatialStructureElement")
                           and not e.is_a("IfcOpeningElement")
                           and not e.is_a("IfcAnnotation")]) + len(
        out.by_type("IfcSpace"))
    return out, report


def export(doc: Document, path: str, options: Options | None = None) -> Report:
    """Grava o IFC na versão pedida; recusa se o arquivo não passa no validador."""
    out, report = build(doc, options)
    found = errors(out)
    if found:
        raise OpError(f"o IFC exportado não passou na conferência: {found[0]}"
                      + (f" (e mais {len(found) - 1})" if len(found) > 1 else ""))
    out.write(str(path))
    return report
