import json
import pickle
import random
import logging
import torch
import torch.nn.functional as F

from preprocess import clean_text
from model import load_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("inference.log")
    ]
)
logger = logging.getLogger(__name__)

MODEL_DIR      = "as_agent_model"
ENCODER_PATH   = "label_encoder.pkl"
RESPONSES_PATH = "responses.json"
CONFIDENCE_THR = 0.60
MAX_LEN        = 64

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

FALLBACK_RESPONSES = [
    "I didn't quite understand that. Could you rephrase?",
    "I'm not sure I understand. Can you ask in a different way?",
    "That's outside my current knowledge. Try asking about AI topics!"
]


class ASAgent:
    def __init__(self):
        self.model      = None
        self.tokenizer  = None
        self.label_enc  = None
        self.responses  = None
        self.last_input = None
        self.ready      = False
        self._load()

    def _load(self):
        try:
            self.model, self.tokenizer = load_model(MODEL_DIR)
            self.model.to(device)
            self.model.eval()

            with open(ENCODER_PATH, "rb") as f:
                self.label_enc = pickle.load(f)

            with open(RESPONSES_PATH, "r", encoding="utf-8") as f:
                self.responses = json.load(f)

            self.ready = True
            logger.info("AS Agent ready.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.error("Please run train.py first.")

    def predict(self, text: str) -> tuple[str, float]:
        if not self.ready:
            return "Model not loaded. Please train first.", 0.0

        cmd_response = self._handle_commands(text)
        if cmd_response:
            return cmd_response, 1.0

        try:
            self.last_input = text
            cleaned = clean_text(text)

            enc = self.tokenizer(
                cleaned,
                truncation=True,
                padding="max_length",
                max_length=MAX_LEN,
                return_tensors="pt"
            )
            ids  = enc["input_ids"].to(device)
            mask = enc["attention_mask"].to(device)

            with torch.no_grad():
                out   = self.model(ids, attention_mask=mask)
                probs = F.softmax(out.logits, dim=1)
                conf  = probs.max().item()
                idx   = probs.argmax().item()

            intent = self.label_enc.inverse_transform([idx])[0]
            logger.debug(f"Input: '{text}' → Intent: '{intent}' | Confidence: {conf:.2%}")

            if conf < CONFIDENCE_THR:
                return random.choice(FALLBACK_RESPONSES), conf

            responses = self.responses.get(intent, FALLBACK_RESPONSES)
            return random.choice(responses), conf

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return "An error occurred. Please try again.", 0.0

    def _handle_commands(self, text: str) -> str | None:
        import webbrowser, os, datetime, pyautogui

        cmd = text.lower().strip()
        words = set(cmd.split())

        web = {
            "open google":     "https://google.com",
            "open youtube":    "https://youtube.com",
            "open github":     "https://github.com",
            "open facebook":   "https://facebook.com",
            "open whatsapp":   "https://web.whatsapp.com",
            "open discord":    "https://discord.com",
            "open linkedin":   "https://linkedin.com",
            "open twitter":    "https://twitter.com",
            "open university": "https://eru.edu.eg",
        }
        for key, url in web.items():
            if key in cmd:
                webbrowser.open(url)
                return f"Opening {key.replace('open ', '').title()}."

        apps = {
            "open notepad":    "notepad.exe",
            "open calculator": "calc.exe",
            "open paint":      "mspaint.exe",
        }
        for key, exe in apps.items():
            if key in cmd:
                os.system(exe)
                return f"Opening {key.replace('open ', '').title()}."

        close_apps = {
            "close notepad":    "taskkill /f /im notepad.exe",
            "close calculator": "taskkill /f /im calculator.exe 2>nul",
            "close paint":      "taskkill /f /im mspaint.exe",
        }
        for key, kill_cmd in close_apps.items():
            if key in cmd:
                os.system(kill_cmd)
                return f"Closed {key.replace('close ', '').title()}."

        if cmd in ["volume up", "increase volume"]:
            pyautogui.press("volumeup"); return "Volume increased."
        if cmd in ["volume down", "decrease volume"]:
            pyautogui.press("volumedown"); return "Volume decreased."
        if cmd in ["mute", "mute volume"]:
            pyautogui.press("volumemute"); return "Muted."

        if cmd in ["time", "what time", "what is the time", "what time is it", "current time"]:
            return f"The time is {datetime.datetime.now().strftime('%I:%M %p')}."
        if cmd in ["date", "what date", "what is the date", "today date", "what is today"]:
            return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."
        if cmd in ["day", "what day", "what day is it"]:
            return f"Today is {datetime.datetime.now().strftime('%A')}."

        if any(w in cmd for w in ["schedule", "my class", "my lecture", "today class"]):
            schedule = {
                "monday":    "Computer Graphics at 9:00 AM",
                "tuesday":   "Data Science at 9:00 AM",
                "wednesday": "Artificial Intelligence at 9:00 AM",
                "thursday":  "Pattern Recognition at 9:00 AM",
                "friday":    "No classes today, enjoy!",
                "saturday":  "Natural Language Processing at 9:00 AM",
                "sunday":    "Computer Vision at 9:00 AM",
            }
            day = datetime.datetime.today().strftime("%A").lower()
            return schedule.get(day, "No schedule found.")

        if any(w in cmd for w in ["who made you", "who created you", "your creator", "who built you"]):
            return "I am AS Agent, created by Abdelrahman Ahmed, a Computer Science student at the Egyptian Russian University."

        if cmd in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]:
            import random
            return random.choice(["Hello! How can I help you?", "Hey! Ask me anything about AI.", "Hi there! Ready to assist."])

        if cmd in ["how are you", "how are you doing"]:
            return "im fine! Ready to help you with AI topics."

        if cmd in ["thank you", "thanks", "thank you so much"]:
            return "You are welcome! Feel free to ask more."

        if cmd in ["bye", "goodbye", "see you"]:
            return "Goodbye! Keep learning AI!"

        return None

    def chat(self, text: str) -> str:
        response, conf = self.predict(text)
        return response


if __name__ == "__main__":
    agent = ASAgent()
    if not agent.ready:
        print("Run train.py first!")
        exit()

    
    print("  AS Agent — Chat Mode  (type 'quit' to exit)")
    

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "bye"):
                print("AS Agent: Goodbye! Keep learning AI!")
                break
            response, conf = agent.predict(user_input)
            print(f"AS Agent: {response}")
            print(f"          [confidence: {conf:.1%}]\n")
        except KeyboardInterrupt:
            print("\nAS Agent: Goodbye!")
            break