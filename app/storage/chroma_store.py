import chromadb

def init_vector_store(cfg):
    client = chromadb.PersistentClient(path=cfg['vector_path'])
    return client.get_or_create_collection(
        name=cfg['collection_name'],
        metadata={"hnsw:space": cfg['similarity_metric']}
    )
