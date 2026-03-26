import customtkinter as ctk
import threading
import time
import os
from tkinter import filedialog
from audio_engine import AudioEngine
from transcription_engine import TranscriptionEngine
from summarizer import Summarizer

# UI Theme Setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TranscriptionApp(ctk.CTk):
    """
    Main Application Window. 
    Manages coordination between Audio Capture, Transcription, Summarization and the UI.
    """
    def __init__(self):
        super().__init__()

        self.title("Overhear - Local Transcriber & Summarizer")
        self.geometry("600x600")

        # Initialize Engines
        self.audio_engine = AudioEngine()
        self.transcriber = TranscriptionEngine()
        self.summarizer = Summarizer()

        self._build_ui()
        self._update_volume_indicator()
        self._refresh_latest_transcript()

    def _build_ui(self):
        """Creates the tabbed GUI layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tabview.add("Recording")
        self.tabview.add("Summarization")
        self.tabview.add("Settings")

        self._build_recording_tab()
        self._build_summarization_tab()
        self._build_settings_tab()

    def _build_recording_tab(self):
        tab = self.tabview.tab("Recording")
        tab.grid_columnconfigure(0, weight=1)

        # 1. Meeting Name Input
        self.title_label = ctk.CTkLabel(tab, text="Meeting Name:", font=("Inter", 14, "bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.meeting_input = ctk.CTkEntry(tab, placeholder_text="Enter meeting name...", width=400)
        self.meeting_input.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")

        # 2. Audio Device Selection
        self.device_label = ctk.CTkLabel(tab, text="Select Audio Source:", font=("Inter", 14, "bold"))
        self.device_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.devices = self.audio_engine.get_input_devices()
        self.device_map = {d['name']: d['id'] for d in self.devices}
        device_names = list(self.device_map.keys())
        default_device = next((name for name in device_names if "Aggregate" in name or "BlackHole" in name or "CABLE" in name), device_names[0] if device_names else "No input found")
        
        self.device_var = ctk.StringVar(value=default_device)
        self.device_menu = ctk.CTkOptionMenu(tab, values=device_names, variable=self.device_var, width=400)
        self.device_menu.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")

        # 3. Control Buttons
        self.btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.btn_frame.grid(row=4, column=0, padx=20, pady=10)

        self.record_btn = ctk.CTkButton(self.btn_frame, text="Record", command=self.start_recording, fg_color="#2ecc71", hover_color="#27ae60")
        self.record_btn.grid(row=0, column=0, padx=5)

        self.pause_btn = ctk.CTkButton(self.btn_frame, text="Pause", command=self.toggle_pause, state="disabled")
        self.pause_btn.grid(row=0, column=1, padx=5)

        self.stop_btn = ctk.CTkButton(self.btn_frame, text="Stop", command=self.stop_recording, state="disabled", fg_color="#e74c3c", hover_color="#c0392b")
        self.stop_btn.grid(row=0, column=2, padx=5)

        # 4. Auto-Summarize Toggle
        self.auto_summarize_var = ctk.BooleanVar(value=False)
        self.auto_summarize_switch = ctk.CTkSwitch(tab, text="Auto-Summarize after stop", variable=self.auto_summarize_var)
        self.auto_summarize_switch.grid(row=5, column=0, padx=20, pady=10, sticky="w")

        # 5. Volume Indicator
        self.volume_label = ctk.CTkLabel(tab, text="Audio Levels:", font=("Inter", 12))
        self.volume_label.grid(row=6, column=0, padx=20, pady=(10, 5), sticky="w")

        self.volume_bar = ctk.CTkProgressBar(tab, width=400)
        self.volume_bar.set(0)
        self.volume_bar.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")

        # 6. Status Label
        self.status_label = ctk.CTkLabel(tab, text="Status: Ready", font=("Inter", 12, "italic"))
        self.status_label.grid(row=8, column=0, padx=20, pady=(0, 20))

    def _build_summarization_tab(self):
        tab = self.tabview.tab("Summarization")
        tab.grid_columnconfigure(0, weight=1)

        # 1. Transcript File Selection
        self.file_label = ctk.CTkLabel(tab, text="Select Transcript:", font=("Inter", 14, "bold"))
        self.file_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        file_row = ctk.CTkFrame(tab, fg_color="transparent")
        file_row.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="ew")
        file_row.grid_columnconfigure(0, weight=1)

        self.transcript_file_var = ctk.StringVar()
        self.transcript_file_entry = ctk.CTkEntry(file_row, textvariable=self.transcript_file_var)
        self.transcript_file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.browse_btn = ctk.CTkButton(file_row, text="Browse", width=80, command=self._browse_transcript)
        self.browse_btn.grid(row=0, column=1)

        self.refresh_btn = ctk.CTkButton(tab, text="Use Latest Transcript", command=self._refresh_latest_transcript)
        self.refresh_btn.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")

        # 2. Summary Prompt Editor
        self.prompt_label = ctk.CTkLabel(tab, text="Summary Prompt:", font=("Inter", 14, "bold"))
        self.prompt_label.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="w")

        self.prompt_text = ctk.CTkTextbox(tab, height=150, width=400)
        self.prompt_text.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.prompt_text.insert("1.0", self.summarizer.system_prompt)

        # 3. Generate Button
        self.sum_btn = ctk.CTkButton(tab, text="Generate Summary", command=self.generate_summary)
        self.sum_btn.grid(row=5, column=0, padx=20, pady=(10, 4))

        # 4. Progress bar (indeterminate spinner, hidden until a call is running)
        self.sum_progress = ctk.CTkProgressBar(tab, mode="indeterminate", width=400)
        self.sum_progress.grid(row=6, column=0, padx=20, pady=(0, 4), sticky="ew")
        self.sum_progress.grid_remove()

        # 5. Status label
        self.sum_status_label = ctk.CTkLabel(tab, text="", font=("Inter", 12, "italic"))
        self.sum_status_label.grid(row=7, column=0, padx=20, pady=(0, 10))

    def _build_settings_tab(self):
        tab = self.tabview.tab("Settings")
        tab.grid_columnconfigure(0, weight=1)

        # 1. API Key & Provider
        self.provider_label = ctk.CTkLabel(tab, text="API Provider:", font=("Inter", 14, "bold"))
        self.provider_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.provider_var = ctk.StringVar(value="GEMINI")
        self.provider_menu = ctk.CTkOptionMenu(tab, values=["GEMINI", "OPENAI", "ANTHROPIC"], variable=self.provider_var, command=self._on_provider_change)
        self.provider_menu.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        self.key_label = ctk.CTkLabel(tab, text="API Key:", font=("Inter", 14, "bold"))
        self.key_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.key_entry = ctk.CTkEntry(tab, show="*", width=400)
        self.key_entry.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # 2. Model Selection
        model_header = ctk.CTkFrame(tab, fg_color="transparent")
        model_header.grid(row=4, column=0, padx=20, pady=(10, 0), sticky="ew")
        model_header.grid_columnconfigure(0, weight=1)

        self.model_label = ctk.CTkLabel(model_header, text="LLM Model:", font=("Inter", 14, "bold"))
        self.model_label.grid(row=0, column=0, sticky="w")

        self.refresh_models_btn = ctk.CTkButton(
            model_header, text="Refresh", width=80, height=26,
            command=self._on_refresh_models_clicked
        )
        self.refresh_models_btn.grid(row=0, column=1, sticky="e")

        self.model_var = ctk.StringVar(value=self.summarizer.model_name)
        self.model_menu = ctk.CTkOptionMenu(tab, values=[self.summarizer.model_name], variable=self.model_var, width=400)
        self.model_menu.grid(row=5, column=0, padx=20, pady=(4, 0), sticky="ew")

        self.model_status_label = ctk.CTkLabel(tab, text="", font=("Inter", 11), text_color="gray")
        self.model_status_label.grid(row=6, column=0, padx=20, pady=(2, 10), sticky="w")

        self._on_provider_change("GEMINI")  # Load initial key and models

        # 3. Save Settings
        self.save_settings_btn = ctk.CTkButton(tab, text="Save Settings", command=self.save_settings)
        self.save_settings_btn.grid(row=7, column=0, padx=20, pady=(10, 20))

    def _on_provider_change(self, provider):
        """Update key entry and trigger async model fetch when provider changes."""
        self.key_entry.delete(0, "end")
        existing_key = self.summarizer.get_api_key(provider)
        if existing_key:
            self.key_entry.insert(0, existing_key)
            self._load_models_async(provider, existing_key)
        else:
            self.model_menu.configure(state="normal", values=["— enter API key first —"])
            self.model_var.set("— enter API key first —")
            self.model_status_label.configure(text="Save an API key to load available models.")

    def _on_refresh_models_clicked(self):
        provider = self.provider_var.get()
        api_key = self.key_entry.get().strip() or self.summarizer.get_api_key(provider)
        if not api_key:
            self.model_status_label.configure(text="No API key found. Save one first.")
            return
        self._load_models_async(provider, api_key)

    def _load_models_async(self, provider: str, api_key: str):
        """Fetch live models in a background thread and update the dropdown."""
        self.model_menu.configure(state="disabled", values=["Loading..."])
        self.model_var.set("Loading...")
        self.model_status_label.configure(text="Fetching available models...")
        self.refresh_models_btn.configure(state="disabled")

        current_model = self.summarizer.model_name

        def worker():
            try:
                models = self.summarizer.fetch_live_models(provider, api_key)
                self.after(0, self._apply_loaded_models, models, current_model)
            except Exception as e:
                self.after(0, self._apply_models_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_loaded_models(self, models: list, preferred: str):
        self.refresh_models_btn.configure(state="normal")
        if not models:
            self.model_menu.configure(state="normal", values=["— no models found —"])
            self.model_var.set("— no models found —")
            self.model_status_label.configure(text="No supported models found for this provider.")
            return
        self.model_menu.configure(state="normal", values=models)
        if preferred in models:
            self.model_var.set(preferred)
        else:
            self.model_var.set(models[0])
        self.model_status_label.configure(text=f"{len(models)} models available.")

    def _apply_models_error(self, error: str):
        self.refresh_models_btn.configure(state="normal")
        self.model_menu.configure(state="normal", values=[self.summarizer.model_name])
        self.model_var.set(self.summarizer.model_name)
        msg = self._format_error(error)
        self.model_status_label.configure(text=f"Could not fetch models: {msg}")

    def _browse_transcript(self):
        path = filedialog.askopenfilename(
            title="Select Transcript",
            initialdir=self.summarizer.transcriptions_dir,
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if path:
            self.transcript_file_var.set(path)

    def _refresh_latest_transcript(self):
        latest = self.summarizer.get_latest_transcript()
        if latest:
            self.transcript_file_var.set(latest)

    def save_settings(self):
        provider = self.provider_var.get()
        api_key = self.key_entry.get().strip()
        key_saved = False
        if api_key:
            self.summarizer.save_api_key(provider, api_key)
            key_saved = True

        new_model = self.model_var.get()
        # Only persist if it looks like a real model name (not a placeholder)
        if new_model and not new_model.startswith("—"):
            self.summarizer.model_name = new_model
            try:
                import toml
                config = toml.load(self.summarizer.config_path)
                config.setdefault("summarization", {})["model_name"] = new_model
                with open(self.summarizer.config_path, "w") as f:
                    toml.dump(config, f)
            except Exception as e:
                print(f"Error saving model to config: {e}")

        if key_saved:
            self.status_label.configure(text=f"Status: {provider} API key saved — refreshing models...")
            self._load_models_async(provider, api_key)
        else:
            self.status_label.configure(text="Status: Settings saved.")

    def generate_summary(self, file_path=None):
        target_file = file_path if file_path else self.transcript_file_var.get()
        if not target_file or not os.path.exists(target_file):
            self.sum_status_label.configure(text="Error: Transcript file not found.")
            return

        self.sum_btn.configure(state="disabled")
        self.sum_status_label.configure(text="", text_color="gray")
        self.sum_progress.grid()
        self.sum_progress.start()
        
        custom_prompt = self.prompt_text.get("1.0", "end-1c")
        self.summarizer.summarize(target_file, custom_prompt, self._summary_callback)

    def _summary_callback(self, success, result):
        # Called from a background thread — schedule UI updates on the main thread.
        self.after(0, self._apply_summary_result, success, result)

    def _apply_summary_result(self, success, result):
        self.sum_progress.stop()
        self.sum_progress.grid_remove()
        self.sum_btn.configure(state="normal")
        if success:
            name = os.path.basename(result)
            self.sum_status_label.configure(text=f"Summary saved: {name}", text_color="green")
            self.status_label.configure(text=f"Status: Summary saved — {name}")
        else:
            msg = self._format_error(result)
            self.sum_status_label.configure(text=f"Error: {msg}", text_color="#e74c3c")
            self.status_label.configure(text="Status: Summary failed — see Summarization tab")

    def _format_error(self, error_str: str) -> str:
        """Return a short, human-readable error message from a raw exception string."""
        s = error_str
        if "NotFoundError" in s or "NOT_FOUND" in s or "404" in s:
            return "Model not found (may be deprecated). Select another model in Settings."
        if "AuthenticationError" in s or "UNAUTHENTICATED" in s or "401" in s:
            return "Invalid API key. Check your key in Settings."
        if "RateLimitError" in s or "RESOURCE_EXHAUSTED" in s or "429" in s:
            return "Rate limit reached. Wait a moment and try again."
        if "Timeout" in s or "timeout" in s:
            return "Request timed out. Try a faster model or check your connection."
        if "ConnectionError" in s or "Connection refused" in s:
            return "Connection failed. Check your internet connection."
        # Fallback: first non-boilerplate line, capped at 120 chars
        skip = {"Traceback", "File ", "During ", "  "}
        for line in s.split("\n"):
            line = line.strip()
            if line and not any(line.startswith(p) for p in skip):
                return line[:120]
        return "An unexpected error occurred."

    def _update_volume_indicator(self):
        if self.audio_engine.is_recording and not self.audio_engine.is_paused:
            vol = self.audio_engine.get_volume()
            clamped_vol = min(vol * 5, 1.0) 
            self.volume_bar.set(clamped_vol)
        else:
            self.volume_bar.set(0)
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
        self.update_idletasks()
        self.audio_engine.stop_recording()
        self.transcriber.stop()
        
        final_filename = self.transcriber.filename
        
        self.record_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        self.meeting_input.configure(state="normal")
        self.device_menu.configure(state="normal")
        self.status_label.configure(text=f"Status: Saved to {os.path.basename(final_filename)}")

        # Auto-summarize logic
        if self.auto_summarize_var.get():
            self.generate_summary(final_filename)
        
        # Refresh the latest transcript in the other tab
        self._refresh_latest_transcript()

if __name__ == "__main__":
    app = TranscriptionApp()
    app.mainloop()
