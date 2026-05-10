import tkinter as tk
from tkinter import font as tkfont
import threading
import datetime
import math
import time
import logging
import speech_recognition as sr
import random

try:
    import win32com.client
    import pythoncom
    WIN32_OK = True
except ImportError:
    WIN32_OK = False

try:
    import pyttsx3
    PYTTSX3_OK = True
except ImportError:
    PYTTSX3_OK = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BG_VOID      = "#020408"
BG_DEEP      = "#050d18"
BG_PANEL     = "#071525"
BG_GLASS     = "#0a1f35"
BG_INPUT     = "#0d1b2a"

NEON_BLUE    = "#00d4ff"
NEON_CYAN    = "#00ffea"
NEON_PURPLE  = "#7b2fff"
NEON_PINK    = "#ff2d78"
NEON_GREEN   = "#00ff88"

USER_BG      = "#0d2137"
BOT_BG       = "#071525"

TEXT_BRIGHT  = "#e8f4ff"
TEXT_MID     = "#6a9cc0"
TEXT_DIM     = "#2a4a6a"
TEXT_TIME    = "#1a3a5a"

GRID_COLOR   = "#071d30"
BORDER_GLOW  = "#0a3060"


class HolographicCanvas(tk.Canvas):
    """Animated background with 3D grid, particles and pulse rings."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_VOID, highlightthickness=0, **kwargs)
        self._particles  = []
        self._rings      = []
        self._grid_off   = 0.0
        self._pulse      = 0.0
        self._running    = True
        self._init_particles()
        self._animate()

    def _init_particles(self):
        for _ in range(55):
            self._particles.append({
                "x": random.uniform(0, 1400),
                "y": random.uniform(0, 800),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.4, -0.1),
                "r": random.uniform(1, 3),
                "alpha": random.uniform(0.2, 0.9),
                "color": random.choice([NEON_BLUE, NEON_CYAN, NEON_PURPLE]),
            })

    def _hex_alpha(self, hex_color, alpha):
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        r2 = int(r * alpha + int(BG_VOID[1:3], 16) * (1 - alpha))
        g2 = int(g * alpha + int(BG_VOID[3:5], 16) * (1 - alpha))
        b2 = int(b * alpha + int(BG_VOID[5:7], 16) * (1 - alpha))
        return f"#{r2:02x}{g2:02x}{b2:02x}"

    def _draw_grid(self, w, h):
        step   = 55
        offset = (self._grid_off % step)
        vanish_x, vanish_y = w // 2, h // 2

        for raw_x in range(-step, w + step, step):
            x = raw_x + offset
            alpha = 1 - abs(x - vanish_x) / (w * 0.85)
            alpha = max(0, min(alpha, 1)) * 0.35
            color = self._hex_alpha(NEON_BLUE, alpha)
            self.create_line(x, 0, x, h, fill=color, width=1)

        for raw_y in range(-step, h + step, step):
            y = raw_y + offset * 0.4
            alpha = 1 - abs(y - vanish_y) / (h * 0.85)
            alpha = max(0, min(alpha, 1)) * 0.35
            color = self._hex_alpha(NEON_BLUE, alpha)
            self.create_line(0, y, w, y, fill=color, width=1)

    def _draw_particles(self, w, h):
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["y"] < -5:
                p["y"] = h + 5
                p["x"] = random.uniform(0, w)
            if p["x"] < 0:   p["x"] = w
            if p["x"] > w:   p["x"] = 0
            alpha = p["alpha"] * (0.6 + 0.4 * math.sin(time.time() * 2 + p["x"]))
            color = self._hex_alpha(p["color"], alpha)
            r = p["r"]
            self.create_oval(p["x"]-r, p["y"]-r, p["x"]+r, p["y"]+r,
                             fill=color, outline="")

    def _draw_rings(self, w, h):
        cx, cy = w // 2, h // 2
        for ring in self._rings[:]:
            ring["r"]  += 3
            ring["age"] += 1
            alpha = max(0, 1 - ring["age"] / 60)
            color = self._hex_alpha(NEON_CYAN, alpha * 0.5)
            r = ring["r"]
            self.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=2)
            if ring["age"] > 60:
                self._rings.remove(ring)

    def _draw_scanline(self, w, h):
        y = int((time.time() * 80) % h)
        alpha = 0.06
        color = self._hex_alpha(NEON_CYAN, alpha)
        self.create_rectangle(0, y, w, y + 3, fill=color, outline="")

    def _animate(self):
        if not self._running:
            return
        self.delete("all")
        w = self.winfo_width()  or 1000
        h = self.winfo_height() or 700

        self._grid_off += 0.5
        self._pulse    += 0.04

        self._draw_grid(w, h)
        self._draw_rings(w, h)
        self._draw_particles(w, h)
        self._draw_scanline(w, h)

        self.after(28, self._animate)

    def add_ring(self):
        self._rings.append({"r": 10, "age": 0})

    def stop(self):
        self._running = False


class ChatBubble(tk.Frame):
    def __init__(self, parent, text, sender, timestamp, **kwargs):
        super().__init__(parent, bg=BG_PANEL, **kwargs)
        is_user      = sender == "user"
        bubble_color = USER_BG if is_user else BOT_BG
        anchor_side  = "e" if is_user else "w"
        text_align   = "right" if is_user else "left"
        name_color   = NEON_PINK if is_user else NEON_CYAN
        name_text    = "YOU" if is_user else "AS AGENT"
        border_color = NEON_PINK if is_user else NEON_BLUE

        outer = tk.Frame(self, bg=BG_PANEL)
        outer.pack(fill="x", padx=22, pady=6)

        wrapper = tk.Frame(outer, bg=BG_PANEL)
        wrapper.pack(anchor=anchor_side)

        tk.Label(wrapper, text=name_text, bg=BG_PANEL, fg=name_color,
                 font=("Courier New", 8, "bold")).pack(anchor=anchor_side, padx=6, pady=(0, 2))

        glow = tk.Frame(wrapper, bg=border_color, padx=1, pady=1)
        glow.pack(anchor=anchor_side)

        bubble = tk.Frame(glow, bg=bubble_color, padx=16, pady=12)
        bubble.pack()

        tk.Label(bubble, text=text, bg=bubble_color, fg=TEXT_BRIGHT,
                 font=("Courier New", 10), wraplength=440,
                 justify=text_align, anchor="w").pack()

        tk.Label(wrapper, text=timestamp, bg=BG_PANEL, fg=TEXT_TIME,
                 font=("Courier New", 7)).pack(anchor=anchor_side, padx=6, pady=(2, 0))


class VoiceEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self.ready = True

    def speak(self, text: str):
        threading.Thread(target=self._do_speak, args=(text,), daemon=True).start()

    def _do_speak(self, text: str):
        with self._lock:
            if WIN32_OK:
                try:
                    pythoncom.CoInitialize()
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    voices  = speaker.GetVoices()
                    if voices.Count > 1:
                        speaker.Voice = voices.Item(1)
                    speaker.Rate   = 0
                    speaker.Volume = 100
                    speaker.Speak(text)
                    pythoncom.CoUninitialize()
                    return
                except Exception as e:
                    logger.error(f"win32com error: {e}")
            if PYTTSX3_OK:
                try:
                    eng = pyttsx3.init("sapi5")
                    v   = eng.getProperty("voices")
                    if len(v) > 1:
                        eng.setProperty("voice", v[1].id)
                    eng.setProperty("rate", 170)
                    eng.setProperty("volume", 0.9)
                    eng.say(text)
                    eng.runAndWait()
                    eng.stop()
                except Exception as e:
                    logger.error(f"pyttsx3 error: {e}")


class ASAgentGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AS Agent — Holographic AI")
        self.root.geometry("1050x730")
        self.root.minsize(800, 580)
        self.root.configure(bg=BG_VOID)

        self.agent_ready  = False
        self.agent        = None
        self.voice_engine = VoiceEngine()
        self.listening    = False
        self._blink_state = True

        self._load_agent()
        self._build_ui()
        self._welcome()
        self._blink_cursor()

    
    def _load_agent(self):
        try:
            from inference import ASAgent
            self.agent       = ASAgent()
            self.agent_ready = self.agent.ready
        except Exception as e:
            logger.error(f"Agent load error: {e}")
            self.agent_ready = False

    
    def _build_ui(self):
        self._build_bg()
        self._build_header()
        self._build_chat()
        self._build_input()

    def _build_bg(self):
        self.bg_canvas = HolographicCanvas(self.root)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG_PANEL, height=78)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Frame(hdr, bg=NEON_BLUE, height=1).pack(fill="x", side="top")
        tk.Frame(hdr, bg=NEON_CYAN, height=2).pack(fill="x", side="bottom")

        inner = tk.Frame(hdr, bg=BG_PANEL)
        inner.pack(fill="both", expand=True, padx=28)

        left = tk.Frame(inner, bg=BG_PANEL)
        left.pack(side="left", pady=14)

        tk.Label(left, text="◈", bg=BG_PANEL, fg=NEON_CYAN,
                 font=("Courier New", 22, "bold")).pack(side="left")

        tk.Label(left, text=" AS AGENT", bg=BG_PANEL, fg=NEON_BLUE,
                 font=("Courier New", 20, "bold")).pack(side="left")

        tk.Label(left, text="  /  AI ACADEMIC SYSTEM", bg=BG_PANEL, fg=TEXT_MID,
                 font=("Courier New", 9)).pack(side="left", pady=(6, 0))

        right = tk.Frame(inner, bg=BG_PANEL)
        right.pack(side="right", pady=14)

        self.time_lbl = tk.Label(right, text="", bg=BG_PANEL, fg=TEXT_MID,
                                  font=("Courier New", 9))
        self.time_lbl.pack(side="right", padx=(14, 0))

        sc    = NEON_GREEN if self.agent_ready else NEON_PINK
        st    = "SYS:ONLINE" if self.agent_ready else "SYS:OFFLINE"
        self.status_lbl = tk.Label(right, text=f"● {st}", bg=BG_PANEL, fg=sc,
                                    font=("Courier New", 9, "bold"))
        self.status_lbl.pack(side="right", padx=(0, 8))

        self._update_clock()

    def _build_chat(self):
        wrapper = tk.Frame(self.root, bg=BG_DEEP,
                           highlightthickness=1, highlightbackground=BORDER_GLOW)
        wrapper.pack(fill="both", expand=True, padx=16, pady=(10, 0))

        canvas = tk.Canvas(wrapper, bg=BG_PANEL, highlightthickness=0)
        scroll = tk.Scrollbar(wrapper, orient="vertical", command=canvas.yview,
                              bg=BG_PANEL, troughcolor=BG_DEEP, width=6)
        canvas.configure(yscrollcommand=scroll.set)

        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.chat_frame = tk.Frame(canvas, bg=BG_PANEL)
        self.canvas_win = canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        self.canvas     = canvas

        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(self.canvas_win, width=e.width))
        self.chat_frame.bind("<Configure>",
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def _build_input(self):
        outer = tk.Frame(self.root, bg=BG_VOID)
        outer.pack(fill="x", padx=16, pady=10)

        bar = tk.Frame(outer, bg=BG_INPUT, height=62,
                       highlightthickness=1, highlightbackground=NEON_BLUE)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        self.input_var   = tk.StringVar()
        self.input_field = tk.Entry(
            bar, textvariable=self.input_var,
            bg=BG_INPUT, fg=NEON_CYAN,
            insertbackground=NEON_CYAN,
            relief="flat", bd=0,
            font=("Courier New", 11)
        )
        self.input_field.pack(side="left", fill="both", expand=True, padx=18, pady=16)
        self.input_field.bind("<Return>", lambda e: self._send_text())

        placeholder = "ENTER QUERY..."
        self.input_field.insert(0, placeholder)
        self.input_field.config(fg=TEXT_DIM)

        def focus_in(e):
            if self.input_field.get() == placeholder:
                self.input_field.delete(0, "end")
                self.input_field.config(fg=NEON_CYAN)

        def focus_out(e):
            if not self.input_field.get():
                self.input_field.insert(0, placeholder)
                self.input_field.config(fg=TEXT_DIM)

        self.input_field.bind("<FocusIn>",  focus_in)
        self.input_field.bind("<FocusOut>", focus_out)

        self.mic_btn = tk.Button(
            bar, text="🎙", bg=BG_INPUT, fg=NEON_BLUE,
            activebackground=BG_INPUT, relief="flat", bd=0,
            font=("Segoe UI", 18), cursor="hand2",
            command=self._toggle_voice
        )
        self.mic_btn.pack(side="right", padx=(0, 8), pady=10)

        send_btn = tk.Button(
            bar, text="[ SEND ]",
            bg=BG_DEEP, fg=NEON_BLUE,
            activebackground=NEON_BLUE, activeforeground=BG_VOID,
            relief="flat", bd=0,
            font=("Courier New", 10, "bold"),
            padx=14, pady=6,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
            command=self._send_text
        )
        send_btn.pack(side="right", padx=(0, 10), pady=14)

        self.mic_status = tk.Label(
            outer, text="", bg=BG_VOID, fg=TEXT_MID,
            font=("Courier New", 8)
        )
        self.mic_status.pack(pady=(4, 0))

    #
    def _welcome(self):
        h     = datetime.datetime.now().hour
        greet = "GOOD MORNING" if h < 12 else ("GOOD AFTERNOON" if h < 18 else "GOOD EVENING")
        if self.agent_ready:
            msg = f"{greet}  AS AGENT ONLINE  Ask me anything about Artificial Intelligence."
        else:
            msg = "WARNING: MODEL NOT LOADED. Run train.py first, then restart."
        self._add_bot_message(msg)
        self.voice_engine.speak(msg)

    def _add_user_message(self, text):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        ChatBubble(self.chat_frame, text, "user", ts).pack(fill="x")
        self._scroll_bottom()
        self.bg_canvas.add_ring()

    def _add_bot_message(self, text):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        ChatBubble(self.chat_frame, text, "bot", ts).pack(fill="x")
        self._scroll_bottom()

    def _add_typing(self):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._typing_bubble = ChatBubble(self.chat_frame, "PROCESSING  ▌", "bot", ts)
        self._typing_bubble.pack(fill="x")
        self._scroll_bottom()

    def _remove_typing(self):
        if hasattr(self, "_typing_bubble"):
            self._typing_bubble.destroy()

    def _scroll_bottom(self):
        self.root.after(60, lambda: self.canvas.yview_moveto(1.0))

  
    def _send_text(self):
        text = self.input_var.get().strip()
        if not text or text == "ENTER QUERY...":
            return
        self.input_var.set("")
        self._process(text)

    def _process(self, text):
        self._add_user_message(text)
        self._add_typing()
        threading.Thread(target=self._get_response, args=(text,), daemon=True).start()

    def _get_response(self, text):
        time.sleep(0.35)
        if self.agent_ready:
            try:
                response, _ = self.agent.predict(text)
            except Exception as e:
                response = f"SYSTEM ERROR: {e}"
        else:
            response = "MODEL OFFLINE. Run train.py first."

        self.root.after(0, self._remove_typing)
        self.root.after(60,  lambda: self._add_bot_message(response))
        self.root.after(200, lambda: self.voice_engine.speak(response))

    
    def _toggle_voice(self):
        if self.listening:
            return
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        self.listening = True
        self.root.after(0, lambda: self.mic_btn.config(fg=NEON_PINK))
        self.root.after(0, lambda: self.mic_status.config(
            text="◉ AUDIO INPUT ACTIVE — SPEAK NOW", fg=NEON_PINK))
        self.bg_canvas.add_ring()

        recognizer = sr.Recognizer()
        recognizer.energy_threshold        = 200
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold          = 1.2
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
                self.root.after(0, lambda: self.mic_status.config(
                    text="READY — SPEAK NOW", fg=NEON_GREEN))
                audio = recognizer.listen(source, timeout=15, phrase_time_limit=15)
            self.root.after(0, lambda: self.mic_status.config(
                text=" PROCESSING AUDIO...", fg=NEON_BLUE))
            text = recognizer.recognize_google(audio, language="en-US")
            self.root.after(0, lambda: self.mic_status.config(
                text=f" INPUT: {text}", fg=NEON_GREEN))
            self.root.after(0, lambda: self._process(text))
        except sr.WaitTimeoutError:
            self.root.after(0, lambda: self.mic_status.config(
                text="TIMEOUT — CLICK MIC AND TRY AGAIN", fg=TEXT_MID))
        except sr.UnknownValueError:
            self.root.after(0, lambda: self.mic_status.config(
                text="COULD NOT UNDERSTAND — TRY AGAIN", fg=TEXT_MID))
        except sr.RequestError as e:
            self.root.after(0, lambda: self.mic_status.config(
                text=f"NETWORK ERROR: {e}", fg=NEON_PINK))
        except Exception as e:
            self.root.after(0, lambda: self.mic_status.config(
                text=f"ERROR: {e}", fg=NEON_PINK))
        finally:
            self.listening = False
            self.root.after(0, lambda: self.mic_btn.config(fg=NEON_BLUE))
            self.root.after(4000, lambda: self.mic_status.config(text=""))

   
    def _blink_cursor(self):
        self._blink_state = not self._blink_state
        self.root.after(600, self._blink_cursor)

    def _update_clock(self):
        now = datetime.datetime.now()
        self.time_lbl.configure(
            text=now.strftime("DATE:%Y.%m.%d  TIME:%H:%M:%S")
        )
        self.root.after(1000, self._update_clock)

    def run(self):
        self.root.mainloop()
        self.bg_canvas.stop()


if __name__ == "__main__":
    app = ASAgentGUI()
    app.run()