"""
Coleta dados dos deputados federais via API da Câmara dos Deputados.
Salva dados brutos em data/raw/.

Uso: python src/scraper/collect.py
"""

import json
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests

# ===========================
# Configuração
# ===========================
BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

LEGISLATURA_ATUAL = 57
DIAS_RETROATIVOS = 30
SLEEP_ENTRE_REQUESTS = 0.5  # segundos — respeita rate limit da API

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ===========================
# Progresso
# ===========================
_inicio: float = 0.0
_total: int = 0


def progresso_inicio(total: int) -> None:
    global _inicio, _total
    _inicio = time.monotonic()
    _total = total


def progresso(atual: int, nome: str, etapa: str) -> None:
    """Imprime barra de progresso com ETA na mesma linha."""
    pct = atual / _total
    largura = 30
    preenchido = int(largura * pct)
    barra = "=" * preenchido + ">" + " " * (largura - preenchido)

    elapsed = time.monotonic() - _inicio
    if atual > 0:
        eta_seg = elapsed / atual * (_total - atual)
        eta = f"{int(eta_seg // 60):02d}:{int(eta_seg % 60):02d}"
    else:
        eta = "--:--"

    linha = (
        f"\r[{barra}] {atual:>{len(str(_total))}}/{_total} "
        f"({pct:.0%}) | ETA {eta} | {nome[:28]:<28} | {etapa}"
    )
    sys.stdout.write(linha)
    sys.stdout.flush()


def progresso_fim() -> None:
    elapsed = time.monotonic() - _inicio
    sys.stdout.write(f"\r{'':100}\r")  # limpa a linha
    sys.stdout.flush()
    log.info("Concluído em %dm%02ds", int(elapsed // 60), int(elapsed % 60))

# ===========================
# HTTP
# ===========================
session = requests.Session()
session.headers.update({"Accept": "application/json"})


def get(endpoint: str, params: dict | None = None, paginado: bool = True) -> list | dict:
    """GET paginado: coleta todas as páginas automaticamente.
    Use paginado=False para endpoints que não aceitam itens/pagina."""
    params = params or {}
    if paginado:
        params["itens"] = 100
    resultados = []
    pagina = 1

    while True:
        if paginado:
            params["pagina"] = pagina
        url = f"{BASE_URL}{endpoint}"

        try:
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            log.error("Erro em GET %s: %s", endpoint, e)
            break

        dados = data.get("dados", [])
        if not dados:
            break

        resultados.extend(dados)

        # Verifica se há próxima página pelos links
        links = data.get("links", [])
        tem_proxima = any(lk.get("rel") == "next" for lk in links)
        if not tem_proxima or not paginado:
            break

        pagina += 1
        time.sleep(SLEEP_ENTRE_REQUESTS)

    time.sleep(SLEEP_ENTRE_REQUESTS)
    return resultados


def get_unico(endpoint: str, params: dict | None = None) -> dict:
    """GET simples para endpoints que retornam um único objeto."""
    params = params or {}
    params["formato"] = "json"
    url = f"{BASE_URL}{endpoint}"

    try:
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("dados", {})
    except requests.RequestException as e:
        log.error("Erro em GET %s: %s", endpoint, e)
        return {}


# ===========================
# Coleta
# ===========================
def coletar_deputados() -> list[dict]:
    """Lista todos os deputados ativos na legislatura atual."""
    log.info("Coletando lista de deputados...")
    deputados = get("/deputados", {"idLegislatura": LEGISLATURA_ATUAL})
    log.info("  %d deputados encontrados", len(deputados))
    return deputados


def coletar_detalhes(deputado_id: int) -> dict:
    """Detalhes completos de um deputado (inclui URL da foto)."""
    dados = get_unico(f"/deputados/{deputado_id}")
    return {
        "id": deputado_id,
        "nome": dados.get("nomeCivil", ""),
        "nome_urna": dados.get("ultimoStatus", {}).get("nomeEleitoral", ""),
        "partido": dados.get("ultimoStatus", {}).get("siglaPartido", ""),
        "uf": dados.get("ultimoStatus", {}).get("siglaUf", ""),
        "situacao": dados.get("ultimoStatus", {}).get("situacao", ""),
        "foto_url": dados.get("ultimoStatus", {}).get("urlFoto", ""),
    }


def coletar_proposicoes(deputado_id: int, data_inicio: str) -> int:
    """Conta proposições apresentadas pelo deputado desde data_inicio."""
    dados = get("/proposicoes", {
        "idDeputadoAutor": deputado_id,
        "dataInicio": data_inicio,
    })
    return len(dados)


def coletar_requerimentos(deputado_id: int, data_inicio: str) -> int:
    """Conta requerimentos (tipo REQ) apresentados pelo deputado."""
    dados = get("/proposicoes", {
        "idDeputadoAutor": deputado_id,
        "siglaTipo": "REQ",
        "dataInicio": data_inicio,
    })
    return len(dados)


def coletar_discursos(deputado_id: int, data_inicio: str) -> int:
    """Conta discursos no plenário."""
    dados = get(f"/deputados/{deputado_id}/discursos", {
        "dataInicio": data_inicio,
        "ordenarPor": "dataHoraInicio",
    })
    return len(dados)


def coletar_votacoes(deputado_id: int, data_inicio: str) -> tuple[int, int]:
    """Retorna (total_votacoes, presencas) sem usar itens/pagina."""
    dados = get(f"/deputados/{deputado_id}/votacoes", {
        "dataInicio": data_inicio,
    }, paginado=False)
    total = len(dados)
    tipos_presenca = {"Sim", "Não", "Abstenção", "Obstrução", "Artigo 17"}
    presencas = sum(1 for v in dados if v.get("tipoVoto") in tipos_presenca)
    return total, presencas


def coletar_orgaos(deputado_id: int) -> int:
    """Conta comissões em que o deputado participa atualmente."""
    dados = get(f"/deputados/{deputado_id}/orgaos")
    # filtra apenas comissões ativas (sem dataFim ou dataFim futura)
    hoje = datetime.today().date()
    ativos = [
        o for o in dados
        if not o.get("dataFim") or datetime.fromisoformat(o["dataFim"]).date() >= hoje
    ]
    return len(ativos)



# ===========================
# Loop principal
# ===========================
def main() -> None:
    data_inicio = (datetime.today() - timedelta(days=DIAS_RETROATIVOS)).strftime("%Y-%m-%d")
    log.info("Coletando dados desde %s", data_inicio)

    deputados_base = coletar_deputados()

    # Filtra afastados/licenciados
    deputados_ativos = [
        d for d in deputados_base
        if d.get("situacao", "").upper() not in {"AFASTADO", "LICENCIADO", "FALECIDO"}
    ]
    log.info("%d deputados ativos para processar", len(deputados_ativos))

    resultados = []
    progresso_inicio(len(deputados_ativos))

    for i, dep in enumerate(deputados_ativos, 1):
        dep_id = dep["id"]
        nome_curto = dep.get("nome", str(dep_id))

        progresso(i, nome_curto, "detalhes...    ")
        detalhes = coletar_detalhes(dep_id)

        # Pula se situação indica afastamento nos detalhes completos
        if detalhes.get("situacao", "").upper() in {"AFASTADO", "LICENCIADO", "FALECIDO"}:
            progresso_fim()
            log.info("Pulando %s — situação: %s", nome_curto, detalhes["situacao"])
            progresso_inicio(len(deputados_ativos) - i)
            continue

        progresso(i, nome_curto, "proposições... ")
        proposicoes = coletar_proposicoes(dep_id, data_inicio)

        progresso(i, nome_curto, "requerimentos..")
        requerimentos = coletar_requerimentos(dep_id, data_inicio)

        progresso(i, nome_curto, "discursos...   ")
        discursos = coletar_discursos(dep_id, data_inicio)

        progresso(i, nome_curto, "comissões...   ")
        orgaos = coletar_orgaos(dep_id)

        progresso(i, nome_curto, "votações...    ")
        total_votacoes, presencas = coletar_votacoes(dep_id, data_inicio)

        presenca_pct = round(presencas / total_votacoes * 100, 1) if total_votacoes > 0 else 0.0

        resultados.append({
            **detalhes,
            "proposicoes": proposicoes,
            "requerimentos": requerimentos,
            "discursos": discursos,
            "orgaos": orgaos,
            "total_votacoes": total_votacoes,
            "presencas_votacoes": presencas,
            "presenca_votacoes": presenca_pct,
            "data_coleta": data_inicio,
        })

    progresso_fim()

    # Salva dados brutos
    saida = RAW_DIR / f"deputados_{datetime.today().strftime('%Y-%m-%d')}.json"
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    log.info("Dados brutos salvos em %s (%d deputados)", saida, len(resultados))


if __name__ == "__main__":
    main()
