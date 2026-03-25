import customtkinter as ctk
import threading
import time
from audio_engine import AudioEngine
from transcription_engine import TranscriptionEngine

# UI Theme Setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TranscriptionApp(ctk.CTk):
    """
    Main Application Window. 
    Manages coordination between Audio Capture, Transcription, and the UI.
    """
    def __init__(self):
        super().__init__()

        self.title("Local Meeting Transcriber")
        self.geometry("500x450")

        # Initialize Engines
        self.audio_engine = AudioEngine()
        self.transcriber = TranscriptionEngine() # Configuration loaded from config.toml

        self._build_ui()
        self._update_volume_indicator() # Start UI polling for volume

    def _build_ui(self):
        """Creates the GUI layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 1. Meeting Name Input
        self.title_label = ctk.CTkLabel(self.main_frame, text="Meeting Name:", font=("Inter", 14, "bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.meeting_input = ctk.CTkEntry(self.main_frame, placeholder_text="Enter meeting name...", width=400)
        self.meeting_input.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")

        # 2. Audio Device Selection
        self.device_label = ctk.CTkLabel(self.main_frame, text="Select Audio Source (Aggregate Device):", font=("Inter", 14, "bold"))
        self.device_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        
        # Get devices and prepare for dropdown
        self.devices = self.audio_engine.get_input_devices()
        self.device_map = {d['name']: d['id'] for d in self.devices}
        device_names = list(self.device_map.keys())
        
        # Try to find a default (Aggregate Device)
        default_device = next((name for name in device_names if "Aggregate" in name), device_names[0] if device_names else "No input found")
        
        self.device_var = ctk.StringVar(value=default_device)
        self.device_menu = ctk.CTkOptionMenu(self.main_frame, values=device_names, variable=self.device_var, width=400)
        self.device_menu.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")

        # 3. Control Buttons
        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.grid(row=4, column=0, padx=20, pady=10)

        self.record_btn = ctk.CTkButton(self.btn_frame, text="Record", command=self.start_recording, fg_color="#2ecc71", hover_color="#27ae60")
        self.record_btn.grid(row=0, column=0, padx=5)

        self.pause_btn = ctk.CTkButton(self.btn_frame, text="Pause", command=self.toggle_pause, state="disabled")
        self.pause_btn.grid(row=0, column=1, padx=5)

        self.stop_btn = ctk.CTkButton(self.btn_frame, text="Stop", command=self.stop_recording, state="disabled", fg_color="#e74c3c", hover_color="#c0392b")
        self.stop_btn.grid(row=0, column=2, padx=5)

        # 4. Volume Indicator (Visualizer)
        self.volume_label = ctk.CTkLabel(self.main_frame, text="Audio Levels:", font=("Inter", 12))
        self.volume_label.grid(row=5, column=0, padx=20, pady=(10, 5), sticky="w")

        self.volume_bar = ctk.CTkProgressBar(self.main_frame, width=400)
        self.volume_bar.set(0) # Initial level
        self.volume_bar.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="ew")

        # 5. Status Label
        self.status_label = ctk.CTkLabel(self.main_frame, text="Status: Ready", font=("Inter", 12, "italic"))
        self.status_label.grid(row=7, column=0, padx=20, pady=(0, 20))

    def _update_volume_indicator(self):
        """Polls the audio engine for volume levels to update UI."""
        if self.audio_engine.is_recording and not self.audio_engine.is_paused:
            # Scale the raw volume (0.0 to 1.0) for the progress bar
            vol = self.audio_engine.get_volume()
            # Simple scaling for visualization (tweak as needed)
            clamped_vol = min(vol * 5, 1.0) 
            self.volume_bar.set(clamped_vol)
        else:
            self.volume_bar.set(0)
        
        # Poll every 50ms
        self.after(50, self._update_volume_indicator)

    def start_recording(self):
        name = self.meeting_input.get().strip() or "Unnamed_Meeting"
        selected_name = self.device_var.get()
        device_id = self.device_map.get(selected_name)
        
        if device_id is None:
            self.status_label.configure(text="Error: No valid device selected.")
            return

        try:
            self.audio_engine.start_recording(device_id)
            self.transcriber.start(self.audio_engine.audio_queue, name)
            
            # Update UI state
            self.record_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal", text="Pause")
            self.stop_btn.configure(state="normal")
            self.meeting_input.configure(state="disabled")
            self.device_menu.configure(state="disabled")
            self.status_label.configure(text=f"Status: Recording via {selected_name}")
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")

    def toggle_pause(self):
        if not self.audio_engine.is_paused:
            self.audio_engine.pause_recording()
            self.pause_btn.configure(text="Resume")
            self.status_label.configure(text="Status: Paused")
        else:
            self.audio_engine.resume_recording()
            self.pause_btn.configure(text="Pause")
            self.status_label.configure(text="Status: Recording...")

    def stop_recording(self):
        self.status_label.configure(text="Status: Stopping & Saving...")
        self.update_idletasks() # Refresh UI to show status
        
        # 1. Stop Audio
        self.audio_engine.stop_recording()
        # 2. Stop Transcriber (Processes remaining queue items)
        self.transcriber.stop()
        
        # Reset UI
        self.record_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        self.meeting_input.configure(state="normal")
        self.device_menu.configure(state="normal")
        self.status_label.configure(text=f"Status: Saved to {self.transcriber.filename}")

if __name__ == "__main__":
    app = TranscriptionApp()
    app.mainloop()
