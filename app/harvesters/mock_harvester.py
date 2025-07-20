import json
from tqdm import tqdm

def harvest_patents(max_docs, cpc_codes=None, keyword=None):
    """Yield dicts with patent metadata & abstract text from a local file."""
    with open("mock_patents.json", "r") as f:
        patents = json.load(f)

    for patent in tqdm(patents[:max_docs], desc="Harvesting", unit="patent"):
        yield patent
