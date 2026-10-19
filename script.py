#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gzip
import hashlib
import io
import json
import os
import random
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import Counter
from zoneinfo import ZoneInfo

import requests

FEED_URL = "https://feeds.whatjobs.com/sinerj/sinerj_pt_BR.xml.gz"
OUTPUT_FOLDER = "json_parts"
STATE_FILE = "daily_jobs_state.json"
MAX_JOBS_PER_RUN = 1000
TIMEZONE = ZoneInfo("America/Sao_Paulo")


# Extração de remuneração inspirada na validação do repositório rio-de-janeiro.
MONEY_NUMBER = (
    r"(?:"
    r"\d{1,3}(?:\.\d{3})+(?:,\d{2})?"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d{2})?"
    r"|\d+(?:,\d{2}|\.\d{2})?"
    r")"
)
SALARY_AMOUNT_RE = re.compile(
    rf"\b(?:faixa salarial|piso salarial|sal[aá]rios?|remunera[cç][aã]o|proventos)\b"
    rf"(?:\s+(?:fixo|base|mensal(?:\s+de)?|bruto|inicial|m[ií]nimo garantido|"
    rf"oferecido|oferecida|oferecidos|oferecidas|de at[eé]|a partir de|entre)){{0,3}}"
    rf"\s*(?:[:：=–—-]\s*)?"
    rf"(?:(?:a partir de|de|entre)\s+)?"
    rf"(?P<amount>(?:R\$\s*)?{MONEY_NUMBER})(?![\d.,])",
    re.IGNORECASE,
)

def normalize_salary_text(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip().lower()

def has_real_salary(salary):
    value = normalize_salary_text(salary)
    if not value:
        return False
    placeholders = (
        "a combinar", "nao informado", "nao informada",
        "nao divulgado", "nao divulgada", "confidencial",
        "negociavel", "sob consulta", "salario nao informado",
        "salario a combinar",
    )
    if any(marker in value for marker in placeholders):
        return False
    if not re.search(r"\d", value):
        return False
    if not re.search(r"(?:R\$|[$€£])", value) and re.fullmatch(r"\d+", value):
        return False
    return True

def extract_salary(structured_salary, description):
    """Prioriza <salary>; no fallback aceita somente valor ligado a rótulo salarial."""
    structured_salary = re.sub(r"\s+", " ", structured_salary or "").strip()
    if has_real_salary(structured_salary):
        return structured_salary

    text = re.sub(r"<[^>]+>", " ", description or "")
    text = re.sub(r"\s+", " ", text).strip()
    for match in SALARY_AMOUNT_RE.finditer(text):
        amount = re.sub(r"\s+", " ", match.group("amount")).strip()
        raw_number = re.sub(r"^R\$\s*", "", amount, flags=re.IGNORECASE).strip()
        has_currency = amount.upper().startswith("R$")
        if not has_currency and re.fullmatch(r"\d{1,2}", raw_number):
            continue
        return amount
    return ""


CIDADES = None

def normalize(text):
    return (text or "").strip().lower()

def clean_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()

def parse_date(value):
    if not value:
        return None
    value = value.strip()
    formats = (
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

def job_key(job):
    return job.get("url") or hashlib.md5(
        f"{job.get('title','')}|{job.get('company','')}|{job.get('city','')}".encode("utf-8")
    ).hexdigest()

def load_state(today):
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        if state.get("date") != today:
            return {}
        return state.get("jobs", {})
    except (OSError, json.JSONDecodeError):
        return {}

def save_state(today, selected):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"date": today, "jobs": selected}, f, ensure_ascii=False, indent=2)

def gerar_intro(titulo, cidade):
    intros = [
        f"Confira a oportunidade para {titulo} em {cidade}. Veja requisitos e como se candidatar.",
        f"Nova vaga disponível para {titulo} em {cidade}. Saiba mais sobre essa oportunidade.",
        f"Empresa está contratando {titulo} em {cidade}. Veja detalhes e envie seu currículo.",
    ]
    return random.choice(intros)

def local_name(tag):
    # ElementTree inclui {namespace} no nome quando o XML usa namespace.
    return str(tag).rsplit('}', 1)[-1].split(':')[-1].lower()

def find_node(element, path):
    current = element
    for part in path.split('/') if path else []:
        if current is None:
            return None
        wanted = part.lower()
        current = next((child for child in list(current) if local_name(child.tag) == wanted), None)
    return current

def text_at(element, path):
    node = find_node(element, path)
    if node is None:
        return ''
    return ''.join(node.itertext()).strip()

def build_job(elem):
    title = text_at(elem, "title")
    description = text_at(elem, "description")
    company = text_at(elem, "company/name") or "Confidencial"
    url = text_at(elem, "urlDeeplink") or text_at(elem, "link")
    job_type = text_at(elem, "jobType")
    source_salary = text_at(elem, "salary")
    location_elem = find_node(elem, "locations/location")
    city = text_at(location_elem, "city") if location_elem is not None else text_at(elem, "city")
    state = text_at(location_elem, "state") if location_elem is not None else text_at(elem, "state")
    pub_raw = text_at(elem, "pubdate") or text_at(elem, "pubDate")
    updated_raw = text_at(elem, "updated")
    pub_dt = parse_date(pub_raw) or parse_date(updated_raw)

    if not title or not url or not city or not state:
        return None

    if not job_matches(city, title, description):
        return None

    salary = extract_salary(source_salary, description)
    description = clean_html(description)
    return {
        "id": hashlib.md5(f"{title}-{company}-{city}-{url}".encode("utf-8")).hexdigest(),
        "title": title,
        "description": description,
        "company": company,
        "salary": salary,
        "city": city,
        "state": state,
        "url": url,
        "tipo": job_type,
        "data_publicacao": pub_dt.date().isoformat() if pub_dt else "",
        "data_atualizacao": updated_dt.date().isoformat() if (updated_dt := parse_date(updated_raw)) else "",
        "origem": "WhatJobs",
    }

def job_matches(city, title, description):
    return True

def seasonal_score(job):
    title = normalize_salary_text(job.get('title', ''))
    description = normalize_salary_text(clean_html(job.get('description', '')))
    company = normalize_salary_text(job.get('company', ''))
    text = f'{title} {description} {company}'
    explicit_terms = (
        'extra natal', 'extra de natal', 'temporario natal', 'temporaria natal',
        'temporario de natal', 'temporaria de natal',
        'temporarios de natal', 'temporarias de natal', 'vagas natalinas',
        'natalino', 'natalina', 'natalinos', 'natalinas',
        'natal 2026', 'fim de ano', 'final de ano', 'temporada de natal',
        'black friday', 'black friday 2026', 'reforco de natal',
        'reforco para o natal', 'contratacao de natal', 'vagas para o natal',
        'temporario de fim de ano', 'temporaria de fim de ano',
    )
    if any(term in text for term in explicit_terms):
        return 2

    temporary_terms = ('temporario', 'temporaria', 'temporarios', 'temporarias', 'contrato temporario', 'contratacao temporaria')
    retail_terms = (
        'estoquista', 'vendedor', 'vendedora', 'atendente',
        'operador de caixa', 'operadora de caixa', 'repositor', 'repositora',
        'auxiliar de loja', 'promotor', 'promotora', 'embalador', 'embaladora',
        'shopping', 'loja', 'vendas',
    )
    if any(term in text for term in temporary_terms) and any(term in title for term in retail_terms):
        return 1
    return 0

def main():
    today = datetime.now(TIMEZONE).date().isoformat()
    print(f"📅 Data de execução: {today}")
    print("📥 Baixando e analisando o feed nacional do WhatJobs...")
    try:
        response = requests.get(
            FEED_URL,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FeedProcessor/1.0)"},
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise SystemExit(f"❌ Erro ao baixar o feed: {e}")

    candidates = {}
    jobs_seen = 0
    jobs_rejected = 0
    jobtype_total = 0
    jobtype_nonempty = 0
    jobtype_values = Counter()
    type_related_tags = Counter()
    type_related_values = {}
    with gzip.open(io.BytesIO(response.content), "rt", encoding="utf-8") as f:
        for event, elem in ET.iterparse(f, events=("end",)):
            if local_name(elem.tag) != "job":
                continue
            jobs_seen += 1

            # Diagnóstico do XML original: conta jobType e possíveis campos equivalentes.
            for node in elem.iter():
                tag = local_name(node.tag)
                if any(term in tag for term in ("type", "employment", "contract", "category")):
                    type_related_tags[tag] += 1
                    value = " ".join("".join(node.itertext()).split())
                    if value:
                        values = type_related_values.setdefault(tag, Counter())
                        values[value] += 1
            for node in elem.iter():
                if local_name(node.tag) == "jobtype":
                    jobtype_total += 1
                    value = " ".join("".join(node.itertext()).split())
                    if value:
                        jobtype_nonempty += 1
                        jobtype_values[value] += 1

            job = build_job(elem)
            if job:
                candidates[job_key(job)] = job
            else:
                jobs_rejected += 1
            elem.clear()

    seasonal = [job for job in candidates.values() if seasonal_score(job) > 0]
    seasonal.sort(
        key=lambda j: (
            seasonal_score(j),
            j.get("data_publicacao", ""),
            j.get("data_atualizacao", ""),
        ),
        reverse=True,
    )
    jobs = seasonal[:MAX_JOBS_PER_RUN]

    print(f"🔎 Registros <job> lidos no XML: {jobs_seen}")
    print(f"✅ Vagas com os campos essenciais: {len(candidates)}")
    print(f"↩️ Registros descartados por dados obrigatórios: {jobs_rejected}")
    print(f"DIAG jobType: nós encontrados={jobtype_total}; preenchidos={jobtype_nonempty}; vazios/ausentes={max(0, jobs_seen-jobtype_nonempty)}")
    print("DIAG campos relacionados a tipo/contrato/categoria:")
    for tag, qty in type_related_tags.most_common(25):
        values = type_related_values.get(tag, Counter())
        print(f"DIAG campo={tag}; nós={qty}; valores preenchidos={sum(values.values())}; mais comuns={values.most_common(8)}")
    print(f"DIAG valores jobType mais comuns: {jobtype_values.most_common(20)}")
    print(f"🎄 Vagas classificadas como Natal/fim de ano: {len(seasonal)}")
    print(f"📦 Vagas sazonais selecionadas (limite 1.000): {len(jobs)}")

    if not jobs:
        raise SystemExit("❌ Não foram encontradas vagas sazonais. Os arquivos publicados foram preservados para evitar substituir o feed por um arquivo vazio.")

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    for filename in os.listdir(OUTPUT_FOLDER):
        if filename.startswith("part_") and filename.endswith(".json"):
            os.remove(os.path.join(OUTPUT_FOLDER, filename))

    output_path = os.path.join(OUTPUT_FOLDER, "part_1.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    print(f"✅ Feed sazonal pronto: {output_path}")
if __name__ == "__main__":
    main()
