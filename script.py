import requests
import gzip
import xml.etree.ElementTree as ET
import io
import json
import os

feed_url = "https://feeds.whatjobs.com/sinerj/sinerj_pt_BR.xml.gz"
json_folder = "json_parts"
os.makedirs(json_folder, exist_ok=True)

file_count = 1
jobs = []

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; FeedProcessor/1.0; +https://example.com/bot)"
}

print("📥 Baixando feed do WhatJobs...")
try:
    response = requests.get(feed_url, stream=True, headers=headers, timeout=30)
except requests.RequestException as e:
    print(f"❌ Erro de conexão: {e}")
    exit(1)

if response.status_code == 200:
    try:
        with gzip.open(io.BytesIO(response.content), "rt", encoding="utf-8") as f:
            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag == "job":
                    title = elem.findtext("title", "").strip()
                    description = elem.findtext("description", "").strip()
                    company = elem.findtext("company/name", "").strip()
                    job_type = elem.findtext("jobType", "").strip()
                    url = elem.findtext("urlDeeplink", "").strip()

                    location_elem = elem.find("locations/location")
                    city = location_elem.findtext("city", "").strip() if location_elem is not None else ""
                    state = location_elem.findtext("state", "").strip() if location_elem is not None else ""

                    if not title or not url:
                        elem.clear()
                        continue

                    job_data = {
                        "title": title,
                        "description": description,
                        "company": company,
                        "city": city,
                        "state": state,
                        "tipo": job_type,
                        "url": url
                    }

                    jobs.append(job_data)
                    elem.clear()

                    if len(jobs) >= 1000:
                        if file_count > 30:
                            print("⛔ Limite de 30 arquivos atingido.")
                            break
                        json_path = os.path.join(json_folder, f"part_{file_count}.json")
                        with open(json_path, "w", encoding="utf-8") as json_file:
                            json.dump(jobs, json_file, ensure_ascii=False, indent=2)
                        print(f"✅ Gerado {json_path} com 1000 registros.")
                        jobs = []
                        file_count += 1

            if jobs and file_count <= 30:
                json_path = os.path.join(json_folder, f"part_{file_count}.json")
                with open(json_path, "w", encoding="utf-8") as json_file:
                    json.dump(jobs, json_file, ensure_ascii=False, indent=2)
                print(f"✅ Gerado {json_path} com {len(jobs)} registros finais.")

        print(f"📦 Total de arquivos gerados: {file_count}")

    except Exception as e:
        print(f"❌ Erro ao processar XML: {e}")
else:
    print(f"❌ Erro HTTP ao baixar feed: {response.status_code}")
