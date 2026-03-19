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
MAX_RETRIES = 3

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


def _get_com_retry(url: str, params: dict, timeout: int = 30) -> requests.Response:
    """GET com retry exponencial para erros transitórios (5xx, timeout, connection error)."""
    ultimo_erro: Exception | None = None
    for tentativa in range(MAX_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=timeout)
            if resp.status_code >= 500:
                raise requests.HTTPError(response=resp)
            resp.raise_for_status()
            return resp
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            ultimo_erro = e
            espera = 2 ** tentativa
            log.warning(
                "Tentativa %d/%d falhou em %s (%s). Aguardando %ds...",
                tentativa + 1, MAX_RETRIES, url, e, espera,
            )
            if tentativa < MAX_RETRIES - 1:
                time.sleep(espera)
    raise ultimo_erro  # type: ignore[misc]


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
            resp = _get_com_retry(url, params)
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
        resp = _get_com_retry(url, params)
        return resp.json().get("dados", {})
    except requests.RequestException as e:
        log.error("Erro em GET %s: %s", endpoint, e)
        return {}


# ===========================
# Coleta
# ===========================
def coletar_deputados() -> list[dict]:
    """Lista todos os deputados atualmente em exercício."""
    log.info("Coletando lista de deputados...")
    deputados = get("/deputados")
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



def coletar_discursos(deputado_id: int, data_inicio: str) -> int:
    """Conta discursos no plenário."""
    dados = get(f"/deputados/{deputado_id}/discursos", {
        "dataInicio": data_inicio,
        "ordenarPor": "dataHoraInicio",
    })
    return len(dados)


def coletar_presencas_votacoes(data_inicio: str) -> tuple[int, dict[int, int]]:
    """Retorna (total_votacoes, {deputado_id: num_presencas}) usando bulk files anuais.

    Estratégia: baixa votacoesVotos-{ano}.json (um arquivo por ano necessário),
    filtra por data localmente. Zero requisições extras por deputado.
    """
    TIPOS_PRESENCA = {"Sim", "Não", "Abstenção", "Obstrução", "Artigo 17"}
    BULK_BASE = "https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/json"

    ano_inicio = int(data_inicio[:4])
    ano_atual = datetime.today().year
    anos = list(range(ano_inicio, ano_atual + 1))

    todos_votos: list[dict] = []
    for ano in anos:
        url = f"{BULK_BASE}/votacoesVotos-{ano}.json"
        log.info("Baixando bulk file de votos: %s", url)
        try:
            resp = session.get(url, timeout=60)
            resp.raise_for_status()
            dados = resp.json().get("dados", [])
            log.info("  %d registros carregados (%d)", len(dados), ano)
            todos_votos.extend(dados)
        except requests.RequestException as e:
            log.error("Erro ao baixar bulk file %s: %s", url, e)

    # Filtra pela data de início
    votos_periodo = [
        v for v in todos_votos
        if v.get("dataHoraVoto", "") >= data_inicio
    ]
    log.info("  %d votos no período desde %s", len(votos_periodo), data_inicio)

    ids_votacao: set[str] = set()
    presencas: dict[int, int] = {}

    for voto in votos_periodo:
        tipo = voto.get("voto", "")
        if tipo not in TIPOS_PRESENCA:
            continue
        vid = voto.get("idVotacao")
        if vid:
            ids_votacao.add(vid)
        dep = voto.get("deputado_", {})
        dep_id = dep.get("id")
        if dep_id:
            dep_id = int(dep_id)
            presencas[dep_id] = presencas.get(dep_id, 0) + 1

    total_votacoes = len(ids_votacao)
    log.info("  %d votações distintas, %d deputados com presença", total_votacoes, len(presencas))
    return total_votacoes, presencas


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

    deputados_ativos = deputados_base
    log.info("%d deputados para processar", len(deputados_ativos))

    # Coleta votações uma vez para todos os deputados
    total_votacoes, presencas_por_deputado = coletar_presencas_votacoes(data_inicio)

    resultados = []
    progresso_inicio(len(deputados_ativos))

    for i, dep in enumerate(deputados_ativos, 1):
        dep_id = dep["id"]
        nome_curto = dep.get("nome", str(dep_id))

        progresso(i, nome_curto, "detalhes...    ")
        detalhes = coletar_detalhes(dep_id)

        # Pula se situação não é exercício ativo do mandato
        if detalhes.get("situacao", "").upper() != "EXERCÍCIO":
            progresso_fim()
            log.info("Pulando %s — situação: %s", nome_curto, detalhes["situacao"])
            progresso_inicio(len(deputados_ativos) - i)
            continue

        progresso(i, nome_curto, "proposições... ")
        proposicoes = coletar_proposicoes(dep_id, data_inicio)

        progresso(i, nome_curto, "discursos...   ")
        discursos = coletar_discursos(dep_id, data_inicio)

        progresso(i, nome_curto, "comissões...   ")
        orgaos = coletar_orgaos(dep_id)

        presencas = presencas_por_deputado.get(dep_id, 0)
        presenca_pct = round(presencas / total_votacoes * 100, 1) if total_votacoes > 0 else 0.0

        resultados.append({
            **detalhes,
            "proposicoes": proposicoes,
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
