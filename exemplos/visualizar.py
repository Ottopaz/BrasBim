# SPDX-License-Identifier: LGPL-3.0-or-later
"""Converte um IFC numa página HTML com visualizador 3D e abre no navegador.

Uso: python exemplos/visualizar.py modelo.ifc [saida.html]

A geometria é triangulada aqui (ifcopenshell.geom) e embutida na página; o navegador
só baixa a biblioteca three.js. Nada do modelo sai da máquina.
"""

import json
import sys
import webbrowser
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element

_PALETTE = ["#c9a27e", "#9db4c8", "#a8c49a", "#d4b483", "#b9a3c9", "#c99a9a"]

_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BrasBim — __TITLE__</title>
<style>
  html, body { margin: 0; height: 100%; background: #eef0f2; font: 14px system-ui, sans-serif; }
  #painel { position: absolute; top: 12px; left: 12px; background: #fffe; padding: 10px 14px;
            border-radius: 8px; box-shadow: 0 1px 4px #0003; max-width: 280px; }
  #painel h1 { font-size: 15px; margin: 0 0 6px; }
  #painel label { display: block; margin: 2px 0; cursor: pointer; }
  #info { margin-top: 8px; color: #333; min-height: 2.6em; white-space: pre-line; }
  .cor { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; }
</style>
</head>
<body>
<div id="painel">
  <h1>__TITLE__</h1>
  <div id="pavimentos"></div>
  <div id="tipos"></div>
  <div id="info">Clique num elemento para ver os dados.</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
const DATA = __DATA__;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef0f2);
const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 0.05, 1000);
camera.up.set(0, 0, 1);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(devicePixelRatio);
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff, 0x888888, 0.9));
const sun = new THREE.DirectionalLight(0xffffff, 0.6);
sun.position.set(5, -8, 12);
scene.add(sun);

const box = new THREE.Box3();
const meshes = [];
for (const el of DATA.elements) {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(el.verts, 3));
  g.setIndex(el.faces);
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshLambertMaterial({ color: el.color }));
  m.userData = el;
  m.add(new THREE.LineSegments(new THREE.EdgesGeometry(g, 20),
                               new THREE.LineBasicMaterial({ color: 0x333333 })));
  scene.add(m);
  meshes.push(m);
  box.expandByObject(m);
}
const center = box.getCenter(new THREE.Vector3());
const size = box.getSize(new THREE.Vector3()).length() || 10;
const grid = new THREE.GridHelper(Math.ceil(size * 2), Math.ceil(size * 2), 0xbbbbbb, 0xdddddd);
grid.rotation.x = Math.PI / 2;
grid.position.set(center.x, center.y, box.min.z);
scene.add(grid);
camera.position.set(center.x + size * 0.6, center.y - size * 0.9, center.z + size * 0.7);
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.target.copy(center);
controls.update();

function filtros(id, chave, valores, cor) {
  const div = document.getElementById(id);
  for (const v of valores) {
    const l = document.createElement("label");
    const c = document.createElement("input");
    c.type = "checkbox"; c.checked = true;
    c.onchange = () => { for (const m of meshes) if (m.userData[chave] === v)
      m.userData["oculto_" + chave] = !c.checked; atualizar(); };
    l.appendChild(c);
    if (cor) { const s = document.createElement("span"); s.className = "cor";
      s.style.background = cor(v); l.appendChild(s); }
    l.appendChild(document.createTextNode(" " + v));
    div.appendChild(l);
  }
}
function atualizar() {
  for (const m of meshes) m.visible = !m.userData.oculto_storey && !m.userData.oculto_type;
}
const uniq = k => [...new Set(DATA.elements.map(e => e[k]))];
filtros("pavimentos", "storey", uniq("storey"));
filtros("tipos", "type", uniq("type"),
        v => DATA.elements.find(e => e.type === v).color);

const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
let selecionado = null;
renderer.domElement.addEventListener("click", ev => {
  mouse.set(ev.clientX / innerWidth * 2 - 1, -(ev.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(meshes.filter(m => m.visible))[0];
  if (selecionado) selecionado.material.emissive.setHex(0x000000);
  selecionado = hit ? hit.object : null;
  const info = document.getElementById("info");
  if (!selecionado) { info.textContent = "Clique num elemento para ver os dados."; return; }
  selecionado.material.emissive.setHex(0x553300);
  const d = selecionado.userData;
  info.textContent = `${d.ifc_class}  ${d.name || ""}\\nTipo: ${d.type}\\nPavimento: ${d.storey}\\n` +
                     `GlobalId: ${d.guid}` + (d.qto ? "\\n" + d.qto : "");
});
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
(function loop() { requestAnimationFrame(loop); renderer.render(scene, camera); })();
</script>
</body>
</html>
"""


_QTO = {
    "Qto_WallBaseQuantities": (("Length", "Comprimento", "m"), ("Width", "Espessura", "m"),
                               ("Height", "Altura", "m"), ("NetVolume", "Volume", "m³")),
    "Qto_DoorBaseQuantities": (("Width", "Largura", "m"), ("Height", "Altura", "m"),
                               ("Area", "Área", "m²")),
}


def _qto_text(element) -> str:
    parts = []
    for name, fields in _QTO.items():
        q = ifcopenshell.util.element.get_pset(element, name)
        if q:
            break
    else:
        return ""
    for key, label, unit in fields:
        if key in q:
            parts.append(f"{label}: {q[key]:.3f} {unit}".replace(".", ","))
    return "\n".join(parts)


def to_html(ifc_path: str) -> str:
    ifc = ifcopenshell.open(ifc_path)
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    colors: dict[str, str] = {}
    elements = []
    for product in ifc.by_type("IfcElement"):
        if product.is_a("IfcFeatureElementSubtraction") or product.Representation is None:
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
        except RuntimeError:
            continue
        element_type = ifcopenshell.util.element.get_type(product)
        type_name = element_type.Name if element_type else product.is_a()
        color = colors.setdefault(type_name, _PALETTE[len(colors) % len(_PALETTE)])
        container = ifcopenshell.util.element.get_container(product)
        elements.append({
            "guid": product.GlobalId,
            "ifc_class": product.is_a(),
            "name": product.Name,
            "type": type_name,
            "storey": container.Name if container else "—",
            "color": color,
            "qto": _qto_text(product),
            "verts": [round(v, 5) for v in shape.geometry.verts],
            "faces": list(shape.geometry.faces),
        })
    title = Path(ifc_path).stem
    return _HTML.replace("__TITLE__", title).replace("__DATA__", json.dumps({"elements": elements}))


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ifc_path = sys.argv[1]
    out = Path(sys.argv[2] if len(sys.argv) > 2 else Path(ifc_path).with_suffix(".html"))
    out.write_text(to_html(ifc_path), encoding="utf-8")
    print(f"Visualizador gravado em {out}")
    webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
