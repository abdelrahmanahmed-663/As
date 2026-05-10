import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import threading
import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import json
import pickle
import random
import os
import sys
from PIL import Image, ImageDraw, ImageTk
import numpy as np
import win32com.client

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg_main": "#0d0d12",
    "bg_sidebar": "#13131a",
    "bg_card": "#1c1c24",
    "accent_primary": "#6366f1",
    "accent_secondary": "#8b5cf6",
    "accent_success": "#10b981",
    "accent_warning": "#f59e0b",
    "text_main": "#f3f4f6",
    "text_dim": "#9ca3af",
    "border": "#2d2d3a"
}

class TrainTestPanel(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Training Console")
        self.geometry("900x650")
        self.configure(fg_color=COLORS["bg_main"])
        
        main = ctk.CTkFrame(self, fg_color=COLORS["bg_main"])
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        notebook = ctk.CTkTabview(main, fg_color=COLORS["bg_card"], segmented_button_fg_color=COLORS["bg_sidebar"])
        notebook.pack(fill="both", expand=True)
        
        notebook.add("Training")
        notebook.add("Testing")
        notebook.add("Intents Editor")
        
        self._build_train_tab(notebook.tab("Training"))
        self._build_test_tab(notebook.tab("Testing"))
        self._build_intents_tab(notebook.tab("Intents Editor"))
    
    def _build_train_tab(self, parent):
        header = ctk.CTkLabel(parent, text="Model Training", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS["accent_primary"])
        header.pack(pady=15)
        
        self.train_log = scrolledtext.ScrolledText(parent, height=18, bg=COLORS["bg_main"], fg=COLORS["accent_success"], font=("Consolas", 10), relief="flat")
        self.train_log.pack(fill="both", expand=True, padx=20, pady=10)
        
        btn = ctk.CTkButton(parent, text="Start Training", width=180, height=40, fg_color=COLORS["accent_primary"], hover_color=COLORS["accent_secondary"], command=self._start_training)
        btn.pack(pady=10)
    
    def _build_test_tab(self, parent):
        ctk.CTkLabel(parent, text="Interactive Testing", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS["accent_success"]).pack(pady=15)
        
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=10)
        
        self.test_input = ctk.CTkEntry(row, placeholder_text="Enter text to test...", height=40)
        self.test_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.test_input.bind("<Return>", lambda e: self._run_test())
        
        ctk.CTkButton(row, text="Test", width=100, height=40, fg_color=COLORS["accent_success"], command=self._run_test).pack(side="right")
        
        self.test_log = scrolledtext.ScrolledText(parent, height=12, bg=COLORS["bg_main"], fg=COLORS["text_main"], font=("Consolas", 10), relief="flat")
        self.test_log.pack(fill="both", expand=True, padx=20, pady=10)
    
    def _build_intents_tab(self, parent):
        ctk.CTkLabel(parent, text="Intents Configuration", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS["accent_warning"]).pack(pady=15)
        
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(btn_frame, text="Load File", width=120, fg_color=COLORS["accent_warning"], command=self._load_intents).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Save", width=120, fg_color=COLORS["accent_success"], command=self._save_intents).pack(side="left", padx=5)
        
        self.intents_box = scrolledtext.ScrolledText(parent, bg=COLORS["bg_main"], fg=COLORS["text_main"], font=("Consolas", 10), relief="flat")
        self.intents_box.pack(fill="both", expand=True, padx=20, pady=10)
        
        if os.path.exists("intents.json"):
            with open("intents.json", "r", encoding="utf-8") as f:
                self.intents_box.insert("1.0", f.read())
    
    def _start_training(self):
        self.train_log.delete("1.0", tk.END)
        self._log_train("Starting training process...\n")
        threading.Thread(target=self._run_training, daemon=True).start()
    
    def _run_training(self):
        try:
            import subprocess
            result = subprocess.run([sys.executable, "train_model.py"], capture_output=True, text=True)
            self._log_train(result.stdout)
            if result.stderr:
                self._log_train(f"Errors:\n{result.stderr}")
            self._log_train("\nTraining completed successfully!")
            if hasattr(self.master, 'agent'):
                self.master.agent.load_model()
        except Exception as e:
            self._log_train(f"Error: {str(e)}")
    
    def _run_test(self):
        text = self.test_input.get().strip()
        if not text:
            return
        self.test_input.delete(0, tk.END)
        self._log_test(f">>> {text}\n")
        if hasattr(self.master, 'agent') and self.master.agent.model_ready:
            response = self.master.agent.get_response(text)
            self._log_test(f"Response: {response}\n\n")
        else:
            self._log_test("Model not ready. Please train first.\n\n")
    
    def _load_intents(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.intents_box.delete("1.0", tk.END)
                self.intents_box.insert("1.0", f.read())
    
    def _save_intents(self):
        content = self.intents_box.get("1.0", tk.END)
        try:
            json.loads(content)
            with open("intents.json", "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Success", "Intents saved successfully!")
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON: {str(e)}")
    
    def _log_train(self, msg):
        self.after(0, lambda: (self.train_log.insert(tk.END, msg), self.train_log.see(tk.END)))
    
    def _log_test(self, msg):
        self.after(0, lambda: (self.test_log.insert(tk.END, msg), self.test_log.see(tk.END)))

class ASAgent:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("ASIST")
        self.root.geometry("1100x720")
        self.root.configure(fg_color=COLORS["bg_main"])
        self.root.agent = self
        
        self.model = None
        self.vectorizer = None
        self.label_encoder = None
        self.intents_data = None
        self.model_ready = False
        self.tts_engine = None
        self.listening = False
        
        self.load_model()
        self._init_tts()
        self._setup_ui()
        self._update_time()
        self._welcome_message()
    
    def _init_tts(self):
        try:
            self.tts_engine = win32com.client.Dispatch("SAPI.SpVoice")
            self.tts_engine.Rate = 1
        except:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 170)
            except:
                self.tts_engine = None
    
    def speak(self, text):
        if not self.tts_engine:
            return
        def _speak():
            try:
                if isinstance(self.tts_engine, win32com.client.CDispatch):
                    self.tts_engine.Speak(text)
                else:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
            except:
                pass
        threading.Thread(target=_speak, daemon=True).start()
    
    def load_model(self):
        try:
            with open("best_model.pkl", "rb") as f:
                self.model = pickle.load(f)
            with open("vectorizer.pkl", "rb") as f:
                self.vectorizer = pickle.load(f)
            with open("label_encoder.pkl", "rb") as f:
                self.label_encoder = pickle.load(f)
            with open("intents.json", "r", encoding="utf-8") as f:
                self.intents_data = json.load(f)
            self.model_ready = True
            return True
        except:
            self.model_ready = False
            return False
    
    def _setup_ui(self):
        main_container = ctk.CTkFrame(self.root, fg_color=COLORS["bg_main"])
        main_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        sidebar = ctk.CTkFrame(main_container, width=260, fg_color=COLORS["bg_sidebar"], corner_radius=15)
        sidebar.pack(side="left", fill="y", padx=(0, 15))
        sidebar.pack_propagate(False)
        
        ctk.CTkLabel(sidebar, text="ASIST", font=ctk.CTkFont(family="Arial", size=28, weight="bold"), text_color=COLORS["accent_primary"]).pack(pady=(30, 10))
        ctk.CTkLabel(sidebar, text="AI Assistant", font=ctk.CTkFont(size=12), text_color=COLORS["text_dim"]).pack(pady=(0, 30))
        
        status_frame = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_card"], corner_radius=10)
        status_frame.pack(fill="x", padx=15, pady=10)
        status_text = "● Online" if self.model_ready else "● Offline"
        status_color = COLORS["accent_success"] if self.model_ready else COLORS["accent_warning"]
        ctk.CTkLabel(status_frame, text=status_text, font=ctk.CTkFont(size=11), text_color=status_color).pack(pady=8)
        
        btn_style = {"height": 42, "corner_radius": 10, "font": ctk.CTkFont(size=12)}
        
        ctk.CTkButton(sidebar, text="🎤 Voice Input", fg_color=COLORS["accent_secondary"], hover_color="#7c3aed", command=self._voice_input, **btn_style).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(sidebar, text="⚙️ Training Center", fg_color=COLORS["bg_card"], hover_color=COLORS["border"], command=self._open_train_test, **btn_style).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(sidebar, text="🗑️ Clear Chat", fg_color=COLORS["bg_card"], hover_color=COLORS["border"], command=self._clear_chat, **btn_style).pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(sidebar, text=f"© 2024", font=ctk.CTkFont(size=10), text_color=COLORS["text_dim"]).pack(side="bottom", pady=20)
        
        chat_area = ctk.CTkFrame(main_container, fg_color=COLORS["bg_card"], corner_radius=15)
        chat_area.pack(side="right", fill="both", expand=True)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_area, wrap=tk.WORD, font=("Segoe UI", 11),
            bg=COLORS["bg_card"], fg=COLORS["text_main"],
            relief="flat", padx=20, pady=15, insertbackground=COLORS["accent_primary"]
        )
        self.chat_display.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.chat_display.tag_config("user", foreground=COLORS["accent_primary"], font=("Segoe UI", 11, "bold"))
        self.chat_display.tag_config("bot", foreground=COLORS["accent_success"], font=("Segoe UI", 11))
        self.chat_display.tag_config("system", foreground=COLORS["accent_warning"], font=("Segoe UI", 10, "italic"))
        
        input_frame = ctk.CTkFrame(chat_area, fg_color="transparent", height=70)
        input_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.input_field = ctk.CTkEntry(input_frame, placeholder_text="Type your message...", height=45, font=ctk.CTkFont(size=13), fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.input_field.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_field.bind("<Return>", lambda e: self._process_input())
        
        ctk.CTkButton(input_frame, text="Send", width=90, height=45, fg_color=COLORS["accent_primary"], hover_color=COLORS["accent_secondary"], command=self._process_input).pack(side="right")
        
        self.time_label = ctk.CTkLabel(sidebar, text="", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"])
        self.time_label.pack(side="bottom", pady=15)
    
    def _update_time(self):
        self.time_label.configure(text=datetime.datetime.now().strftime("%I:%M %p"))
        self.root.after(1000, self._update_time)
    
    def _welcome_message(self):
        hour = datetime.datetime.now().hour
        if hour < 12: greeting = "Good morning"
        elif hour < 18: greeting = "Good afternoon"
        else: greeting = "Good evening"
        
        msg = f"{greeting}! I'm ASIST, your assistant. How can I help today?"
        self._add_message(msg, "bot")
        self.speak(msg)
    
    def _add_message(self, text, sender):
        if sender == "user":
            self.chat_display.insert(tk.END, f"YOU: {text}\n", "user")
        elif sender == "bot":
            self.chat_display.insert(tk.END, f"ASIST: {text}\n\n", "bot")
        else:
            self.chat_display.insert(tk.END, f"[{text}]\n", "system")
        self.chat_display.see(tk.END)
    
    def _clear_chat(self):
        self.chat_display.delete("1.0", tk.END)
        self._add_message("Chat cleared", "system")
    
    def get_response(self, text):
        if not self.model_ready:
            return "Model not trained yet. Please train from the Training Center."
        
        try:
            text_vec = self.vectorizer.transform([text.lower()])
            pred = self.model.predict(text_vec)[0]
            tag = self.label_encoder.inverse_transform([pred])[0]
            
            for intent in self.intents_data["intents"]:
                if intent["tag"] == tag:
                    return random.choice(intent["responses"])
            return "I'm not sure how to respond to that."
        except:
            return "Sorry, I encountered an error."
    
    def _process_input(self):
        text = self.input_field.get().strip()
        if not text:
            return
        
        self.input_field.delete(0, tk.END)
        self._add_message(text, "user")
        
        cmd = text.lower()
        
        if cmd in ["time", "what time"]:
            response = f"It's {datetime.datetime.now().strftime('%I:%M %p')}"
        elif cmd in ["date", "what date"]:
            response = f"Today is {datetime.datetime.now().strftime('%B %d, %Y')}"
        elif "open " in cmd:
            sites = {"google": "https://google.com", "youtube": "https://youtube.com", "github": "https://github.com"}
            found = False
            for name, url in sites.items():
                if name in cmd:
                    webbrowser.open(url)
                    response = f"Opening {name}"
                    found = True
                    break
            if not found:
                response = "Website not recognized"
        else:
            response = self.get_response(text)
        
        self._add_message(response, "bot")
        self.speak(response)
    
    def _voice_input(self):
        if self.listening:
            return
        
        def listen():
            self.listening = True
            self._add_message("Listening...", "system")
            
            try:
                recognizer = sr.Recognizer()
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=6)
                
                text = recognizer.recognize_google(audio)
                self._add_message(f"Heard: {text}", "system")
                self.root.after(0, lambda: self._process_voice_text(text))
            except sr.WaitTimeoutError:
                self._add_message("No speech detected", "system")
            except sr.UnknownValueError:
                self._add_message("Could not understand audio", "system")
            except Exception as e:
                self._add_message(f"Voice error: {str(e)}", "system")
            finally:
                self.listening = False
        
        threading.Thread(target=listen, daemon=True).start()
    
    def _process_voice_text(self, text):
        self._add_message(text, "user")
        
        cmd = text.lower()
        
        if cmd in ["time", "what time"]:
            response = f"It's {datetime.datetime.now().strftime('%I:%M %p')}"
        elif cmd in ["date", "what date"]:
            response = f"Today is {datetime.datetime.now().strftime('%B %d, %Y')}"
        else:
            response = self.get_response(text)
        
        self._add_message(response, "bot")
        self.speak(response)
    
    def _open_train_test(self):
        TrainTestPanel(self.root)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ASAgent()
    app.run() 