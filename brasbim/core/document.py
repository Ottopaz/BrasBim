# SPDX-License-Identifier: LGPL-3.0-or-later
"""Documento BrasBim: o modelo IFC 4.3 em memória e o acesso a ele."""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.project
import ifcopenshell.api.root

from brasbim.core import IFC_SCHEMA, guid


class OpError(ValueError):
    """Operação inválida ou impossível no estado atual do modelo."""


class Document:
    def __init__(self, ifc: ifcopenshell.file):
        self.ifc = ifc
        self._body = self._axis = self._profile = self._plan_body = None
        # GlobalIds recalculados durante a transação em curso (ver ``ops.history.run``).
        self.changed: set[str] = set()
        # Perfis trocados num tipo de pilar ou viga, apagados depois de refeitos os corpos.
        self.orphan_profiles: list = []
        # Elementos que um pilar, viga ou laje excluído cortava: refeitos na derivação.
        self.cut_victims: set[str] = set()
        # Camadas (spec/ui 18): camada conhecida de cada elemento, montada do IFC na primeira
        # consulta; e a exibição (ocultas, bloqueadas), que não é operação.
        from brasbim.core.display_layers import Display

        self.element_layers: dict | None = None
        self.display = Display()
        # Projeto legal (spec/ui 31 §2–§3): situação conhecida de cada elemento (como as
        # camadas) e o filtro de situação da vista, que não é operação.
        self.element_situations: dict | None = None
        self.situation_view = "project"
        # Elementos travados (spec/ui 39 §5), montado do IFC na primeira consulta.
        self.locked_elements: set[str] | None = None

    # --- criação e arquivo ---------------------------------------------------

    @classmethod
    def new(cls, name: str = "Projeto", project_id: str | None = None) -> Document:
        """Projeto vazio com terreno e edificação, em metros.

        Os GlobalIds do terreno e da edificação derivam do GlobalId do projeto, para que
        dois documentos criados com o mesmo ``project_id`` sejam equivalentes.
        """
        ifc = ifcopenshell.api.project.create_file(version=IFC_SCHEMA)
        project = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcProject", name=name)
        if project_id:
            project.GlobalId = project_id
        pid = project.GlobalId
        units = [
            ifc.createIfcSIUnit(None, "LENGTHUNIT", None, "METRE"),
            ifc.createIfcSIUnit(None, "AREAUNIT", None, "SQUARE_METRE"),
            ifc.createIfcSIUnit(None, "VOLUMEUNIT", None, "CUBIC_METRE"),
            ifc.createIfcSIUnit(None, "PLANEANGLEUNIT", None, "RADIAN"),
            ifc.createIfcSIUnit(None, "MASSUNIT", "KILO", "GRAM"),
        ]
        project.UnitsInContext = ifc.createIfcUnitAssignment(units)

        site = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcSite", name="Terreno")
        building = ifcopenshell.api.root.create_entity(
            ifc, ifc_class="IfcBuilding", name="Edificação"
        )
        guid.stamp(site, pid, "site")
        guid.stamp(building, pid, "building")
        site.ObjectPlacement = local_placement(ifc, None)
        building.ObjectPlacement = local_placement(ifc, site.ObjectPlacement)
        guid.stamp(
            ifcopenshell.api.aggregate.assign_object(ifc, products=[site], relating_object=project),
            pid, "aggregates",
        )
        guid.stamp(
            ifcopenshell.api.aggregate.assign_object(
                ifc, products=[building], relating_object=site
            ),
            site.GlobalId, "aggregates",
        )
        doc = cls(ifc)
        doc.body_context  # noqa: B018 - cria os contextos
        doc.axis_context  # noqa: B018
        doc.profile_context  # noqa: B018
        from brasbim.core import display_layers

        display_layers.setup(doc)  # conjunto inicial de camadas (spec/ui 18 §3.1)
        return doc

    @classmethod
    def open(cls, path: str) -> Document:
        return cls(ifcopenshell.open(path))

    def save(self, path: str) -> None:
        self.ifc.write(path)

    # --- acesso --------------------------------------------------------------

    def find(self, global_id: str):
        try:
            return self.ifc.by_guid(global_id)
        except RuntimeError:
            return None

    def get(self, global_id: str, ifc_class: str | None = None):
        entity = self.find(global_id)
        if entity is None:
            raise OpError(f"objeto {global_id} não existe")
        if ifc_class and not entity.is_a(ifc_class):
            raise OpError(f"{global_id} é {entity.is_a()}, esperado {ifc_class}")
        return entity

    @property
    def project(self):
        return self.ifc.by_type("IfcProject")[0]

    @property
    def building(self):
        buildings = self.ifc.by_type("IfcBuilding")
        if not buildings:
            raise OpError("o projeto não tem edificação")
        return buildings[0]

    def storeys(self) -> list:
        """Pavimentos ordenados pela cota."""
        return sorted(self.ifc.by_type("IfcBuildingStorey"), key=lambda s: s.Elevation or 0.0)

    def storey_above(self, storey) -> object | None:
        storeys = self.storeys()
        i = storeys.index(storey)
        return storeys[i + 1] if i + 1 < len(storeys) else None

    @property
    def body_context(self):
        if self._body is None:
            self._body = self._subcontext("Model", "Body", "MODEL_VIEW")
        return self._body

    @property
    def axis_context(self):
        if self._axis is None:
            self._axis = self._subcontext("Plan", "Axis", "GRAPH_VIEW")
        return self._axis

    @property
    def model_axis_context(self):
        """Eixo 3D de pilares e vigas (representação ``Axis``, ``Curve3D``)."""
        return self._subcontext("Model", "Axis", "MODEL_VIEW")

    @property
    def annotation_context(self):
        """Anotações da planta: cotas, textos, símbolos (spec/ui 13)."""
        return self._subcontext("Plan", "Annotation", "PLAN_VIEW")

    @property
    def footprint_context(self):
        """Contorno dos ambientes (``FootPrint``, spec/ui 13 §3.1)."""
        return self._subcontext("Plan", "FootPrint", "PLAN_VIEW")

    @property
    def profile_context(self):
        """Contorno 3D de portas e janelas (representação ``Profile``)."""
        if self._profile is None:
            self._profile = self._subcontext("Model", "Profile", "ELEVATION_VIEW")
        return self._profile

    @property
    def plan_body_context(self):
        """Estilos de corte da planta (spec/ui 06 §4.3), criado quando for preciso."""
        if self._plan_body is None:
            self._plan_body = self._subcontext("Plan", "Body", "PLAN_VIEW")
        return self._plan_body

    def _subcontext(self, context_type: str, identifier: str, target_view: str):
        for sub in self.ifc.by_type("IfcGeometricRepresentationSubContext"):
            if sub.ContextType == context_type and sub.ContextIdentifier == identifier:
                return sub
        parent = next(
            (
                c
                for c in self.ifc.by_type("IfcGeometricRepresentationContext", include_subtypes=False)
                if c.ContextType == context_type
            ),
            None,
        ) or ifcopenshell.api.context.add_context(self.ifc, context_type=context_type)
        return ifcopenshell.api.context.add_context(
            self.ifc,
            context_type=context_type,
            context_identifier=identifier,
            target_view=target_view,
            parent=parent,
        )


def axis_placement(ifc, origin, z: float, direction):
    return ifc.createIfcAxis2Placement3D(
        ifc.createIfcCartesianPoint((float(origin[0]), float(origin[1]), float(z))),
        ifc.createIfcDirection((0.0, 0.0, 1.0)),
        ifc.createIfcDirection((float(direction[0]), float(direction[1]), 0.0)),
    )


def local_placement(ifc, relative_to, z: float = 0.0, origin=(0.0, 0.0), direction=(1.0, 0.0)):
    return ifc.createIfcLocalPlacement(relative_to, axis_placement(ifc, origin, z, direction))
