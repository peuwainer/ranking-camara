// ===========================
// Estado da aplicação
// ===========================
let dadosOriginais = [];
let ordenacao = { col: 'score', dir: 'desc' };
let paginaAtual = 1;
const ITENS_POR_PAGINA = 30;

// ===========================
// Inicialização
// ===========================
document.addEventListener('DOMContentLoaded', () => {
  carregarDados();

  document.getElementById('busca').addEventListener('input', () => { paginaAtual = 1; renderTabela(); });
  document.getElementById('filtro-partido').addEventListener('change', () => { paginaAtual = 1; renderTabela(); });
  document.getElementById('filtro-uf').addEventListener('change', () => { paginaAtual = 1; renderTabela(); });
  document.getElementById('btn-limpar').addEventListener('click', limparFiltros);

  document.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => ordenarPor(th.dataset.col));
  });
});

// ===========================
// Carrega ranking.json
// ===========================
async function carregarDados() {
  try {
    const res = await fetch('ranking.json');
    if (!res.ok) throw new Error('Arquivo não encontrado');
    const json = await res.json();

    dadosOriginais = json.deputados;
    document.getElementById('ultima-atualizacao').textContent = formatarData(json.atualizado_em);

    preencherFiltros();
    renderCards();
    renderTabela();
  } catch (e) {
    document.getElementById('tbody').innerHTML =
      '<tr><td colspan="10" class="sem-resultados">Não foi possível carregar os dados. Rode o script de coleta primeiro.</td></tr>';
  }
}

// ===========================
// Preenche selects de filtro
// ===========================
function preencherFiltros() {
  const partidos = [...new Set(dadosOriginais.map(d => d.partido))].sort();
  const ufs = [...new Set(dadosOriginais.map(d => d.uf))].sort();

  const selPartido = document.getElementById('filtro-partido');
  partidos.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p; opt.textContent = p;
    selPartido.appendChild(opt);
  });

  const selUF = document.getElementById('filtro-uf');
  ufs.forEach(u => {
    const opt = document.createElement('option');
    opt.value = u; opt.textContent = u;
    selUF.appendChild(opt);
  });
}

// ===========================
// Cards de resumo
// ===========================
function renderCards() {
  document.getElementById('total-deputados').textContent = dadosOriginais.length;
  document.getElementById('total-partidos').textContent =
    new Set(dadosOriginais.map(d => d.partido)).size;
  document.getElementById('total-ufs').textContent =
    new Set(dadosOriginais.map(d => d.uf)).size;
}

// ===========================
// Filtragem e ordenação
// ===========================
function dadosFiltrados() {
  const busca = document.getElementById('busca').value.toLowerCase().trim();
  const partido = document.getElementById('filtro-partido').value;
  const uf = document.getElementById('filtro-uf').value;

  return dadosOriginais.filter(d => {
    if (busca && !d.nome.toLowerCase().includes(busca)) return false;
    if (partido && d.partido !== partido) return false;
    if (uf && d.uf !== uf) return false;
    return true;
  });
}

function ordenarDados(lista) {
  const { col, dir } = ordenacao;
  return [...lista].sort((a, b) => {
    let va = a[col], vb = b[col];
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    if (va < vb) return dir === 'asc' ? -1 : 1;
    if (va > vb) return dir === 'asc' ? 1 : -1;
    return 0;
  });
}

function ordenarPor(col) {
  if (ordenacao.col === col) {
    ordenacao.dir = ordenacao.dir === 'asc' ? 'desc' : 'asc';
  } else {
    ordenacao.col = col;
    ordenacao.dir = col === 'score' ? 'desc' : 'asc';
  }
  atualizarIconesOrdenacao();
  paginaAtual = 1;
  renderTabela();
}

function atualizarIconesOrdenacao() {
  document.querySelectorAll('th.sortable').forEach(th => {
    th.classList.remove('active', 'asc', 'desc');
    th.querySelector('.sort-icon').textContent = '↕';
    if (th.dataset.col === ordenacao.col) {
      th.classList.add('active', ordenacao.dir);
      th.querySelector('.sort-icon').textContent = ordenacao.dir === 'asc' ? '↑' : '↓';
    }
  });
}

function limparFiltros() {
  document.getElementById('busca').value = '';
  document.getElementById('filtro-partido').value = '';
  document.getElementById('filtro-uf').value = '';
  paginaAtual = 1;
  renderTabela();
}

// ===========================
// Renderiza a tabela
// ===========================
function renderTabela() {
  const listaCompleta = ordenarDados(dadosFiltrados());
  const tbody = document.getElementById('tbody');
  const contagem = document.getElementById('contagem-resultados');

  if (listaCompleta.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="sem-resultados">Nenhum deputado encontrado com esses filtros.</td></tr>';
    contagem.textContent = '';
    document.getElementById('paginacao').innerHTML = '';
    return;
  }

  // Mapa de id → posição global (sempre por score desc, independente da ordenação atual)
  const rankGlobal = new Map();
  [...dadosOriginais].sort((a, b) => b.score - a.score).forEach((d, i) => rankGlobal.set(d.id, i + 1));

  const total = listaCompleta.length;
  const inicio = (paginaAtual - 1) * ITENS_POR_PAGINA;
  const fim = Math.min(inicio + ITENS_POR_PAGINA, total);
  const lista = listaCompleta.slice(inicio, fim);

  contagem.textContent = `Exibindo ${inicio + 1}–${fim} de ${total} deputados`;

  tbody.innerHTML = lista.map((d) => {
    const pos = rankGlobal.get(d.id) ?? '—';
    const usarMedalha = ordenacao.col === 'score' && ordenacao.dir === 'desc';
    const classePos = usarMedalha && pos <= 3 ? 'posicao top3' : 'posicao';
    const medalha = usarMedalha
      ? (pos === 1 ? '🥇' : pos === 2 ? '🥈' : pos === 3 ? '🥉' : pos)
      : pos;
    const classeScore = d.score >= 70 ? 'score-alto' : d.score >= 40 ? 'score-medio' : 'score-baixo';

    const foto = d.foto_url
      ? `<img class="foto-deputado" src="${d.foto_url}" alt="${d.nome}" loading="lazy" onerror="this.src='placeholder.svg'">`
      : `<img class="foto-deputado" src="placeholder.svg" alt="${d.nome}">`;

    return `
      <tr>
        <td class="${classePos}">${medalha}</td>
        <td>${foto}</td>
        <td class="col-nome">${d.nome}</td>
        <td><span class="badge-partido">${d.partido}</span></td>
        <td>${d.uf}</td>
        <td>
          <div class="score-wrapper ${classeScore}">
            <span class="score-valor">${d.score.toFixed(1)}</span>
            <div class="score-barra-bg">
              <div class="score-barra" style="width:${d.score}%"></div>
            </div>
          </div>
        </td>
        <td class="num"><a href="https://www.camara.leg.br/busca-portal?contextoBusca=BuscaProposicoes&pagina=1&order=data&abaEspecifica=true&q=autores.ideCadastro%3A%20${d.id}%20AND%20dataApresentacao%3A%5B${new Date().getFullYear()}-01-01%20TO%20${new Date().getFullYear()}-12-31%5D" target="_blank" rel="noopener">${d.proposicoes}</a></td>
        <td class="num">${d.presenca_votacoes}%</td>
        <td class="num">${d.discursos}</td>
        <td class="num">${d.orgaos}</td>
      </tr>`;
  }).join('');

  renderPaginacao(total);
}

// ===========================
// Renderiza paginação
// ===========================
function renderPaginacao(total) {
  const totalPaginas = Math.ceil(total / ITENS_POR_PAGINA);
  const el = document.getElementById('paginacao');

  if (totalPaginas <= 1) {
    el.innerHTML = '';
    return;
  }

  const tabela = document.getElementById('tabela-ranking');

  function irPara(n) {
    paginaAtual = n;
    renderTabela();
    window.scrollTo({ top: tabela.offsetTop - 20, behavior: 'smooth' });
  }

  const botoes = [];

  // Anterior
  botoes.push(`<button ${paginaAtual === 1 ? 'disabled' : ''} data-pag="${paginaAtual - 1}">← Anterior</button>`);

  // Números de página
  const delta = 2;
  const paginas = new Set();
  paginas.add(1);
  paginas.add(totalPaginas);
  for (let p = paginaAtual - delta; p <= paginaAtual + delta; p++) {
    if (p >= 1 && p <= totalPaginas) paginas.add(p);
  }

  let prev = 0;
  [...paginas].sort((a, b) => a - b).forEach(p => {
    if (prev && p - prev > 1) {
      botoes.push(`<span class="reticencias">…</span>`);
    }
    botoes.push(`<button class="pagina-btn${p === paginaAtual ? ' ativa' : ''}" data-pag="${p}">${p}</button>`);
    prev = p;
  });

  // Próxima
  botoes.push(`<button ${paginaAtual === totalPaginas ? 'disabled' : ''} data-pag="${paginaAtual + 1}">Próxima →</button>`);

  el.innerHTML = botoes.join('');

  el.querySelectorAll('button[data-pag]').forEach(btn => {
    btn.addEventListener('click', () => irPara(Number(btn.dataset.pag)));
  });
}

// ===========================
// Tooltips
// ===========================
(function () {
  const tip = document.getElementById('tooltip');

  document.querySelectorAll('th[data-tooltip]').forEach(th => {
    th.addEventListener('mouseenter', () => {
      const rect = th.getBoundingClientRect();
      tip.textContent = th.dataset.tooltip;
      tip.style.opacity = '1';
      // posiciona acima do th, centralizado
      const tipWidth = 220;
      let left = rect.left + rect.width / 2 - tipWidth / 2;
      left = Math.max(8, Math.min(left, window.innerWidth - tipWidth - 8));
      tip.style.left = left + 'px';
      tip.style.top = (rect.top - tip.offsetHeight - 8) + 'px';
    });

    th.addEventListener('mouseleave', () => {
      tip.style.opacity = '0';
    });
  });
})();

// ===========================
// Utilitários
// ===========================
function formatarData(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}
