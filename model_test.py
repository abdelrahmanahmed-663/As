import torch
import pickle
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def load_model_and_tokenizer(model_path="./best_model"):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    
    with open("label_encoder.pkl", "rb") as f:
        label_encoder = pickle.load(f)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    
    return model, tokenizer, label_encoder, device

def predict_intent(text, model, tokenizer, label_encoder, device, max_len=128):
    encoding = tokenizer(
        text.lower().strip(),
        truncation=True,
        padding='max_length',
        max_length=max_len,
        return_tensors='pt'
    )
    
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)
    
    with torch.no_grad():
        outputs = model(input_ids, attention_mask=attention_mask)
        probabilities = torch.softmax(outputs.logits, dim=-1)
        predicted_class = torch.argmax(probabilities, dim=-1).cpu().numpy()[0]
        confidence = torch.max(probabilities).cpu().numpy()
    
    intent = label_encoder.inverse_transform([predicted_class])[0]
    
    all_probs = probabilities.cpu().numpy()[0]
    top_3_indices = np.argsort(all_probs)[-3:][::-1]
    top_3_intents = [(label_encoder.inverse_transform([idx])[0], all_probs[idx]) for idx in top_3_indices]
    
    return intent, confidence, top_3_intents

def run_test():
    model, tokenizer, label_encoder, device = load_model_and_tokenizer()
    
    print("=== Intent Recognition System ===")
    print("Type 'exit' to quit\n")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        
        intent, confidence, top_3 = predict_intent(user_input, model, tokenizer, label_encoder, device)
        
        print(f"Intent: {intent}")
        print(f"Confidence: {confidence:.2f}")
        print("Top alternatives:")
        for alt_intent, alt_conf in top_3[1:]:
            print(f"  - {alt_intent}: {alt_conf:.2f}")
        print()

if __name__ == "__main__":
    run_test()