import json
import os

pasta = 'json_parts'
arquivos = sorted([
    f for f in os.listdir(pasta)
    if f.startswith('part_') and f.endswith('.json')
], key=lambda x: int(x.split('_')[1].split('.')[0]))

print(f"🔍 {len(arquivos)} arquivos encontrados em '{pasta}'.")

dados_totais = []
total_registros = 0
erros = 0

for arquivo in arquivos:
    caminho = os.path.join(pasta, arquivo)
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            if isinstance(dados, list):
                dados_totais.extend(dados)
                total_registros += len(dados)
                print(f"✅ {arquivo}: {len(dados)} registros adicionados.")
            else:
                print(f"⚠️ {arquivo} não contém uma lista.")
    except Exception as e:
        erros += 1
        print(f"❌ Erro ao processar {arquivo}: {e}")

# Salvar todos os dados em merged.json
if dados_totais:
    try:
        with open('merged.json', 'w', encoding='utf-8') as f:
            json.dump(dados_totais, f, ensure_ascii=False, indent=2)
        print(f"✅ merged.json criado com {total_registros} registros.")
        print(f"📄 Tamanho do arquivo: {os.path.getsize('merged.json') / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"❌ Erro ao salvar merged.json: {e}")
else:
    print("⚠️ Nenhum dado válido para salvar em merged.json.")

if erros > 0:
    print(f"⚠️ {erros} arquivo(s) apresentaram erro.")
