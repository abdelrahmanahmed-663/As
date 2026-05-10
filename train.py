import os
import json
import pickle 
import logging
import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import get_linear_schedule_with_warmup
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from data_loader import load_intents, build_dataset, split_dataset
from preprocess import IntentDataset, preprocess_batch
from model import build_model, build_tokenizer, save_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("training.log")
    ]
)
logger = logging.getLogger(__name__)

BATCH_SIZE    = 16
EPOCHS        = 20
LR            = 2e-5
MAX_LEN       = 64
WEIGHT_DECAY  = 0.01
WARMUP_RATIO  = 0.1
MAX_GRAD_NORM = 1.0
PATIENCE      = 4
SEED          = 42
MODEL_DIR     = "as_agent_model"
ENCODER_PATH  = "label_encoder.pkl"
RESPONSES_PATH= "responses.json"

torch.manual_seed(SEED)
np.random.seed(SEED)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# Data augmentation
def augment(texts, labels):
    
    import random
    aug_texts, aug_labels = list(texts), list(labels)
    for t, l in zip(texts, labels):
        words = t.split()
        if len(words) < 2:
            continue
        for _ in range(2):
            w = words.copy()
            op = random.randint(0, 2)
            if op == 0 and len(w) > 2:
                w.pop(random.randint(0, len(w)-1))
            elif op == 1:
                i, j = random.sample(range(len(w)), 2)
                w[i], w[j] = w[j], w[i]
            else:
                idx = random.randint(0, len(w)-1)
                w.insert(idx, w[random.randint(0, len(w)-1)])
            aug_texts.append(" ".join(w))
            aug_labels.append(l)
    return aug_texts, aug_labels


def evaluate(model, loader, device):
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for batch in loader:
            ids   = batch["input_ids"].to(device)
            mask  = batch["attention_mask"].to(device)
            lbls  = batch["label"].to(device)
            out   = model(ids, attention_mask=mask)
            preds = out.logits.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(lbls.cpu().numpy())

    acc = accuracy_score(all_labels, all_preds)
    prec, rec, f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, average="weighted", zero_division=0
    )
    return acc, prec, rec, f1


def train():
    
    logger.info("  AS Agent — Training Pipeline")
    logger.info(f"Device: {device}")

    intents = load_intents("intents.json")
    texts, labels, responses = build_dataset(intents)

    with open(RESPONSES_PATH, "w", encoding="utf-8") as f:
        json.dump(responses, f, indent=2)
    logger.info(f"Responses saved {RESPONSES_PATH}")

    label_enc      = LabelEncoder()
    labels_encoded = label_enc.fit_transform(labels)
    num_classes    = len(label_enc.classes_)

    with open(ENCODER_PATH, "wb") as f:
        pickle.dump(label_enc, f)
    logger.info(f"Label encoder saved → {ENCODER_PATH}")

    X_train, X_test, y_train, y_test = split_dataset(texts, labels_encoded)
    X_train_aug, y_train_aug         = augment(X_train, y_train)
    logger.info(f"Augmented train: {len(X_train_aug)} samples")

    tokenizer    = build_tokenizer()
    train_ds     = IntentDataset(X_train_aug, y_train_aug, tokenizer, MAX_LEN)
    test_ds      = IntentDataset(X_test,      y_test,      tokenizer, MAX_LEN)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    class_weights = compute_class_weight("balanced", classes=np.unique(y_train_aug), y=y_train_aug)
    cw_tensor     = torch.tensor(class_weights, dtype=torch.float).to(device)
    loss_fn       = torch.nn.CrossEntropyLoss(weight=cw_tensor)

    model     = build_model(num_classes)
    model.to(device)

    optimizer     = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    total_steps   = len(train_loader) * EPOCHS
    warmup_steps  = int(total_steps * WARMUP_RATIO)
    scheduler     = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    scaler        = torch.cuda.amp.GradScaler() if torch.cuda.is_available() else None

    best_acc      = 0.0
    patience_cnt  = 0

    logger.info(f"\nTraining for up to {EPOCHS} epochs (patience={PATIENCE})...\n")
    

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0

        for batch in train_loader:
            ids  = batch["input_ids"].to(device)
            mask = batch["attention_mask"].to(device)
            lbls = batch["label"].to(device)
            optimizer.zero_grad()

            if scaler:
                with torch.cuda.amp.autocast():
                    out  = model(ids, attention_mask=mask)
                    loss = loss_fn(out.logits, lbls)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
                scaler.step(optimizer)
                scaler.update()
            else:
                out  = model(ids, attention_mask=mask)
                loss = loss_fn(out.logits, lbls)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
                optimizer.step()

            scheduler.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)
        acc, prec, rec, f1 = evaluate(model, test_loader, device)

        status = ""
        if acc > best_acc:
            best_acc     = acc
            patience_cnt = 0
            save_model(model, tokenizer, MODEL_DIR)
            status = " ← BEST"
        else:
            patience_cnt += 1

        logger.info(
            f"Epoch {epoch:02d}/{EPOCHS} | Loss: {avg_loss:.4f} | "
            f"Acc: {acc*100:.2f}% | P: {prec:.3f} | R: {rec:.3f} | F1: {f1:.3f}{status}"
        )

        if patience_cnt >= PATIENCE:
            logger.info(f"\nEarly stopping at epoch {epoch}.")
            break

    
    logger.info(f"Best Accuracy : {best_acc*100:.2f}%")
    logger.info(f"Model saved   : {MODEL_DIR}/")
    logger.info("Training complete.")


if __name__ == "__main__":
    train()
