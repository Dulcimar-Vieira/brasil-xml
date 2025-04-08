import os
import json

# Caminhos
json_folder = "json_parts"
merged_file = "merged.json"

# Verificar se a pasta existe
if not os.path.exists(json_folder):
    print(f"❌ Pasta '{json_folder}' não encontrada.")
    exit(1)

# Coletar arquivos part_XXX.json em ordem
json_files = sorted(
    [f for f in os.listdir(json_folder) if f.startswith("part_") and f.endswith(".json")],
    key=lambda x: int(x.split("_")[1].split(".")[0])
)

if not json_files:
    print("❌ Nenhum arquivo JSON encontrado.")
    exit(1)

print(f"🔍 Arquivos encontrados: {json_files}")

all_jobs = []
falhas = []

# Processar arquivos
for filename in json_files:
    caminho = os.path.join(json_folder, filename)
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            if isinstance(dados, list):
                all_jobs.extend(dados)
                print(f"✅ {filename}: {len(dados)} registros adicionados.")
            else:
                print(f"⚠️ {filename}: formato inválido, não é uma lista.")
                falhas.append(filename)
    except Exception as e:
        print(f"❌ Erro ao ler {filename}: {e}")
        falhas.append(filename)

# Tentar salvar mesmo com falhas
if all_jobs:
    try:
        with open(merged_file, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, ensure_ascii=False, indent=2)
        print(f"✅ merged.json criado com {len(all_jobs)} registros.")
    except Exception as e:
        print(f"❌ Erro ao salvar merged.json: {e}")
        exit(1)
else:
    print("⚠️ Nenhum dado válido para salvar.")
    exit(1)

# Mostrar resumo de falhas
if falhas:
    print("⚠️ Arquivos com erro ou formato inválido:")
    for f in falhas:
        print(f"  - {f}")
