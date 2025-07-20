import requests
from tqdm import tqdm
import json

def harvest_patents(max_docs, cpc_codes=None, keyword=None):
    """Yield dicts with patent metadata & abstract text."""
    if keyword:
        query = f'{{"searchText":"{keyword}"}}'
    else:
        cpc_query = " OR ".join([f'cpc:"{cpc}"' for cpc in cpc_codes])
        query = f'{{"searchText":"{cpc_query}"}}'

    url = "https://ppubs.uspto.gov/solr/pubeach/solr/pubeach/search"
    headers = {"Content-Type": "application/json"}

    start = 0
    rows = 100

    patents = []
    with tqdm(total=max_docs, desc="Harvesting", unit="patent") as pbar:
        while start < max_docs:
            params = {"start": start, "rows": rows}
            try:
                response = requests.post(url, headers=headers, data=query, params=params)
                response.raise_for_status()
                data = response.json()
                patents.extend(data.get("patents", []))
                pbar.update(len(data.get("patents", [])))
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                print(f"Error fetching patents: {e}")
                return []


            for patent in patents:
                yield {
                    "patent_id": patent.get("patentNumber", ""),
                    "title": patent.get("title", ""),
                    "abstract": patent.get("abstractText", ""),
                    "filing_date": patent.get("filingDate", ""),
                    "assignee": patent.get("assignee", ""),
                    "cpc": [c.get("class") for c in patent.get("cpc", [])],
                }
                pbar.update(1)
                if pbar.n >= max_docs:
                    break

            start += rows
            if not data.get("patents"):
                break
