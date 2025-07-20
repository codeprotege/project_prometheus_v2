import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

def harvest_patents(max_docs, cpc_codes=None, keyword=None):
    """Yield dicts with patent metadata & abstract text."""
    if keyword:
        query = keyword
    else:
        query = " OR ".join(cpc_codes)

    url = "https://ppubs.uspto.gov/pubwebapp/external/search.html"

    start = 0
    rows = 100

    patents = []
    with tqdm(total=max_docs, desc="Harvesting", unit="patent") as pbar:
        while start < max_docs:
            params = {
                "q": query,
                "start": start,
                "rows": rows,
            }
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                results = soup.find_all("div", class_="search-result")
                if not results:
                    break

                for result in results:
                    patent_id = result.find("span", class_="patent-number").text
                    title = result.find("span", class_="title").text
                    abstract = result.find("p", class_="abstract").text

                    patents.append({
                        "patent_id": patent_id,
                        "title": title,
                        "abstract": abstract,
                        "filing_date": "",
                        "assignee": "",
                        "cpc": [],
                    })
                    pbar.update(1)
                    if pbar.n >= max_docs:
                        break
            except requests.exceptions.RequestException as e:
                print(f"Error fetching patents: {e}")
                return []

            start += rows

    return patents
