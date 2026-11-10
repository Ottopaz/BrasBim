"""Ranking do fórum (GitHub Discussions) do BrasBim.

Busca as discussões abertas do repositório, ordena por votos e grava as 30 primeiras
num JSON que a página inicial do site mostra (seção Fórum, com as 10 primeiras em
destaque: são as que entram no desenvolvimento).

Regras do ranking:
- só a categoria Ideias (aceita o nome antigo do GitHub, "Ideas", e o slug);
- só discussões abertas: ao implementar uma ideia, feche a discussão e ela sai da lista;
- mais votos primeiro; no empate, mais respostas; no empate, a mais nova.

Uso:
    python scripts/site/forum_top.py site/forum.json   # grava o JSON (usado no site.yml)
    python scripts/site/forum_top.py                    # só mostra o ranking no terminal

Precisa de um token do GitHub na variável GITHUB_TOKEN (no Actions já vem pronto; no
computador, crie um em github.com/settings/tokens, sem permissão extra, só leitura
pública). Se falhar (Discussions desligado, sem rede, sem token), grava a lista vazia e
termina sem erro, para não travar a publicação do site.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

DONO, REPO = "Ottopaz", "BrasBim"
QUANTOS = 30  # o site mostra 30; as 10 primeiras entram no desenvolvimento
CATEGORIAS = {"ideias", "ideas"}  # nome ou slug da categoria, sem diferenciar maiúsculas

CONSULTA = """
query($dono: String!, $repo: String!, $depois: String) {
  repository(owner: $dono, name: $repo) {
    discussions(first: 100, after: $depois, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        title url createdAt closed upvoteCount
        comments { totalCount }
        category { name slug }
        author { login }
      }
    }
  }
}
"""


def buscar(token: str) -> list[dict]:
    discussoes: list[dict] = []
    depois = None
    for _ in range(20):  # até 2000 discussões; folga de sobra
        corpo = json.dumps({
            "query": CONSULTA,
            "variables": {"dono": DONO, "repo": REPO, "depois": depois},
        }).encode()
        pedido = urllib.request.Request(
            "https://api.github.com/graphql", data=corpo,
            headers={"Authorization": f"Bearer {token}", "User-Agent": "brasbim-forum"},
        )
        with urllib.request.urlopen(pedido, timeout=30) as resposta:
            dados = json.load(resposta)
        if dados.get("errors"):
            raise RuntimeError(dados["errors"][0].get("message", "erro na API"))
        pagina = dados["data"]["repository"]["discussions"]
        discussoes += pagina["nodes"]
        if not pagina["pageInfo"]["hasNextPage"]:
            break
        depois = pagina["pageInfo"]["endCursor"]
    return discussoes


def ranquear(discussoes: list[dict]) -> list[dict]:
    def e_ideia(d: dict) -> bool:
        cat = d.get("category") or {}
        return bool({cat.get("name", "").lower(), cat.get("slug", "").lower()} & CATEGORIAS)

    abertas = [d for d in discussoes if not d["closed"] and e_ideia(d)]
    abertas.sort(key=lambda d: d["createdAt"], reverse=True)
    abertas.sort(key=lambda d: (d["upvoteCount"], d["comments"]["totalCount"]), reverse=True)
    return [
        {
            "titulo": d["title"],
            "url": d["url"],
            "votos": d["upvoteCount"],
            "respostas": d["comments"]["totalCount"],
            "categoria": d["category"]["name"] if d.get("category") else "",
            "autor": (d.get("author") or {}).get("login", ""),
            "criada": d["createdAt"],
        }
        for d in abertas[:QUANTOS]
    ]


def main() -> int:
    destino = sys.argv[1] if len(sys.argv) > 1 else None
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        if not token:
            raise RuntimeError("defina GITHUB_TOKEN")
        top = ranquear(buscar(token))
    except Exception as erro:  # noqa: BLE001 - nunca travar a publicação do site
        print(f"Fórum: não deu para buscar as discussões ({erro}).", file=sys.stderr)
        top = []

    if destino:
        saida = {"atualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "postagens": top}
        with open(destino, "w", encoding="utf-8") as arquivo:
            json.dump(saida, arquivo, ensure_ascii=False, indent=1)
        print(f"Fórum: {len(top)} postagens gravadas em {destino}.")
    else:
        for i, p in enumerate(top, 1):
            if i == 11:
                print("---- (acima: as 10 que entram no desenvolvimento) ----")
            print(f"{i:2}. [{p['votos']} votos, {p['respostas']} respostas] {p['titulo']}")
            print(f"    {p['url']}")
        if not top:
            print("Nenhuma discussão aberta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
