#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conta os campos de tipo no XML original do WhatJobs sem alterar os feeds."""

import gzip
import io
from collections import Counter

import requests
import xml.etree.ElementTree as ET

FEED_URL = "https://feeds.whatjobs.com/sinerj/sinerj_pt_BR.xml.gz"
TIMEOUT = 120

FIELD_ALIASES = {
    "jobtype",
    "employmenttype",
    "contracttype",
    "jobcategory",
    "category",
    "type",
}

def local_name(tag):
    return str(tag).rsplit("}", 1)[-1].split(":")[-1].lower()

def get_text(node):
    return " ".join("".join(node.itertext()).split())

def main():
    print("Baixando XML original do WhatJobs...")
    response = requests.get(
        FEED_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; FeedFieldDiagnostic/1.0)"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()

    rows = 0
    field_rows = Counter()
    field_nodes = Counter()
    field_values = {}
    jobtype_present = 0
    jobtype_filled = 0
    jobtype_empty = 0
    jobtype_values = Counter()
    examples = []

    with gzip.open(io.BytesIO(response.content), "rt", encoding="utf-8") as xml:
        for _, job in ET.iterparse(xml, events=("end",)):
            if local_name(job.tag) != "job":
                continue
            rows += 1
            values_in_job = {}
            for node in job.iter():
                name = local_name(node.tag)
                if name not in FIELD_ALIASES and not any(
                    word in name for word in ("jobtype", "employmenttype", "contracttype", "jobcategory")
                ):
                    continue
                value = get_text(node)
                field_nodes[name] += 1
                if name not in values_in_job:
                    values_in_job[name] = []
                if value:
                    values_in_job[name].append(value)
                    field_values.setdefault(name, Counter())[value] += 1

            for name, vals in values_in_job.items():
                if vals:
                    field_rows[name] += 1

            if "jobtype" in values_in_job:
                jobtype_present += 1
                nonempty = [v for v in values_in_job["jobtype"] if v]
                if nonempty:
                    jobtype_filled += 1
                    jobtype_values.update(nonempty)
                    if len(examples) < 10:
                        title = ""
                        for node in job.iter():
                            if local_name(node.tag) == "title":
                                title = get_text(node)
                                break
                        examples.append((title, nonempty[0]))
                else:
                    jobtype_empty += 1
            job.clear()

    print(f"TOTAL_JOB_RECORDS={rows}")
    print(f"JOBTYPE_NODE_PRESENT_IN={jobtype_present}")
    print(f"JOBTYPE_WITH_VALUE_IN={jobtype_filled}")
    print(f"JOBTYPE_EMPTY_WHEN_PRESENT={jobtype_empty}")
    print(f"JOBTYPE_MISSING={rows - jobtype_present}")
    print("FIELDS_WITH_TYPE_OR_CATEGORY:")
    for name, count in field_rows.most_common():
        vals = field_values.get(name, Counter())
        print(f"FIELD={name}; JOBS_WITH_VALUE={count}; NONEMPTY_VALUES={vals.total()}; TOP_VALUES={vals.most_common(10)}")
    print(f"JOBTYPE_TOP_VALUES={jobtype_values.most_common(20)}")
    print(f"EXAMPLES_TITLE_AND_JOBTYPE={examples}")

if __name__ == "__main__":
    main()
