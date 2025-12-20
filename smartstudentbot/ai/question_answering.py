import json
import asyncio
from typing import Optional, List
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from smartstudentbot.config import settings
from smartstudentbot.utils.logger import logger
import torch

class QAEngine:
    _instance = None
    _model = None
    _knowledge_base = []
    _qna_exact = {}
    _embeddings = None
    _loading_lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QAEngine, cls).__new__(cls)
        return cls._instance

    async def initialize(self):
        """Lazy load models and data"""
        if self._model is not None:
            return

        async with self._loading_lock:
            # Double check locking pattern
            if self._model is not None:
                return

            logger.info("Loading QA Engine (Lazy)...")

            # Load Data using pathlib for robustness
            base_path = Path(__file__).resolve().parent.parent # smartstudentbot/

            try:
                with open(base_path / "qna.json", "r") as f:
                    self._qna_exact = json.load(f)
                with open(base_path / "knowledge.json", "r") as f:
                    self._knowledge_base = json.load(f)
            except FileNotFoundError as e:
                logger.warning(f"Knowledge base files not found at {base_path}. Starting empty. Error: {e}")
                self._qna_exact = {}
                self._knowledge_base = []

            # Load Model (Lightweight DistilBERT)
            # Run in executor to avoid blocking main loop during load
            await asyncio.to_thread(self._load_model)

    def _load_model(self):
        # Use a lightweight model optimized for CPU
        self._model = SentenceTransformer('distiluse-base-multilingual-cased-v1')

        # Pre-compute embeddings for knowledge base
        if self._knowledge_base:
            texts = [item['question'] for item in self._knowledge_base]
            if texts:
                self._embeddings = self._model.encode(texts, convert_to_tensor=True)
                logger.info(f"Encoded {len(texts)} knowledge items.")
            else:
                self._embeddings = None

    async def get_answer(self, query: str, lang: str = "en") -> Optional[str]:
        if not settings.FEATURE_AI_ENABLED:
            return None

        # Lazy load if needed
        if self._model is None:
            await self.initialize()

        # 1. Exact Match (O(1))
        # Normalize query?
        if query in self._qna_exact:
            return self._qna_exact[query].get(lang, self._qna_exact[query].get("en"))

        # 2. Semantic Search
        if self._model and self._embeddings is not None:
            return await asyncio.to_thread(self._semantic_search, query, lang)

        return None

    def _semantic_search(self, query: str, lang: str) -> Optional[str]:
        query_embedding = self._model.encode(query, convert_to_tensor=True)

        # Compute cosine similarity
        cos_scores = util.cos_sim(query_embedding, self._embeddings)[0]

        # Find top result
        top_result = torch.topk(cos_scores, k=1)
        score = top_result.values[0].item()
        idx = top_result.indices[0].item()

        # Threshold for confidence
        if score > 0.6:
            return self._knowledge_base[idx]['answer'].get(lang, self._knowledge_base[idx]['answer'].get("en"))

        return None

# Global instance
qa_engine = QAEngine()
