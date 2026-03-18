# Ranking dos Deputados Federais

Site público que rankeia os 513 deputados federais brasileiros por produtividade, atualizado automaticamente todo dia com dados abertos da Câmara dos Deputados.

## Como funciona

O score de produtividade de cada deputado é calculado diariamente a partir de dados coletados via API pública da Câmara (`dadosabertos.camara.leg.br`). Nenhum dado é inserido manualmente — tudo vem de fontes oficiais.

### Métricas utilizadas

| Métrica | Peso |
|---|---|
| Proposições apresentadas | 30% |
| Presença em votações | 25% |
| Discursos no plenário | 15% |
| Participação em comissões | 15% |
| Requerimentos | 15% |

O score final é normalizado de 0 a 100 dentro da legislatura atual (57ª, 2023–2027).

## Fonte dos dados

Todos os dados vêm da API oficial da Câmara dos Deputados:

- **API**: https://dadosabertos.camara.leg.br/api/v2
- **Documentação**: https://dadosabertos.camara.leg.br/swagger/api.html
- **Licença dos dados**: Dados abertos sob a [Lei de Acesso à Informação](https://www.camara.leg.br/transparencia/)

Nenhuma raspagem de tela (scraping) é utilizada — apenas a API REST oficial.

## Rodando localmente

**Pré-requisitos:** Python 3.10+

```bash
# Clone o repositório
git clone https://github.com/peuwainer/ranking-camara.git
cd ranking-camara

# Instale as dependências
pip install -r requirements.txt

# Colete os dados
python src/scraper/collect.py

# Calcule os scores
python src/scoring/score.py

# Gere o site
python src/site/build.py

# Abra public/index.html no seu browser
```

## Atualização automática

O ranking é recalculado todo dia às 03:00 (horário de Brasília) via GitHub Actions. O processo completo demora cerca de 10 minutos.

## Estrutura do projeto

```
ranking-camara/
├── src/
│   ├── scraper/     # Coleta dados da API da Câmara
│   ├── scoring/     # Calcula o score de produtividade
│   └── site/        # Gera o site estático
├── data/
│   ├── raw/         # Dados brutos da API
│   ├── processed/   # Dados processados
│   └── history/     # Histórico diário de scores
├── public/          # Site gerado (servido via GitHub Pages)
└── .github/
    └── workflows/   # Pipeline de atualização diária
```

## Contribuindo

Contribuições são bem-vindas, especialmente para:

- Novos critérios de produtividade
- Melhorias no visual do site
- Correções de bugs na coleta de dados

Abra uma issue antes de enviar um PR para alinhar a abordagem.

## Limitações

- O score mede **atividade legislativa registrada**, não qualidade das proposições
- Deputados em licença ou afastamento são excluídos do ranking enquanto inativos
- A API da Câmara pode ter instabilidades pontuais; nesses casos o ranking mantém os dados do dia anterior

## Licença

MIT — veja [LICENSE](LICENSE) para detalhes.
