import nltk
from collections import Counter

def extract_keywords(text:str, stop_set):
    tokens = nltk.word_tokenize(text.lower())
    return Counter(tok for tok in tokens if tok.isalpha() and tok not in stop_set)
