"""Smoke test para verificar coleta de presenças via /votacoes/{id}/votos."""
from datetime import datetime, timedelta
from collect import coletar_presencas_votacoes

data_inicio = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")
print(f"Testando desde {data_inicio}...\n")

total, presencas = coletar_presencas_votacoes(data_inicio)

print(f"\nTotal de votações com votos: {total}")
print(f"Deputados com ao menos 1 presença: {len(presencas)}")

# Top 10
top = sorted(presencas.items(), key=lambda x: x[1], reverse=True)[:10]
print("\nTop 10 por presença:")
for dep_id, count in top:
    pct = round(count / total * 100, 1) if total else 0
    print(f"  id={dep_id}  presenças={count}  ({pct}%)")

# Deputado de referência
dep_ref = 220593
print(f"\nDeputado {dep_ref}: {presencas.get(dep_ref, 0)} presenças de {total}")
