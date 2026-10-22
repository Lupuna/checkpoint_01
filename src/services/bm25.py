import math
import re
from collections import Counter

import numpy as np


class BM25:
    STOP_WORDS = set(
        "а бы в во для до же за и из или к как ко ли на не но о об от по при с со то у что это я мне мой".split()
    )

    def __init__(
        self, 
        texts: list[str],
        k1: float = 1.5,
        b: float = 0.75
    ):
        self.docs = [self._terms(text) for text in texts]
        self.k1, self.b = k1, b
        self.lengths = np.array([len(doc) for doc in self.docs], dtype=np.float32)
        self.avg = float(self.lengths.mean())
        self.freqs = [Counter(d) for d in self.docs]
        self.idf = self._calculate_idf()
    
    def _terms(self, text: str) -> list[str]:
        words = [w for w in re.findall(r'\w+', text.lower()) if w not in self.STOP_WORDS]
        return [w if re.search(r"[0-9a-z]", w) else w[:6] for w in words]

    def _calculate_idf(self) -> dict[str, float]:
        seen = Counter(w for d in self.docs for w in set(d))
        n = len(self.docs)
        return {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in seen.items()}

    def scores(self, query: str) -> np.ndarray:
        result = np.zeros(len(self.docs), dtype=np.float32)
        for word in self._terms(query):
            if word not in self.idf:
                continue
            idf = self.idf[word]
            for i, freq in enumerate(self.freqs):
                if word in freq:
                    tf = freq[word]
                    result[i] += idf * (tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg)))
        return result

    def top(self, query: str, n: int = 20) -> list[int]:
        scores = self.scores(query)
        return [int(i) for i in np.argsort(-scores)[:n] if scores[i] > 0]
