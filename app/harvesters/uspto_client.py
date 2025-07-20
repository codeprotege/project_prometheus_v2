from patent_client import Patent
from tqdm import tqdm

def harvest_patents(max_docs, cpc_codes=None, keyword=None):
    """Yield dicts with patent metadata & abstract text."""
    if keyword:
        q = Patent.objects.filter(patent_title=keyword)[:max_docs]
    else:
        q = Patent.objects.filter(cpc_inventive_class=cpc_codes)[:max_docs]
    for p in tqdm(q):
        yield {
            "patent_id": p.patent_number,
            "title": p.title or "",
            "abstract": p.abstract or "",
            "filing_date": str(p.filing_date) if p.filing_date else "",
            "assignee": p.assignee_name or "",
            "cpc": list(p.cpc)
        }
