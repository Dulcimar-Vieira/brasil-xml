import requests
import gzip
import xml.etree.ElementTree as ET
import io
import json
import os

# URL do feed
feed_url = "https://feeds.whatjobs.com/sinerj/sinerj_pt_BR.xml.gz"

# Pasta para salvar os arquivos JSON
json_folder = "json_parts"
os.makedirs(json_folder, exist_ok=True)

# Contador de arquivos
file_count = 1

# Baixar o feed XML comprimido
print("📥 Baixando feed...")
response = requests.get(feed_url, stream=True)

if response.status_code == 200:
    with gzip.open(io.BytesIO(response.content), "rt", encoding="utf-8") as f:
        jobs = []
        for event, elem in ET.iterparse(f, events=("end",)):
            if elem.tag == "job":
                title = elem.findtext("title", "").strip()

                location_elem = elem.find("locations/location")
                city = location_elem.findtext("city", "").strip() if location_elem is not None else ""
                state = location_elem.findtext("state", "").strip() if location_elem is not None else ""

                job_data = {
                    "title": title,
                    "description": elem.findtext("description", "").strip(),
                    "company": elem.findtext("company/name", "").strip(),
                    "city": city,
                    "state": state,
                    "url": elem.findtext("urlDeeplink", "").strip(),
                    "tipo": elem.findtext("jobType", "").strip(),
                }

                jobs.append(job_data)
                elem.clear()

                # Salvar em arquivos de 1000 registros com limite de 100 arquivos
                if len(jobs) >= 1000:
                    if file_count > 100:
                        print("⛔ Limite de 100 arquivos atingido. Encerrando processamento.")
                        break

                    json_path = os.path.join(json_folder, f"part_{file_count}.json")
                    with open(json_path, "w", encoding="utf-8") as json_file:
                        json.dump(jobs, json_file, ensure_ascii=False, indent=2)
                    print(f"✅ Gerado {json_path} com 1000 registros.")
                    jobs = []
                    file_count += 1

        # Salvar os registros restantes (menos de 1000)
        if jobs and file_count <= 100:
            json_path = os.path.join(json_folder, f"part_{file_count}.json")
            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(jobs, json_file, ensure_ascii=False, indent=2)
            print(f"✅ Gerado {json_path} com {len(jobs)} registros finais.")

    print(f"📦 Total de arquivos gerados: {file_count}")
else:
    print(f"❌ Erro ao baixar o feed: {response.status_code}")
