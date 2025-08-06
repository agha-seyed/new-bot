import logging
from typing import Optional
from transformers import pipeline
from sentence_transformers import SentenceTransformer
from optimum.onnxruntime import ORTModelForQuestionAnswering
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

class AIModels:
    def __init__(self):
        self.sentence_transformer = None
        self.qa_pipeline = None
        self.stt_pipeline = None
        self.tokenizer = None

    def initialize(self):
        """Initialize AI models with quantization."""
        try:
            # Sentence Transformer with quantization
            self.sentence_transformer = SentenceTransformer(
                'sentence-transformers/paraphrase-MiniLM-L6-v2',
                device='cpu',
                quantize=True  # Dynamic quantization
            )
            logger.info("✅ Initialized quantized SentenceTransformer")

            # Quantized QA model using ONNX
            model_name = "distilbert-base-uncased"
            ort_model = ORTModelForQuestionAnswering.from_pretrained(
                model_name,
                export=True,
                provider="CPUExecutionProvider"
            )
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.qa_pipeline = pipeline(
                "question-answering",
                model=ort_model,
                tokenizer=self.tokenizer,
                device=-1  # CPU
            )
            logger.info("✅ Initialized quantized QA pipeline")

            # STT pipeline (unchanged for now)
            self.stt_pipeline = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-tiny",
                device=-1
            )
            logger.info("✅ Initialized STT pipeline")
        except Exception as e:
            logger.error(f"❌ Error initializing models: {str(e)}")
            raise

    def get_sentence_transformer(self) -> Optional[SentenceTransformer]:
        if not self.sentence_transformer:
            self.initialize()
        return self.sentence_transformer

    def get_qa_pipeline(self) -> Optional[pipeline]:
        if not self.qa_pipeline:
            self.initialize()
        return self.qa_pipeline

    def get_stt_pipeline(self) -> Optional[pipeline]:
        if not self.stt_pipeline:
            self.initialize()
        return self.stt_pipeline
