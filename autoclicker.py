import json
import os
import tkinter as tk
from tkinter import messagebox, ttk
from pynput.mouse import Controller, Button
from pynput import keyboard
import threading
import time

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")


class AutoclickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Autoclicker Pro")
        self.root.geometry("450x700")
        self.root.resizable(False, False)
        
        # Styling
        self.style = ttk.Style()
        self.style.configure('TButton', padding=5, font=('Helvetica', 10))
        self.style.configure('TLabel', font=('Helvetica', 10))

        # Main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        self.label = ttk.Label(self.main_frame, text="Portable Autoclicker Pro", font=("Helvetica", 20))
        self.label.pack(pady=10)

        # Status indicator
        self.status_var = tk.StringVar(value="Status: Idle")
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=5)

        # Click counter
        self.click_count = 0
        self.counter_var = tk.StringVar(value="Clicks: 0")
        self.counter_label = ttk.Label(self.main_frame, textvariable=self.counter_var,
                                      font=("Helvetica", 12, "bold"))
        self.counter_label.pack(pady=5)

        # Position frame
        self.position_frame = ttk.LabelFrame(self.main_frame, text="Click Position", padding="5")
        self.position_frame.pack(fill=tk.X, pady=5)

        self.position_var = tk.StringVar(value="Not set - will click at current mouse position")
        self.position_label = ttk.Label(self.position_frame, textvariable=self.position_var)
        self.position_label.pack(pady=5)

        ttk.Label(self.position_frame, text="Press F8 to record position (with 3s countdown)",
                 font=("Helvetica", 9, "italic"), foreground="blue").pack(pady=2)

        self.pos_button_frame = ttk.Frame(self.position_frame)
        self.pos_button_frame.pack(fill=tk.X, pady=5)

        self.clear_pos_button = ttk.Button(self.pos_button_frame, text="Clear Position",
                                          command=self.clear_position)
        self.clear_pos_button.pack(padx=5, expand=True)

        self.saved_position = None
        self.recording_position = False

        self.settings = self.load_settings()

        # Delay frame
        self.delay_frame = ttk.LabelFrame(self.main_frame, text="Delay Settings", padding="5")
        self.delay_frame.pack(fill=tk.X, pady=5)

        self.delay_label = ttk.Label(self.delay_frame, text="Delay (seconds):")
        self.delay_label.pack(side=tk.LEFT, padx=5)

        self.delay_entry = ttk.Entry(self.delay_frame, width=10)
        self.delay_entry.pack(side=tk.LEFT, padx=5)
        self.delay_entry.insert(0, str(self.settings.get("delay", "1.0")))
        self.delay_entry.bind("<FocusOut>", self.on_delay_changed)
        self.delay_entry.bind("<Return>", self.on_delay_changed)

        # Autoclicker frame
        self.click_frame = ttk.LabelFrame(self.main_frame, text="Autoclicker", padding="5")
        self.click_frame.pack(fill=tk.X, pady=5)

        self.start_button = ttk.Button(self.click_frame, text="Start Clicking", 
                                     command=self.start_autoclicking)
        self.start_button.pack(side=tk.LEFT, padx=5, expand=True)

        self.stop_button = ttk.Button(self.click_frame, text="Stop Clicking", 
                                    command=self.stop_autoclicking)
        self.stop_button.pack(side=tk.LEFT, padx=5, expand=True)

        # Hotkey info
        self.hotkey_frame = ttk.LabelFrame(self.main_frame, text="Hotkeys", padding="5")
        self.hotkey_frame.pack(fill=tk.X, pady=5)

        ttk.Label(self.hotkey_frame, text="F6: Start | F7: Stop | F8: Record Position",
                 font=("Helvetica", 10, "italic")).pack()

        # Always on top checkbox
        self.topmost_var = tk.BooleanVar(value=self.settings.get("always_on_top", True))
        self.topmost_check = ttk.Checkbutton(self.main_frame, text="Always on Top",
                                            variable=self.topmost_var,
                                            command=self.toggle_topmost)
        self.topmost_check.pack(pady=5)
        self.root.attributes('-topmost', self.topmost_var.get())

        # Footer
        self.footer_frame = ttk.Frame(self.main_frame)
        self.footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        ttk.Label(self.footer_frame, text="Made by Sh00tsn00ds",
                 font=("Helvetica", 9, "bold")).pack()
        ttk.Label(self.footer_frame, text="\"Productivity is overrated anyway\" 😎",
                 font=("Helvetica", 8, "italic"), foreground="gray").pack()

        # Initialize controllers
        self.mouse = Controller()
        self.running = False
        self.autoclicking = False
        self.click_thread = None

        saved_position = self.settings.get("saved_position")
        if (
            isinstance(saved_position, list)
            and len(saved_position) == 2
            and all(isinstance(coord, int) for coord in saved_position)
        ):
            self.saved_position = tuple(saved_position)
            self.position_var.set(f"Position: X={self.saved_position[0]}, Y={self.saved_position[1]}")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Setup global hotkeys
        self.setup_hotkeys()

    def load_settings(self):
        defaults = {
            "delay": "1.0",
            "always_on_top": True,
            "saved_position": None,
        }

        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as settings_file:
                data = json.load(settings_file)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return defaults

        if not isinstance(data, dict):
            return defaults

        settings = defaults.copy()

        delay = data.get("delay")
        if isinstance(delay, str):
            settings["delay"] = delay
        elif isinstance(delay, (int, float)):
            settings["delay"] = str(delay)

        always_on_top = data.get("always_on_top")
        if isinstance(always_on_top, bool):
            settings["always_on_top"] = always_on_top

        saved_position = data.get("saved_position")
        if (
            isinstance(saved_position, list)
            and len(saved_position) == 2
            and all(isinstance(coord, int) for coord in saved_position)
        ):
            settings["saved_position"] = saved_position

        return settings

    def save_settings(self):
        settings = {
            "delay": self.delay_entry.get().strip() or "1.0",
            "always_on_top": self.topmost_var.get(),
            "saved_position": list(self.saved_position) if self.saved_position else None,
        }

        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as settings_file:
                json.dump(settings, settings_file, indent=2)
        except OSError:
            pass

    def on_delay_changed(self, _event=None):
        self.save_settings()

    def on_close(self):
        self.save_settings()
        self.root.destroy()

    def toggle_topmost(self):
        self.root.attributes('-topmost', self.topmost_var.get())
        self.save_settings()

    def record_position(self):
        if self.recording_position:
            return
        
        self.recording_position = True
        
        def countdown_and_record():
            # Countdown
            for i in range(3, 0, -1):
                self.root.after(0, lambda count=i: self.position_var.set(f"Recording in {count}..."))
                time.sleep(1)
            
            # Record position
            current_pos = self.mouse.position
            self.saved_position = current_pos
            self.root.after(0, lambda: self.position_var.set(f"Position: X={current_pos[0]}, Y={current_pos[1]}"))
            self.root.after(0, self.save_settings)
            self.root.after(0, lambda: messagebox.showinfo("Position Recorded",
                          f"Position recorded at X={current_pos[0]}, Y={current_pos[1]}"))
            
            self.recording_position = False
        
        thread = threading.Thread(target=countdown_and_record, daemon=True)
        thread.start()

    def clear_position(self):
        self.saved_position = None
        self.position_var.set("Not set - will click at current mouse position")
        self.save_settings()

    def setup_hotkeys(self):
        def on_press(key):
            try:
                if key == keyboard.Key.f6:
                    self.root.after(0, self.start_autoclicking)
                elif key == keyboard.Key.f7:
                    self.root.after(0, self.stop_autoclicking)
                elif key == keyboard.Key.f8:
                    self.root.after(0, self.record_position)
            except AttributeError:
                pass

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

    def validate_delay(self):
        try:
            delay = float(self.delay_entry.get())
            if delay <= 0:
                raise ValueError
            return delay
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive number for delay")
            return None

    def update_status(self, status):
        self.status_var.set(f"Status: {status}")

    def click(self):
        while self.running and self.autoclicking:
            # If a position is saved, move to it before clicking
            if self.saved_position:
                self.mouse.position = self.saved_position
                time.sleep(0.05)  # Small delay to ensure position is set
            
            self.mouse.click(Button.left)
            self.click_count += 1
            
            # Update counter on GUI thread
            self.root.after(0, self.update_counter)
            
            delay = float(self.delay_entry.get())
            time.sleep(delay)

    def update_counter(self):
        self.counter_var.set(f"Clicks: {self.click_count}")

    def start_autoclicking(self):
        if not self.running:
            delay = self.validate_delay()
            if delay is None:
                return
            
            self.save_settings()
            self.running = True
            self.autoclicking = True
            
            if self.saved_position:
                self.update_status(f"Autoclicking at X={self.saved_position[0]}, Y={self.saved_position[1]}")
            else:
                self.update_status("Autoclicking at current mouse position")
            
            self.click_thread = threading.Thread(target=self.click, daemon=True)
            self.click_thread.start()

    def stop_autoclicking(self):
        if self.running:
            self.autoclicking = False
            self.running = False
            self.update_status("Stopped")
            if self.click_thread:
                self.click_thread.join(timeout=1.0)
            self.click_thread = None

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoclickerApp(root)
    root.mainloop()
