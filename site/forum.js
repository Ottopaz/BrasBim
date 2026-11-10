// Seção Fórum: mostra as postagens mais votadas do GitHub Discussions.
// A lista vem de forum.json, gerado por scripts/site/forum_top.py no site.yml.
const lista = document.getElementById("forum-lista");

function item(p, posicao) {
  const li = document.createElement("li");
  if (posicao <= 10) li.className = "forum-top";
  const a = document.createElement("a");
  a.href = p.url;

  const votos = document.createElement("span");
  votos.className = "forum-votos";
  const n = document.createElement("strong");
  n.textContent = p.votos;
  votos.append(n, p.votos === 1 ? "voto" : "votos");

  const texto = document.createElement("span");
  texto.className = "forum-texto";
  const titulo = document.createElement("strong");
  titulo.textContent = `${posicao}. ${p.titulo}`;
  const meta = document.createElement("small");
  const partes = [];
  partes.push(p.respostas === 1 ? "1 resposta" : `${p.respostas} respostas`);
  if (p.autor) partes.push(`por ${p.autor}`);
  meta.textContent = partes.join(" · ");
  texto.append(titulo, meta);

  a.append(votos, texto);
  li.append(a);
  return li;
}

fetch("forum.json", { cache: "no-cache" })
  .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
  .then((dados) => {
    const postagens = dados.postagens || [];
    if (!postagens.length) return; // fica a mensagem de fórum vazio
    lista.replaceChildren(...postagens.map((p, i) => item(p, i + 1)));
  })
  .catch(() => {}); // sem a lista, os botões continuam levando ao fórum
