// ===========================
// Carrega e renderiza dados do deputado
// ===========================
document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id');

  if (!id) {
    mostrarErro('ID do deputado nao informado na URL.');
    return;
  }

  carregarDeputado(id);
});

async function carregarDeputado(id) {
  try {
    const res = await fetch(`deputados/${id}.json`);
    if (!res.ok) throw new Error('Dados nao encontrados');
    const dep = await res.json();
    renderizar(dep);
  } catch (e) {
    mostrarErro('Nao foi possivel carregar os dados deste deputado. Verifique se o ID esta correto.');
  }
}

function mostrarErro(msg) {
  document.getElementById('loading').style.display = 'none';
  const erro = document.getElementById('erro');
  erro.textContent = msg;
  erro.style.display = 'block';
}

function renderizar(dep) {
  document.getElementById('loading').style.display = 'none';
  document.getElementById('conteudo').style.display = 'block';

  // Titulo da pagina
  document.title = `${dep.nome} — Ranking Camara`;

  // Perfil
  const foto = document.getElementById('perfil-foto');
  foto.src = dep.foto_url || 'placeholder.svg';
  foto.alt = dep.nome;
  foto.onerror = function () { this.src = 'placeholder.svg'; };

  document.getElementById('perfil-nome').textContent = dep.nome;
  document.getElementById('perfil-partido').textContent = dep.partido;
  document.getElementById('perfil-uf').textContent = dep.uf;
  document.getElementById('perfil-rank').textContent = `#${dep.rank}`;

  const score = dep.score;
  document.getElementById('perfil-score').textContent = score.toFixed(1);
  document.getElementById('perfil-score-barra').style.width = `${score}%`;

  const classeScore = score >= 70 ? 'score-alto' : score >= 40 ? 'score-medio' : 'score-baixo';
  document.getElementById('perfil-score-wrapper').classList.add(classeScore);

  // Proposicoes
  const props = dep.proposicoes || [];
  document.getElementById('contagem-proposicoes').textContent = `${props.length} proposicao(oes) nos ultimos 30 dias`;
  const tbodyProps = document.getElementById('tbody-proposicoes');
  if (props.length === 0) {
    tbodyProps.innerHTML = '<tr><td colspan="4" class="sem-resultados">Nenhuma proposicao no periodo.</td></tr>';
  } else {
    tbodyProps.innerHTML = props.map(p => `
      <tr>
        <td><span class="badge-partido">${esc(p.tipo)}</span></td>
        <td>${p.url ? `<a href="${esc(p.url)}" target="_blank" rel="noopener">${p.numero}/${p.ano}</a>` : `${p.numero}/${p.ano}`}</td>
        <td>${formatarData(p.data)}</td>
        <td class="col-ementa">${esc(p.ementa)}</td>
      </tr>
    `).join('');
  }

  // Discursos
  const discs = dep.discursos || [];
  document.getElementById('contagem-discursos').textContent = `${discs.length} discurso(s) nos ultimos 30 dias`;
  const tbodyDiscs = document.getElementById('tbody-discursos');
  if (discs.length === 0) {
    tbodyDiscs.innerHTML = '<tr><td colspan="3" class="sem-resultados">Nenhum discurso no periodo.</td></tr>';
  } else {
    tbodyDiscs.innerHTML = discs.map(d => `
      <tr>
        <td class="nowrap">${formatarDataHora(d.data)}</td>
        <td>${esc(d.fase)}</td>
        <td class="col-resumo">${esc(d.resumo)}</td>
      </tr>
    `).join('');
  }

  // Orgaos
  const orgaos = dep.orgaos || [];
  document.getElementById('contagem-orgaos').textContent = `${orgaos.length} orgao(s) ativo(s)`;
  const tbodyOrgaos = document.getElementById('tbody-orgaos');
  if (orgaos.length === 0) {
    tbodyOrgaos.innerHTML = '<tr><td colspan="4" class="sem-resultados">Nenhum orgao ativo.</td></tr>';
  } else {
    tbodyOrgaos.innerHTML = orgaos.map(o => `
      <tr>
        <td>${esc(o.nome)}</td>
        <td>${esc(o.sigla)}</td>
        <td>${esc(o.cargo)}</td>
        <td>${formatarData(o.desde)}</td>
      </tr>
    `).join('');
  }

  // Votacoes
  document.getElementById('link-votacoes').href = dep.url_votacoes;
}

// ===========================
// Utilitarios
// ===========================
function esc(str) {
  if (!str) return '';
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

function formatarData(iso) {
  if (!iso) return '';
  const d = new Date(iso + 'T00:00:00');
  if (isNaN(d)) return iso;
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatarDataHora(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
    ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}
