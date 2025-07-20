from sentence_transformers import SentenceTransformer

model_cache = {}

def get_model(name):
    if name not in model_cache:
        model_cache[name] = SentenceTransformer(name, device="cpu")
    return model_cache[name]

def embed(docs, model_name):
    model = get_model(model_name)
    return model.encode(docs, convert_to_numpy=True, show_progress_bar=True)
