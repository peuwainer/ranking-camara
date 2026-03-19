"""
Calcula o score de produtividade de cada deputado e gera:
  - docs/ranking.json          (consumido pelo site)
  - data/processed/ranking_YYYY-MM-DD.json
  - data/history/YYYY-MM-DD.json

Uso: python src/scoring/score.py

Espera encontrar o arquivo mais recente em data/raw/.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

# ===========================
# Configuração
# ===========================
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
HISTORY_DIR = Path("data/history")
PUBLIC_DIR = Path("docs")

for d in (PROCESSED_DIR, HISTORY_DIR, PUBLIC_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Pesos do score (devem somar 1.0)
PESOS: dict[str, float] = {
    "proposicoes": 0.35,
    "presenca":    0.30,
    "discursos":   0.20,
    "orgaos":      0.15,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ===========================
# Utilitários
# ===========================
def arquivo_raw_mais_recente() -> Path:
    arquivos = sorted(RAW_DIR.glob("deputados_*.json"), reverse=True)
    if not arquivos:
        raise FileNotFoundError(
            "Nenhum arquivo encontrado em data/raw/. "
            "Rode primeiro: python src/scraper/collect.py"
        )
    return arquivos[0]


def normalizar(valores: list[float]) -> list[float]:
    """Normaliza uma lista para o intervalo [0, 100]."""
    minv, maxv = min(valores), max(valores)
    if maxv == minv:
        return [50.0] * len(valores)  # todos iguais → score 50
    return [(v - minv) / (maxv - minv) * 100 for v in valores]


# ===========================
# Cálculo
# ===========================
def calcular_scores(deputados: list[dict]) -> list[dict]:
    """
    Para cada métrica, normaliza os valores brutos de 0 a 100.
    O score final é a média ponderada das métricas normalizadas.
    """
    n = len(deputados)
    if n == 0:
        return []

    # Extrai vetores por métrica
    metricas = {
        "proposicoes": [d["proposicoes"] for d in deputados],
        "presenca":    [d["presenca_votacoes"] for d in deputados],
        "discursos":   [d["discursos"] for d in deputados],
        "orgaos":      [d["orgaos"] for d in deputados],
    }

    # Normaliza cada métrica
    normalizadas = {k: normalizar(v) for k, v in metricas.items()}

    # Score ponderado
    resultados = []
    for i, dep in enumerate(deputados):
        score = sum(
            normalizadas[k][i] * peso
            for k, peso in PESOS.items()
        )
        resultados.append({
            **dep,
            "score": round(score, 2),
        })

    # Ordena por score decrescente
    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados


# ===========================
# Formatação para o site
# ===========================
def formatar_para_site(deputados: list[dict], atualizado_em: str) -> dict:
    """Gera o JSON consumido pelo docs/app.js."""
    campos_site = [
        "id", "nome", "nome_urna", "partido", "uf", "foto_url",
        "score", "proposicoes", "presenca_votacoes", "discursos", "orgaos",
    ]
    return {
        "atualizado_em": atualizado_em,
        "legislatura": 57,
        "deputados": [
            {k: d[k] for k in campos_site if k in d}
            for d in deputados
        ],
    }


# ===========================
# Main
# ===========================
def main() -> None:
    raw_path = arquivo_raw_mais_recente()
    log.info("Lendo dados brutos de %s", raw_path)

    with open(raw_path, encoding="utf-8") as f:
        deputados = json.load(f)

    log.info("%d deputados carregados", len(deputados))

    com_scores = calcular_scores(deputados)

    hoje = datetime.today().strftime("%Y-%m-%d")
    atualizado_em = datetime.now().astimezone().isoformat()

    # Salva dados processados completos
    processed_path = PROCESSED_DIR / f"ranking_{hoje}.json"
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(com_scores, f, ensure_ascii=False, indent=2)
    log.info("Dados processados salvos em %s", processed_path)

    # Salva histórico (apenas id, nome, score — para gráficos futuros)
    historico = [{"id": d["id"], "nome": d["nome_urna"] or d["nome"], "score": d["score"]}
                 for d in com_scores]
    history_path = HISTORY_DIR / f"{hoje}.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump({"data": hoje, "scores": historico}, f, ensure_ascii=False, indent=2)
    log.info("Histórico salvo em %s", history_path)

    # Gera ranking.json para o site
    site_data = formatar_para_site(com_scores, atualizado_em)
    site_path = PUBLIC_DIR / "ranking.json"
    with open(site_path, "w", encoding="utf-8") as f:
        json.dump(site_data, f, ensure_ascii=False, indent=2)
    log.info("Site atualizado: %s (%d deputados)", site_path, len(com_scores))

    # Resumo no terminal
    top5 = com_scores[:5]
    log.info("Top 5:")
    for i, d in enumerate(top5, 1):
        nome = d.get("nome_urna") or d["nome"]
        log.info("  %d. %s (%s-%s) — %.1f", i, nome, d["partido"], d["uf"], d["score"])


if __name__ == "__main__":
    main()
