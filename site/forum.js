// Seção Fórum: mostra as ideias mais votadas do GitHub Discussions.
// A lista vem de forum.json, gerado por scripts/site/forum_top.py no site.yml.
// Clicar no título abre a descrição (texto puro, sem HTML de terceiros).
const lista = document.getElementById("forum-lista");

function el(tag, classe, texto) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto !== undefined) e.textContent = texto;
  return e;
}

function item(p, posicao) {
  const li = el("li", posicao <= 10 ? "forum-top" : "");
  const detalhes = el("details");
  const resumo = el("summary");

  const votos = el("span", "forum-votos");
  votos.append(el("strong", "", p.votos), p.votos === 1 ? "voto" : "votos");

  const texto = el("span", "forum-texto");
  const partes = [p.respostas === 1 ? "1 resposta" : `${p.respostas} respostas`];
  if (p.autor) partes.push(`por ${p.autor}`);
  texto.append(el("strong", "", `${posicao}. ${p.titulo}`), el("small", "", partes.join(" · ")));

  resumo.append(votos, texto, el("span", "forum-seta"));

  const corpo = el("div", "forum-corpo");
  if (p.descricao) corpo.append(el("p", "forum-descricao", p.descricao));
  const link = el("a", "forum-link", p.cortada ? "Continuar no fórum, votar e responder →" : "Votar e responder no fórum →");
  link.href = p.url;
  corpo.append(link);

  detalhes.append(resumo, corpo);
  li.append(detalhes);
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
