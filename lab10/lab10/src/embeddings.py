#!/usr/bin/env python3
"""
Модуль векторних представлень (embeddings) із підтримкою двох бекендів:
  - local  (за замовчуванням без інтернету): детермінований TF-IDF + Truncated SVD
             (2 моделі: svd-word-128d та svd-charword-256d для української морфології)
  - neural (за наявності sentence-transformers): intfloat/multilingual-e5-small та
             sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
"""
import math
import re
from collections import Counter
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯіїєґІЇЄҐ0-9]+(?:-[a-zA-Zа-яА-ЯіїєґІЇЄҐ0-9]+)*")


def tokenize_words(text: str):
    return [t.lower() for t in TOKEN_RE.findall(text)]


def tokenize_char_word(text: str):
    words = tokenize_words(text)
    feats = list(words)
    # Додаємо символьні 3- та 4-грами для стійкості до українських відмінків (морфології)
    for w in words:
        if len(w) >= 4:
            padded = f"<{w}>"
            for n in (3, 4):
                for i in range(len(padded) - n + 1):
                    feats.append(f"c{n}:{padded[i:i+n]}")
    return feats


class LocalSVDEmbedder:
    """Локальний щільний ембедер (LSA: TF-IDF + Truncated SVD + L2-нормалізація)."""

    def __init__(self, name: str, dim: int = 128, use_char_ngrams: bool = False, seed: int = 42):
        self.name = name
        self.dim = dim
        self.use_char_ngrams = use_char_ngrams
        self.seed = seed
        self.vocab = {}
        self.idf = None
        self.vt = None  # shape (k, V)
        self.actual_dim = dim

    def _tokenize(self, text: str):
        return tokenize_char_word(text) if self.use_char_ngrams else tokenize_words(text)

    def fit(self, texts):
        n_docs = len(texts)
        df = Counter()
        doc_tokens = []
        for t in texts:
            toks = self._tokenize(t)
            doc_tokens.append(toks)
            for tok in set(toks):
                df[tok] += 1

        # Залишаємо токени, що зустрічаються >= 1 разу (обмежуємо словник для швидкодії)
        min_df = 2 if self.use_char_ngrams and n_docs >= 50 else 1
        kept = [tok for tok, c in df.items() if c >= min_df]
        kept.sort()
        self.vocab = {tok: idx for idx, tok in enumerate(kept)}
        V = len(self.vocab)
        self.idf = np.array([math.log((1 + n_docs) / (1 + df[tok])) + 1.0 for tok in kept], dtype=np.float32)

        X = self._tfidf_matrix(doc_tokens)
        k = min(self.dim, min(X.shape) - 1)
        k = max(2, k)
        self.actual_dim = k
        rng = np.random.default_rng(self.seed)
        v0 = rng.standard_normal(min(X.shape))
        _, _, vt = svds(X, k=k, v0=v0)
        # Сортуємо компоненти за спаданням сингулярних значень
        self.vt = vt[::-1].astype(np.float32)
        return self

    def _tfidf_matrix(self, doc_tokens):
        rows, cols, vals = [], [], []
        for r_idx, toks in enumerate(doc_tokens):
            if not toks:
                continue
            tf = Counter(toks)
            for tok, cnt in tf.items():
                c_idx = self.vocab.get(tok)
                if c_idx is not None:
                    rows.append(r_idx)
                    cols.append(c_idx)
                    vals.append((1.0 + math.log(cnt)) * float(self.idf[c_idx]))
        return csr_matrix((vals, (rows, cols)), shape=(len(doc_tokens), len(self.vocab)), dtype=np.float32)

    def encode(self, texts, is_query: bool = False) -> np.ndarray:
        doc_tokens = [self._tokenize(t) for t in texts]
        X = self._tfidf_matrix(doc_tokens)
        dense = X @ self.vt.T
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return (dense / norms).astype(np.float32)


class NeuralSentenceEmbedder:
    """Обгортка над sentence-transformers для запуску на машині студента (--backend neural)."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.name = model_name
        self.model = SentenceTransformer(model_name)
        self.is_e5 = "e5" in model_name.lower()

    def fit(self, texts):
        return self

    def encode(self, texts, is_query: bool = False) -> np.ndarray:
        if self.is_e5:
            prefix = "query: " if is_query else "passage: "
            texts = [prefix + t for t in texts]
        embs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(embs, dtype=np.float32)


def get_embedder(model_key: str, backend: str = "local", seed: int = 42):
    if backend == "neural":
        mapping = {
            "model_a": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "model_b": "intfloat/multilingual-e5-small",
        }
        return NeuralSentenceEmbedder(mapping.get(model_key, model_key))
    if model_key == "model_a":
        return LocalSVDEmbedder("SVD-Word-128d", dim=128, use_char_ngrams=False, seed=seed)
    return LocalSVDEmbedder("SVD-CharWord-256d", dim=160, use_char_ngrams=True, seed=seed)
