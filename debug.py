from patent_client import Patent

q = Patent.objects.filter(patent_title="CANCER")[:10]
for p in q:
    print(p.patent_number)
