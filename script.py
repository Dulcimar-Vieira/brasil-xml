import requests
import gzip
import xml.etree.ElementTree as ET
import io
import json
import os
from datetime import datetime

feed_url = "https://feeds.whatjobs.com/sinerj/sinerj_pt_BR.xml.gz"
json_folder = "json_parts"
os.makedirs(json_folder, exist_ok=True)

# Limpar arquivos antigos
for f in os.listdir(json_folder):
    if f.endswith(".json"):
        os.remove(os.path.join(json_folder, f))

file_count = 1

try:
    print("📥 Baixando feed...")
    response = requests.get(feed_url, stream=True, timeout=120)
    response.raise_for_status()
except requests.RequestException as e:
    print(f"❌ Erro na requisição: {e}")
    exit(1)

try:
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
                    "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                jobs.append(job_data)
                elem.clear()

                if len(jobs) >= 1000:
                    json_path = os.path.join(json_folder, f"part_{file_count}.json")
                    print(f"✅ Gerando {json_path} com {len(jobs)} registros.")
                    with open(json_path, "w", encoding="utf-8") as json_file:
                        json.dump(jobs, json_file, ensure_ascii=False, indent=2)
                    jobs = []
                    file_count += 1

        if jobs:
            json_path = os.path.join(json_folder, f"part_{file_count}.json")
            print(f"✅ Gerando arquivo final {json_path} com {len(jobs)} registros.")
            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(jobs, json_file, ensure_ascii=False, indent=2)

    print(f"📦 Arquivos JSON gerados: {os.listdir(json_folder)}")

except Exception as e:
    print(f"❌ Erro ao processar o XML: {e}")
    exit(1)
