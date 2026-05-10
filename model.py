import logging
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

MODEL_NAME = "distilbert-base-uncased"


def build_model(num_labels: int):
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=num_labels,
        ignore_mismatched_sizes=True
    )
    logger.info(f"Model loaded: {MODEL_NAME} | Labels: {num_labels}")
    return model


def build_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    logger.info(f"Tokenizer loaded: {MODEL_NAME}")
    return tokenizer


def save_model(model, tokenizer, path: str = "as_agent_model"):
    model.save_pretrained(path)
    tokenizer.save_pretrained(path)
    logger.info(f"Model saved to: {path}")


def load_model(path: str = "as_agent_model"):
    model     = AutoModelForSequenceClassification.from_pretrained(path)
    tokenizer = AutoTokenizer.from_pretrained(path)
    logger.info(f"Model loaded from: {path}")
    return model, tokenizer
