from faster_whisper import WhisperModel
import threading
import queue
import time
import os
from datetime import datetime

class TranscriptionEngine:
    """
    Consumes audio chunks from the queue and transcribes them using faster-whisper.
    Appends the results to a local file with timestamps.
    """
    def __init__(self, model_size="base", device="cpu"):
        # Load the model (offline after initial download)
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        self.is_running = False
        self.current_file = None
        self.start_time = None
        
    def start(self, audio_queue, meeting_name):
        """Starts the transcription loop in a background thread."""
        self.is_running = True
        self.audio_queue = audio_queue
        self.meeting_name = meeting_name
        self.start_time = time.time()
        
        # 1. Prepare directory structure
        # Root: transcriptions/, Subfolder: YYYY-MM-DD
        base_dir = "transcriptions"
        date_folder = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join(base_dir, date_folder)
        
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
                    ts_start = segment.start
                    ts_end = segment.end
                    line = f"[{ts_start:05.2f} - {ts_end:05.2f}] {segment.text}\n"
                    print(f"Transcribed: {line.strip()}")
                    f.write(line)
                    f.flush() # Ensure it's written immediately

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
