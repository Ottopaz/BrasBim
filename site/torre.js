// BrasBim: visualizador da torre paramétrica (modelo exportado pelo BrasBim em glTF).
// Parâmetros na URL, para gerar imagens estáticas: ?vista=frente|aerea|baixo|topo&parado&limpo&noite
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const tela = document.getElementById("torre");
if (tela) iniciar(tela);

function iniciar(tela) {
  const params = new URLSearchParams(location.search);
  const parado = params.has("parado") || matchMedia("(prefers-reduced-motion: reduce)").matches;
  const noite = params.has("noite");
  if (params.has("limpo")) document.body.classList.add("limpo");
  if (noite) document.body.classList.add("noite");

  const renderer = new THREE.WebGLRenderer({ canvas: tela, antialias: true, alpha: true,
    preserveDrawingBuffer: params.has("parado") });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = noite ? 0.8 : 1.05;

  const cena = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  cena.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  const camera = new THREE.PerspectiveCamera(30, 1, 1, 3000);
  const controles = new OrbitControls(camera, tela);
  controles.enableDamping = true;
  controles.enableZoom = false;
  controles.enablePan = false;
  controles.autoRotate = !parado;
  controles.autoRotateSpeed = 0.35;
  controles.minPolarAngle = 0.2;
  controles.maxPolarAngle = 1.62;

  // Luz de fim de tarde
  cena.add(new THREE.HemisphereLight(0xfdf6ff, 0xb8a9a0, 0.9));
  const sol = new THREE.DirectionalLight(noite ? 0xffb38a : 0xffe2c4, noite ? 1.2 : 2.6);
  sol.position.set(-90, 230, 120);
  sol.castShadow = true;
  sol.shadow.mapSize.set(2048, 2048);
  Object.assign(sol.shadow.camera, { left: -90, right: 90, top: 140, bottom: -40, near: 10, far: 500 });
  sol.shadow.bias = -0.0004;
  cena.add(sol);

  const chao = new THREE.Mesh(new THREE.CircleGeometry(400, 64),
    new THREE.ShadowMaterial({ opacity: 0.18 }));
  chao.rotation.x = -Math.PI / 2;
  chao.receiveShadow = true;
  cena.add(chao);

  // Materiais de apresentação, escolhidos pela cor que o BrasBim exportou
  const vidro = new THREE.MeshPhysicalMaterial({ color: noite ? 0xffd9a0 : 0x8fb4c8,
    emissive: noite ? 0xffb860 : 0x000000, emissiveIntensity: noite ? 0.55 : 0, metalness: 0.2, roughness: 0.05,
    transparent: true, opacity: 0.45, envMapIntensity: 1.6, side: THREE.DoubleSide, flatShading: true });
  const concreto = new THREE.MeshStandardMaterial({ color: 0xf1eee9, roughness: 0.75, flatShading: true, side: THREE.DoubleSide });
  const metal = new THREE.MeshStandardMaterial({ color: 0x5a3550, metalness: 0.55, roughness: 0.35, flatShading: true, side: THREE.DoubleSide });
  function material(m) {
    if (m.transparent || m.opacity < 1) return vidro;
    const { r, g, b } = m.color;
    if (b > r + 0.02) return metal;  // alumínio: azulado no export
    return concreto;
  }

  const ajustar = () => {
    const w = tela.clientWidth, h = tela.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(ajustar).observe(tela);
  ajustar();

  new GLTFLoader().load(tela.dataset.modelo, (gltf) => {
    const modelo = gltf.scene;
    modelo.traverse((o) => {
      if (!o.isMesh) return;
      o.material = material(o.material);
      o.castShadow = o.material !== vidro;
      o.receiveShadow = true;
    });
    cena.add(modelo);

    const caixa = new THREE.Box3().setFromObject(modelo);
    const centro = caixa.getCenter(new THREE.Vector3());
    modelo.position.x -= centro.x;
    modelo.position.z -= centro.z;
    modelo.position.y -= caixa.min.y;
    const altura = caixa.max.y - caixa.min.y;

    const vistas = {
      frente: { alvo: [0, altura * 0.47, 0], cam: [150, altura * 0.36, 205], deslocar: -0.2 },
      aerea: { alvo: [0, altura * 0.55, 0], cam: [140, altura * 1.5, 170], deslocar: 0 },
      baixo: { alvo: [0, altura * 0.75, 0], cam: [55, 2, 75], deslocar: 0, fov: 50 },
      topo: { alvo: [0, altura, 0], cam: [0.01, altura + 120, 0.01], deslocar: 0, fov: 40 },
    };
    const v = vistas[params.get("vista")] || vistas.frente;
    if (v.fov) camera.fov = v.fov;
    if (params.get("vista") === "topo") controles.minPolarAngle = 0;
    camera.position.set(...v.cam);
    controles.target.set(...v.alvo);
    // empurra a torre para a direita do quadro, deixando o texto livre à esquerda
    deslocamento = v.deslocar;
    ajustar();
    controles.update();
    tela.classList.add("pronta");
    tela.parentElement.classList.add("com-3d");
    document.documentElement.dataset.torre = "pronta";
  });

  let deslocamento = 0;
  const desenhar = () => {
    controles.update();
    const w = tela.clientWidth, h = tela.clientHeight;
    const dx = innerWidth > 900 ? deslocamento * w : 0;
    camera.setViewOffset(w, h, dx, 0, w, h);
    renderer.render(cena, camera);
    requestAnimationFrame(desenhar);
  };
  desenhar();
}
