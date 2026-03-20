"""
Gera JSONs individuais por deputado em docs/deputados/{id}.json.

Lê dados de:
  - data/raw/deputados_detalhes_*.json (detalhes de proposições, discursos, órgãos)
  - docs/ranking.json (score, rank, dados básicos)

Uso: python src/site/build_details.py
"""

import json
import logging
from datetime import datetime
from pathlib import Path

RAW_DIR = Path("data/raw")
PUBLIC_DIR = Path("docs")
OUTPUT_DIR = PUBLIC_DIR / "deputados"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def arquivo_detalhes_mais_recente() -> Path:
    arquivos = sorted(RAW_DIR.glob("deputados_detalhes_*.json"), reverse=True)
    if not arquivos:
        raise FileNotFoundError(
            "Nenhum arquivo de detalhes encontrado em data/raw/. "
            "Rode primeiro: python src/scraper/collect.py"
        )
    return arquivos[0]


def main() -> None:
    # Carrega detalhes (proposições, discursos, órgãos por deputado)
    detalhes_path = arquivo_detalhes_mais_recente()
    log.info("Lendo detalhes de %s", detalhes_path)
    with open(detalhes_path, encoding="utf-8") as f:
        detalhes_por_id: dict[str, dict] = json.load(f)

    # Carrega ranking para pegar score, rank e dados básicos
    ranking_path = PUBLIC_DIR / "ranking.json"
    log.info("Lendo ranking de %s", ranking_path)
    with open(ranking_path, encoding="utf-8") as f:
        ranking_data = json.load(f)

    deputados = ranking_data["deputados"]
    ano_atual = datetime.today().year

    # Mapa de rank por score desc
    rank_map: dict[int, int] = {}
    deputados_sorted = sorted(deputados, key=lambda d: d["score"], reverse=True)
    for i, d in enumerate(deputados_sorted, 1):
        rank_map[d["id"]] = i

    count = 0
    for dep in deputados:
        dep_id = dep["id"]
        dep_detalhes = detalhes_por_id.get(str(dep_id), {})

        # Formata proposições com URL da Câmara
        proposicoes = []
        for p in dep_detalhes.get("proposicoes", []):
            proposicoes.append({
                "id": p.get("id"),
                "tipo": p.get("siglaTipo", ""),
                "numero": p.get("numero"),
                "ano": p.get("ano"),
                "ementa": p.get("ementa", ""),
                "data": p.get("dataApresentacao", ""),
                "url": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p.get('id')}"
                if p.get("id") else "",
            })

        # Formata discursos
        discursos = [
            {
                "data": d.get("dataHoraInicio", ""),
                "fase": d.get("faseEvento", ""),
                "resumo": d.get("resumo", ""),
            }
            for d in dep_detalhes.get("discursos", [])
        ]

        # Formata órgãos
        orgaos = [
            {
                "nome": o.get("nomeOrgao", ""),
                "sigla": o.get("siglaOrgao", ""),
                "cargo": o.get("titulo", ""),
                "desde": o.get("dataInicio", ""),
            }
            for o in dep_detalhes.get("orgaos", [])
        ]

        resultado = {
            "id": dep_id,
            "nome": dep.get("nome_urna") or dep.get("nome", ""),
            "partido": dep.get("partido", ""),
            "uf": dep.get("uf", ""),
            "foto_url": dep.get("foto_url", ""),
            "score": dep.get("score", 0),
            "rank": rank_map.get(dep_id, 0),
            "proposicoes": proposicoes,
            "discursos": discursos,
            "orgaos": orgaos,
            "url_votacoes": f"https://www.camara.leg.br/deputados/{dep_id}/votacoes-nominais-plenario/{ano_atual}",
        }

        out_path = OUTPUT_DIR / f"{dep_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        count += 1

    log.info("Gerados %d arquivos em %s", count, OUTPUT_DIR)


if __name__ == "__main__":
    main()
