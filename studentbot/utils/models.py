import logging
from typing import Optional
from studentbot import config
from transformers import pipeline
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class AIModels:
    """Manages AI models for NLP tasks."""
    
    def __init__(self):
        self.model: Optional[SentenceTransformer] = None
        self.qa_pipeline = None
        self.stt_pipeline = None
    
    def initialize(self):
        """Initialize AI models with lazy loading."""
        if not config.HUGGINGFACE_API_KEY:
            logger.error("❌ HUGGINGFACE_API_KEY not set")
            raise ValueError("HUGGINGFACE_API_KEY is required")
        
        logger.info("🚀 Initializing AI models...")
        try:
            # Lazy initialization to save memory
            if not self.model:
                self.model = SentenceTransformer(
                    "paraphrase-multilingual-MiniLM-L12-v2",
                    device="cpu"
                )
                logger.info("✅ SentenceTransformer model loaded")
            
            if not self.qa_pipeline:
                self.qa_pipeline = pipeline(
                    "question-answering",
                    model="distilbert-base-cased-distilled-squad",
                    tokenizer="distilbert-base-cased-distilled-squad",
                    device=-1
                )
                logger.info("✅ QA pipeline loaded")
            
            if not self.stt_pipeline:
                self.stt_pipeline = pipeline(
                    "automatic-speech-recognition",
                    model="openai/whisper-tiny",
                    device=-1
                )
                logger.info("✅ STT pipeline loaded")
            
            logger.info("✅ AI models initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing AI models: {str(e)}")
            raise
    
    def get_sentence_transformer(self) -> SentenceTransformer:
        """Get SentenceTransformer model, initializing if necessary."""
        if not self.model:
            self.initialize()
        return self.model
    
    def get_qa_pipeline(self):
        """Get QA pipeline, initializing if necessary."""
        if not self.qa_pipeline:
            self.initialize()
        return self.qa_pipeline
    
    def get_stt_pipeline(self):
        """Get STT pipeline, initializing if necessary."""
        if not self.stt_pipeline:
            self.initialize()
        return self.stt_pipeline

ai_models = AIModels()
