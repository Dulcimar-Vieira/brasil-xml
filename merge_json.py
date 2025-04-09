import os
import json
from datetime import datetime

# Pasta onde estão os arquivos
json_folder = "json_parts"
merged_file = "merged.json"

# Verificar se a pasta existe
if not os.path.exists(json_folder):
    print(f"❌ Pasta '{json_folder}' não encontrada.")
    exit(1)

# Listar e ordenar os arquivos JSON válidos
json_files = sorted(
    [f for f in os.listdir(json_folder) if f.startswith("part_") and f.endswith(".json")],
    key=lambda x: int(x.split("_")[1].split(".")[0])
)

if not json_files:
    print("❌ Nenhum arquivo JSON encontrado para mesclar.")
    exit(1)

print(f"🔍 Arquivos encontrados: {json_files}")

# Lista para armazenar os dados
all_jobs = []

for filename in json_files:
    path = os.path.join(json_folder, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
            if isinstance(jobs, list):
                all_jobs.extend(jobs)
                print(f"✅ {filename} - {len(jobs)} registros adicionados.")
            else:
                print(f"⚠️ {filename} tem formato inválido.")
    except Exception as e:
        print(f"⚠️ Erro ao processar {filename}: {e}")

if not all_jobs:
    print("❌ Nenhuma vaga encontrada. merged.json não será salvo.")
    exit(1)

# Geração com timestamp
output = {
    "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_vagas": len(all_jobs),
    "vagas": all_jobs
}

# Salvar
with open(merged_file, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ merged.json criado com {len(all_jobs)} vagas.")
