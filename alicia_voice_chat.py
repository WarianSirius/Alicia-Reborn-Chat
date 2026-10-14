import tkinter as tk
from tkinter import ttk, messagebox
import threading, json, urllib.request, webbrowser, ctypes
from pathlib import Path
import sounddevice as sd
import numpy as np
import keyboard, pyautogui, pyperclip, psutil
from faster_whisper import WhisperModel

VERSION = "1.2.0"
API = "https://api.github.com/repos/WarianSirius/Alicia-Reborn-Chat/releases/latest"
SETTINGS = Path.home() / "AppData/Roaming/AliciaVoiceChat/settings.json"

def windows():
    import ctypes.wintypes
    user32 = ctypes.windll.user32
    items = []
    def callback(hwnd, unused):
        if not user32.IsWindowVisible(hwnd): return True
        n = user32.GetWindowTextLengthW(hwnd)
        if not n: return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try: process = psutil.Process(pid.value).name()
        except Exception: process = "unknown"
        items.append((hwnd, buf.value, process))
        return True
    cb = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)(callback)
    user32.EnumWindows(cb, 0)
    return items

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Alicia Voice Chat " + VERSION)
        self.root.geometry("480x290")
        try: self.settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
        except Exception: self.settings = {}
        self.recording = False
        self.audio = []
        self.stream = None
        self.model = None
        self.busy = False
        self.target = self.settings.get("target", "")
        self.device = self.settings.get("device")
        self.auto = tk.BooleanVar(value=self.settings.get("auto", False))
        ttk.Label(self.root, text="Alicia Voice Chat", font=("Segoe UI", 17, "bold")).pack(pady=10)
        ttk.Label(self.root, text="F8 = Aufnahme starten / stoppen").pack()
        ttk.Button(self.root, text="Einstellungen (Mikrofon und Spielfenster)", command=self.configure).pack(pady=9)
        ttk.Checkbutton(self.root, text="Erkannten Text automatisch in den Chat senden", variable=self.auto, command=self.save).pack()
        ttk.Button(self.root, text="Auf Updates prüfen", command=lambda: threading.Thread(target=self.updates, daemon=True).start()).pack(pady=9)
        self.status = tk.StringVar(value="Bereit. F8 drücken.")
        ttk.Label(self.root, textvariable=self.status, wraplength=450).pack(pady=5)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        keyboard.add_hotkey("f8", lambda: self.root.after(0, self.toggle))
    def say(self, text):
        self.root.after(0, lambda: self.status.set(text))
    def save(self):
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS.write_text(json.dumps({"target":self.target,"device":self.device,"auto":self.auto.get()},indent=2),encoding="utf-8")
    def configure(self):
        win = tk.Toplevel(self.root)
        win.title("Einstellungen")
        win.geometry("570x260")
        ttk.Label(win,text="Mikrofon").pack(pady=4)
        devices = [(i, d["name"]) for i,d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
        mic = ttk.Combobox(win, state="readonly", values=[f"{i}: {name}" for i,name in devices], width=65)
        mic.pack()
        if devices:
            idx = next((k for k,(i,_) in enumerate(devices) if i == self.device),0)
            mic.current(idx)
        ttk.Label(win,text="Spielfenster (Spiel zuerst starten)").pack(pady=8)
        wins = windows()
        choices = [f"{name} — {proc} (HWND {hwnd})" for hwnd,name,proc in wins]
        selected = ttk.Combobox(win, state="readonly", values=choices, width=65)
        selected.pack()
        for k,(hwnd,name,proc) in enumerate(wins):
            if self.target and self.target == proc: selected.current(k); break
        def save():
            if mic.current() >= 0: self.device = devices[mic.current()][0]
            if selected.current() >= 0: self.target = wins[selected.current()][2]
            self.save()
            win.destroy()
            self.say("Einstellungen gespeichert.")
        ttk.Button(win,text="Speichern",command=save).pack(pady=15)
    def toggle(self):
        if self.busy: return
        if self.recording:
            self.recording = False
            try: self.stream.stop(); self.stream.close()
            except Exception: pass
            self.stream = None
            self.busy = True
            self.say("Erkenne Sprache ...")
            threading.Thread(target=self.transcribe, daemon=True).start()
        else:
            self.audio = []
            try:
                self.stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32", device=self.device, callback=lambda data, frames, time, status: self.audio.append(data.copy()))
                self.stream.start()
                self.recording = True
                self.say("Aufnahme läuft. F8 zum Stoppen.")
            except Exception as exc: messagebox.showerror("Mikrofon",str(exc))
    def transcribe(self):
        try:
            if not self.audio: self.say("Keine Aufnahme."); return
            if self.model is None:
                self.say("Sprachmodell wird geladen (beim ersten Mal dauert es).")
                self.model = WhisperModel("base", device="cpu", compute_type="int8")
            samples = np.concatenate(self.audio).reshape(-1)
            segments, info = self.model.transcribe(samples, language="de", vad_filter=True)
            text = " ".join(s.text.strip() for s in segments).strip()
            if not text: self.say("Keine Sprache erkannt."); return
            self.say("Erkannt: " + text[:160])
            if self.auto.get(): self.send(text)
        except Exception as exc: self.say("Fehler: " + str(exc))
        finally: self.busy = False
    def send(self, text):
        try:
            foreground = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(foreground, ctypes.byref(pid))
            current = psutil.Process(pid.value).name()
            if not self.target or current.lower() != self.target.lower():
                self.say("Text erkannt, aber Alicia ist nicht im Vordergrund. Spielfenster in Einstellungen wählen.")
                return
            pyautogui.press("enter")
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl","v")
            pyautogui.press("enter")
            self.say("Chat-Eingabe versucht: " + text[:120])
        except Exception as exc: self.say("Chat-Fehler: " + str(exc))
    def updates(self):
        try:
            req = urllib.request.Request(API,headers={"User-Agent":"AliciaVoiceChat"})
            with urllib.request.urlopen(req,timeout=12) as resp: data = json.load(resp)
            latest = data.get("tag_name","").lstrip("v")
            if latest == VERSION: self.say("Du hast die aktuelle Version."); return
            url = next((a["browser_download_url"] for a in data.get("assets",[]) if a["name"] == "AliciaVoiceChat_Setup.exe"),None)
            if not url: self.say("Keine neue Setup.exe veröffentlicht."); return
            def ask():
                if messagebox.askyesno("Update",f"Version {latest} verfügbar. Setup herunterladen?"): webbrowser.open(url)
            self.root.after(0,ask)
        except Exception as exc: self.say("Update-Prüfung fehlgeschlagen: " + str(exc))
    def close(self):
        try: keyboard.unhook_all_hotkeys()
        except Exception: pass
        if self.stream:
            try: self.stream.stop(); self.stream.close()
            except Exception: pass
        self.root.destroy()
    def run(self): self.root.mainloop()

if __name__ == "__main__": App().run()
