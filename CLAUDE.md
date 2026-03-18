# CLAUDE.md — Ranking Câmara

## Visão Geral do Projeto

Site público que rankeia deputados federais brasileiros por produtividade, com atualização diária automática usando dados abertos da Câmara dos Deputados.

API pública usada: `https://dadosabertos.camara.leg.br/api/v2`
Documentação Swagger: `https://dadosabertos.camara.leg.br/swagger/api.html`

---

## Arquitetura

```
ranking-camara/
├── data/            # Scripts de coleta e processamento de dados
├── public/          # Site estático gerado (HTML/CSS/JS)
├── src/             # Código-fonte principal
│   ├── scraper/     # Coleta dados da API da Câmara
│   ├── scoring/     # Cálculo do score de produtividade
│   └── site/        # Geração do site estático
└── .github/
    └── workflows/   # GitHub Actions para atualização diária
```

## Stack

- **Coleta de dados**: Python (requests, pandas)
- **Geração do site**: Site estático (HTML/CSS/JS puro, sem framework pesado)
- **Atualização**: GitHub Actions (cron diário)
- **Hospedagem**: GitHub Pages

Preferir soluções simples e sem dependências desnecessárias. O site deve funcionar sem backend — tudo pré-computado e servido como JSON estático.

---

## Score de Produtividade

O score de cada deputado é calculado com base nas seguintes métricas (pesos ajustáveis):

| Métrica | Endpoint da API | Peso |
|---|---|---|
| Proposições apresentadas | `/proposicoes` | 30% |
| Presença em votações | `/votacoes` | 25% |
| Discursos no plenário | `/deputados/{id}/discursos` | 15% |
| Comissões participadas | `/deputados/{id}/orgaos` | 15% |
| Requerimentos | `/proposicoes?siglaTipo=REQ` | 15% |

O score final é normalizado de 0 a 100 dentro da legislatura atual.

---

## Endpoints Principais da API da Câmara

```
GET /deputados                          # Lista todos os deputados ativos
GET /deputados/{id}                     # Detalhes de um deputado
GET /deputados/{id}/discursos           # Discursos do deputado
GET /deputados/{id}/votacoes            # Votações do deputado
GET /deputados/{id}/orgaos              # Comissões do deputado
GET /proposicoes?autor={id}             # Proposições por autor
GET /votacoes                           # Votações em plenário
```

Sempre usar `?formato=json` e respeitar paginação (`?pagina=1&itens=100`).
A API não requer autenticação.

---

## Convenções de Código

- Python: seguir PEP8, usar type hints
- Nomes de variáveis e funções: inglês
- Comentários e mensagens de commit: português
- Cada script de coleta deve ser idempotente (pode rodar várias vezes sem efeito colateral)
- Salvar dados brutos em `data/raw/` antes de processar
- Dados processados em `data/processed/`

---

## Fluxo de Atualização Diária

1. GitHub Actions dispara o workflow às 03:00 BRT
2. `scraper/` coleta dados dos últimos 30 dias via API
3. `scoring/` recalcula o score de todos os deputados
4. `site/` regenera os arquivos JSON e HTML estáticos
5. Commit automático e push para `gh-pages`

---

## Tarefas Comuns

**Rodar coleta manualmente:**
```bash
python src/scraper/collect.py
```

**Recalcular scores:**
```bash
python src/scoring/score.py
```

**Gerar site localmente:**
```bash
python src/site/build.py
# Abrir public/index.html no browser
```

**Instalar dependências:**
```bash
pip install -r requirements.txt
```

---

## Notas Importantes

- A API da Câmara tem rate limit — usar `time.sleep(0.5)` entre requisições
- A legislatura atual é a 57ª (2023–2027)
- Dados de afastados e licenciados devem ser excluídos do ranking
- O ranking deve exibir partido, UF e foto do deputado (foto disponível em `/deputados/{id}`)
- Preservar histórico de scores em `data/history/YYYY-MM-DD.json` para gráficos de evolução
