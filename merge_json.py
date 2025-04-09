import os
import json
from datetime import datetime

# Caminhos
pasta = 'json_parts'
merged_file = 'merged.json'

# Coletar arquivos válidos
arquivos = sorted([
    f for f in os.listdir(pasta)
    if f.startswith('part_') and f.endswith('.json')
], key=lambda x: int(x.split('_')[1].split('.')[0]))

print(f"🔍 Arquivos encontrados: {arquivos}")

dados_totais = []
erros = 0

for arquivo in arquivos:
    caminho = os.path.join(pasta, arquivo)
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            if isinstance(dados, list):
                dados_totais.extend(dados)
                print(f"✅ {arquivo}: {len(dados)} registros adicionados.")
            else:
                print(f"⚠️ {arquivo} não contém uma lista.")
    except Exception as e:
        erros += 1
        print(f"❌ Erro ao processar {arquivo}: {e}")

if dados_totais:
    resultado = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_vagas": len(dados_totais),
        "vagas": dados_totais
    }
    with open(merged_file, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"✅ Arquivo '{merged_file}' gerado com {len(dados_totais)} vagas.")
    print(f"📄 Tamanho final: {os.path.getsize(merged_file) / (1024 * 1024):.2f} MB")
else:
    print("⚠️ Nenhum dado válido encontrado. merged.json não foi criado.")

if erros > 0:
    print(f"⚠️ {erros} arquivo(s) apresentaram erro e foram ignorados.")
