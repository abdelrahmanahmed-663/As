import json
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments, EarlyStoppingCallback
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, classification_report
from torch.utils.data import Dataset
import warnings
import pickle
warnings.filterwarnings('ignore')

SEED = 42
MAX_LEN = 128
BATCH_SIZE = 16
EPOCHS = 10
LEARNING_RATE = 2e-5

MODEL_NAME = "distilbert-base-uncased"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

with open("intents.json", "r", encoding="utf-8") as f:
    data = json.load(f)

texts = []
labels = []

for intent in data["intents"]:
    for pattern in intent["patterns"]:
        texts.append(pattern.lower().strip())
        labels.append(intent["tag"])

label_encoder = LabelEncoder()
labels_encoded = label_encoder.fit_transform(labels)
num_labels = len(label_encoder.classes_)

print(f"Number of classes: {num_labels}")
print(f"Classes: {label_encoder.classes_}")

X_train, X_test, y_train, y_test = train_test_split(
    texts, labels_encoded,
    test_size=0.2,
    random_state=SEED,
    stratify=labels_encoded
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME, 
    num_labels=num_labels,
    ignore_mismatched_sizes=True
)
model.to(device)

class IntentDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_len,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

train_dataset = IntentDataset(X_train, y_train, tokenizer, MAX_LEN)
test_dataset = IntentDataset(X_test, y_test, tokenizer, MAX_LEN)

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    acc = accuracy_score(labels, predictions)
    f1 = f1_score(labels, predictions, average='weighted')
    return {
        'accuracy': acc,
        'f1_score': f1
    }

training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir='./logs',
    logging_steps=10,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="accuracy",
    greater_is_better=True,
    learning_rate=LEARNING_RATE,
    fp16=torch.cuda.is_available(),
    report_to="none"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
)

print("Starting training...")
trainer.train()

eval_results = trainer.evaluate()
print(f"Accuracy: {eval_results['eval_accuracy']*100:.2f}%")
print(f"F1-Score: {eval_results['eval_f1_score']*100:.2f}%")

predictions = trainer.predict(test_dataset)
pred_labels = np.argmax(predictions.predictions, axis=1)
print("\nClassification Report:")
print(classification_report(y_test, pred_labels, target_names=label_encoder.classes_))

model.save_pretrained("./best_model")
tokenizer.save_pretrained("./best_model")

with open("label_encoder.pkl", "wb") as f:
    pickle.dump(label_encoder, f)

print("\nSaved: best_model/, label_encoder.pkl")