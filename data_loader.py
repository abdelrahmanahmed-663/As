import json
import logging
from pathlib import Path
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

# Load data from json file
def load_intents(path: str = "intents.json") -> list:
    if not Path(path).exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} intents from {path}")
    return data


def build_dataset(intents: list) -> tuple[list, list, dict]:
    texts, labels = [], []
    responses = {}

    for item in intents:
        intent = item["intent"]
        responses[intent] = item["responses"]
        for pattern in item["patterns"]:
            texts.append(pattern.strip())
            labels.append(intent)

    logger.info(f"Dataset built: {len(texts)} samples | {len(responses)} classes")
    return texts, labels, responses


def split_dataset(texts: list, labels: list, test_size: float = 0.2, seed: int = 42):
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels,
        test_size=test_size,
        random_state=42,
        stratify=labels
    )
    logger.info(f"Split → Train: {len(X_train)} | Test: {len(X_test)}")
    return X_train, X_test, y_train, y_test
