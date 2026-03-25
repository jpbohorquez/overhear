import sounddevice as sd
import numpy as np
import threading
import queue
import time
import platform

class AudioEngine:
    """
    Handles audio capture from multiple devices (Mic + System Output).
    Streams audio in chunks to a queue for the transcription engine.
    """
    def __init__(self, sample_rate=16000, chunk_duration=30):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration # Seconds per transcription batch
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.is_paused = False
        
        # Buffers for multi-stream audio
        self.combined_buffer = []
        self.lock = threading.Lock()
        
        # Audio metrics (for UI indicator)
        self.current_volume = 0.0

    def get_input_devices(self):
        """Returns a list of dictionaries containing input device info."""
        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                input_devices.append({
                    "id": i,
                    "name": dev['name'],
                    "channels": dev['max_input_channels']
                })
        return input_devices

    def find_blackhole_or_loopback(self):
        """Returns a list of names for likely aggregate devices to help with UI defaults."""
        devices = self.get_input_devices()
        return [d['name'] for d in devices if "Aggregate" in d['name']]

    def _audio_callback(self, indata, frames, time, status):
        """Called by sounddevice for each audio block."""
        if status:
            print(f"Audio Callback Status: {status}")
        
        if self.is_recording and not self.is_paused:
            # indata shape depends on the device selected. 
            # We mix whatever channels we have down to mono.
            if indata.shape[1] > 1:
                mixed_data = np.mean(indata, axis=1, keepdims=True)
            else:
                mixed_data = indata.copy()
            
            # Calculate volume for UI based on mixed signal
            rms = np.sqrt(np.mean(mixed_data**2))
            self.current_volume = float(rms)
            
            with self.lock:
                self.combined_buffer.extend(mixed_data.flatten().astype(np.float32))
                
                if len(self.combined_buffer) >= self.sample_rate * self.chunk_duration:
                    audio_data = np.array(self.combined_buffer).astype(np.float32)
                    self.audio_queue.put(audio_data)
                    self.combined_buffer = []

    def start_recording(self, device_id):
        """Starts recording from a specific device ID."""
        self.is_recording = True
        self.is_paused = False
        self.combined_buffer = []
        
        # Query device to get its channel count
        dev_info = sd.query_devices(device_id)
        channels = dev_info['max_input_channels']
        
        print(f"Starting recording on device {device_id} ({dev_info['name']}) with {channels} channels")
        
        self.stream = sd.InputStream(
            device=device_id,
            channels=channels, 
            samplerate=self.sample_rate,
            callback=self._audio_callback
        )
        self.stream.start()

    def pause_recording(self):
        self.is_paused = True

    def resume_recording(self):
        self.is_paused = False

    def stop_recording(self):
        self.is_recording = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
            
        # Final flush of buffer
        with self.lock:
            if len(self.combined_buffer) > 0:
                audio_data = np.array(self.combined_buffer).flatten().astype(np.float32)
                self.audio_queue.put(audio_data)
                self.combined_buffer = []

    def get_volume(self):
        """Returns latest volume metric for the UI."""
        return self.current_volume
