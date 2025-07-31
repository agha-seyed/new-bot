import logging
from config import config
from transformers import pipeline
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Global variables for lazy initialization
model = None
qa_pipeline = None
stt_pipeline = None

def initialize_models():
    """Initialize AI models with error handling."""
    if not config.HUGGINGFACE_API_KEY:
        logger.error("❌ HUGGINGFACE_API_KEY not set")
        raise ValueError("HUGGINGFACE_API_KEY is required for AI models")

    logger.info("🚀 Starting to initialize AI models...")
    global model, qa_pipeline, stt_pipeline
    try:
        model = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2",
            device="cpu"  # Force CPU for Render
        )
        logger.info("✅ SentenceTransformer model loaded")
        qa_pipeline = pipeline(
            "question-answering",
            model="distilbert-base-cased-distilled-squad",
            tokenizer="distilbert-base-cased-distilled-squad",
            device=-1  # Force CPU
        )
        logger.info("✅ QA pipeline loaded")
        stt_pipeline = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-tiny",
            device=-1  # Force CPU
        )
        logger.info("✅ STT pipeline loaded")
        logger.info("✅ AI models initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing AI models: {str(e)}")
        raise
