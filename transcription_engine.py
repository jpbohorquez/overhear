from faster_whisper import WhisperModel
import threading
import queue
import time
import toml
import os
from datetime import datetime

class TranscriptionEngine:
    """
    Consumes audio chunks from the queue and transcribes them using faster-whisper.
    Appends the results to a local file with timestamps.
    """
    def __init__(self, config_path="config.toml", device="cpu"):
        self.config_path = config_path
        self.device = device
        self._load_config()
            
        # Load the model (offline after initial download)
        self.model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
        self.is_running = False
        self.current_file = None
        self.start_time = None
        self.total_processed_seconds = 0.0

    def _load_config(self):
        # Load configuration
        if os.path.exists(self.config_path):
            config = toml.load(self.config_path)
            self.model_size = config.get("transcription", {}).get("model_size", "base")
            self.base_dir = config.get("transcription", {}).get("output_dir", "transcriptions")
            self.sample_rate = config.get("audio", {}).get("sample_rate", 16000)
        else:
            self.model_size = "base"
            self.base_dir = "transcriptions"
            self.sample_rate = 16000

    def update_config(self):
        """Reloads configuration from disk."""
        old_model_size = self.model_size
        self._load_config()
        
        # If model size changed and we are not currently recording, reload model
        if old_model_size != self.model_size and not self.is_running:
            print(f"Reloading Whisper model with new size: {self.model_size}")
            self.model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
        
    def start(self, audio_queue, meeting_name):
        """Starts the transcription loop in a background thread."""
        self.is_running = True
        self.audio_queue = audio_queue
        self.meeting_name = meeting_name
        self.start_time = time.time()
        self.total_processed_seconds = 0.0
        
        # 1. Prepare directory structure
        # Root from config, Subfolder: YYYY-MM-DD
        date_folder = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join(self.base_dir, date_folder)
        
        # Create directories if they don't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # 2. Create output file path
        timestamp = datetime.now().strftime("%H-%M-%S")
        self.filename = os.path.join(output_dir, f"{meeting_name}_{timestamp}.md")
        
        with open(self.filename, "w") as f:
            f.write(f"# Meeting: {meeting_name}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"---\n\n")

        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()

    def _format_timestamp(self, seconds):
        """Formats seconds into HH:MM:SS string."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _process_queue(self):
        """Worker loop for transcription."""
        print(f"Transcription engine started for {self.filename}")
        
        while self.is_running or not self.audio_queue.empty():
            try:
                # Wait for audio chunk with a timeout to allow exit
                audio_data = self.audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # Transcribe the audio chunk
            segments, info = self.model.transcribe(audio_data, beam_size=5)
            
            # Format and save segments
            with open(self.filename, "a") as f:
                for segment in segments:
                    # Calculate timestamp relative to meeting start
                    ts_start = segment.start + self.total_processed_seconds
                    ts_end = segment.end + self.total_processed_seconds
                    
                    time_str = f"[{self._format_timestamp(ts_start)} - {self._format_timestamp(ts_end)}]"
                    line = f"{time_str} {segment.text}\n"
                    print(f"Transcribed: {line.strip()}")
                    f.write(line)
                    f.flush() # Ensure it's written immediately

            # Update total processed seconds based on chunk length
            self.total_processed_seconds += len(audio_data) / float(self.sample_rate)
            self.audio_queue.task_done()

    def stop(self):
        """Gracefully stops the worker after processing remaining queue items."""
        self.is_running = False
        if hasattr(self, 'thread'):
            self.thread.join()
        print(f"Transcription engine stopped. Results saved to {self.filename}")

    def speaker_diarization_stub(self, segments):
        """
        Placeholder for future diarization. 
        In the future, we would pass audio embeddings to a clustering algorithm 
        (like Pyannote) to distinguish speakers.
        """
        # Logic: Assign Speaker A/B based on volume ratio or external embeddings.
        return segments
