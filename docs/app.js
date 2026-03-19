// ===========================
// Estado da aplicação
// ===========================
let dadosOriginais = [];
let ordenacao = { col: 'score', dir: 'desc' };

// ===========================
// Inicialização
// ===========================
document.addEventListener('DOMContentLoaded', () => {
  carregarDados();

  document.getElementById('busca').addEventListener('input', renderTabela);
  document.getElementById('filtro-partido').addEventListener('change', renderTabela);
  document.getElementById('filtro-uf').addEventListener('change', renderTabela);
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
  renderTabela();
}

// ===========================
// Renderiza a tabela
// ===========================
function renderTabela() {
  const lista = ordenarDados(dadosFiltrados());
  const tbody = document.getElementById('tbody');
  const contagem = document.getElementById('contagem-resultados');

  if (lista.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="sem-resultados">Nenhum deputado encontrado com esses filtros.</td></tr>';
    contagem.textContent = '';
    return;
  }

  contagem.textContent = `Exibindo ${lista.length} de ${dadosOriginais.length} deputados`;

  tbody.innerHTML = lista.map((d, i) => {
    const pos = i + 1;
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
        <td class="num">${d.proposicoes}</td>
        <td class="num">${d.presenca_votacoes}%</td>
        <td class="num">${d.discursos}</td>
        <td class="num">${d.orgaos}</td>
      </tr>`;
  }).join('');
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
