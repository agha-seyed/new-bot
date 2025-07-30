import logging
from transformers import pipeline
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Load models with lazy initialization to save memory
model = None
qa_pipeline = None
stt_pipeline = None

def initialize_models():
    """Initialize AI models with error handling."""
    logger.info("🚀 Starting to initialize AI models...")
    global model, qa_pipeline, stt_pipeline
    try:
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        logger.info("✅ SentenceTransformer model loaded")
        qa_pipeline = pipeline(
            "question-answering",
            model="distilbert-base-cased-distilled-squad",
            tokenizer="distilbert-base-cased-distilled-squad",
        )
        logger.info("✅ QA pipeline loaded")
        stt_pipeline = pipeline("automatic-speech-recognition", model="openai/whisper-tiny")
        logger.info("✅ STT pipeline loaded")
        logger.info("✅ AI models initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing AI models: {str(e)}")
        raise
