import re
import logging
import torch
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def preprocess_batch(texts: list) -> list:
    cleaned = [clean_text(t) for t in texts]
    logger.debug(f"Preprocessed {len(cleaned)} samples")
    return cleaned


class IntentDataset(Dataset):
    def __init__(self, texts: list, labels: list, tokenizer, max_len: int = 64):
        self.texts     = preprocess_batch(texts)
        self.labels    = labels
        self.tokenizer = tokenizer
        self.max_len   = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt"
        )
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "label":          torch.tensor(self.labels[idx], dtype=torch.long)
        }
