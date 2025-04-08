import os
import json

# Caminhos
json_folder = "json_parts"
merged_file = "merged.json"

# Verificar se a pasta existe e possui arquivos
if not os.path.exists(json_folder):
    print(f"❌ Pasta '{json_folder}' não encontrada.")
    exit(1)

json_files = sorted(
    [f for f in os.listdir(json_folder) if f.startswith("part_") and f.endswith(".json")],
    key=lambda x: int(x.split("_")[1].split(".")[0])
)

if not json_files:
    print("❌ Nenhum arquivo JSON encontrado na pasta json_parts.")
    exit(1)

print(f"🔍 Arquivos encontrados: {json_files}")

# Lista para todos os jobs
all_jobs = []

# Ler e somar tudo
for filename in json_files:
    file_path = os.path.join(json_folder, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
            if isinstance(jobs, list):
                all_jobs.extend(jobs)
                print(f"✅ {filename}: {len(jobs)} registros adicionados.")
            else:
                print(f"⚠️ {filename}: formato inesperado.")
    except Exception as e:
        print(f"⚠️ Erro ao ler {filename}: {e}")

# Salvar mesclado
if all_jobs:
    try:
        with open(merged_file, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, ensure_ascii=False, indent=2)
        print(f"✅ Arquivo mesclado salvo como {merged_file} com {len(all_jobs)} registros.")
    except Exception as e:
        print(f"❌ Erro ao salvar {merged_file}: {e}")
        exit(1)
else:
    print("⚠️ Nenhum dado válido para salvar.")
    exit(1)
