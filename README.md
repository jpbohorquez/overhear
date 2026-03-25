# Overhear: Local Meeting Transcriber

**Overhear** is a privacy-first, offline-capable desktop application for transcribing meetings in real-time. It captures both your microphone and system audio (e.g., Zoom, Google Meet, Teams) to provide a complete, timestamped transcript of your conversations.

## Features

-   **100% Local Processing**: Transcriptions are performed on your machine using `faster-whisper`. No data ever leaves your computer.
-   **High Accuracy**: Leverages OpenAI's Whisper models (default: `base`, configurable up to `large-v3`).
-   **Meeting-Relative Timestamps**: Generates transcripts with `[HH:MM:SS - HH:MM:SS]` timestamps relative to the start of the meeting.
-   **Automatic Organization**: Transcripts are saved as Markdown text files (`.md`) and organized by date.
-   **Real-time Volume Indicator**: Visual feedback to ensure your audio levels are correct.

---

## Prerequisites

-   **Python 3.9+**
-   **Audio Loopback Software**:
    -   **macOS**: **BlackHole (2ch)** is required. [Download here](https://existential.audio/blackhole/).
    -   **Windows**: **VB-Cable** is recommended. [Download here](https://vb-audio.com/Cable/).

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/jpbohorquez/overhear.git
cd overhear
```

### 2. Setup the Environment

#### macOS / Linux
Run the provided setup script:
```bash
chmod +x setup.sh
./setup.sh
```

#### Windows
Run these commands in PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## System Audio Setup

### macOS (Using BlackHole)

To capture both your microphone and system audio (e.g., Zoom/Google Meet), configure **Audio MIDI Setup**:

#### Step A: Create a Multi-Output Device (To Listen)
1.  Open **Audio MIDI Setup**.
2.  Click `+` > **Create Multi-Output Device**.
3.  Name it `Overhear - Listen`.
4.  Check **BlackHole 2ch** AND your actual output (e.g., "External Headphones").
5.  Set your output device as the **Master Device**.

#### Step B: Create an Aggregate Device (To Record)
1.  Click `+` > **Create Aggregate Device**.
2.  Name it `Overhear - Aggregate`.
3.  Check **BlackHole 2ch** AND your **Microphone**.

### Windows (Using VB-Cable)

#### Step A: Configure System Output
1.  Right-click the Volume icon in the Taskbar and select **Sound settings**.
2.  Set **Output** to **CABLE Input (VB-Audio Virtual Cable)**.
3.  *(Optional but recommended)*: To hear the audio yourself, go to the **Recording** tab in the old Sound Control Panel, right-click **CABLE Output**, select **Properties** > **Listen**, check "Listen to this device", and select your actual headphones/speakers.

#### Step B: Select the Device in Overhear
In the app's dropdown, select **CABLE Output (VB-Audio Virtual Cable)** to capture the system audio. If you want to capture your microphone simultaneously, you may need to use a tool like **VoiceMeeter** to mix them into the virtual cable.

---

## Usage

### 1. Set System Output
Before starting your meeting, click the Volume icon in your macOS menu bar (or Windows Sound Settings) and set your output to your virtual loopback device (e.g., **Overhear - Listen** on Mac or **VB-Cable** on Windows).

### 2. Launch the Application

-   **macOS**: Double-click the `launch.command` file in the project folder.
-   **Windows**: Double-click the `launch.bat` file in the project folder.

Alternatively, you can run it from the terminal:
```bash
# macOS/Linux
source .venv/bin/activate
python3 main.py

# Windows
.\.venv\Scripts\Activate.ps1
python main.py
```

### 3. Start Transcribing
1.  **Enter Meeting Name**: e.g., "Weekly Sync".
2.  **Select Audio Source**: Choose your aggregate/loopback device from the dropdown menu.
3.  **Click Record**: The app will begin capturing and transcribing.
4.  **Click Stop**: The transcript will be finalized and saved.

---

## Transcript Location

Transcripts are automatically saved in the `transcriptions/` directory, organized by date:
`transcriptions/YYYY-MM-DD/MeetingName_HH-MM-SS.md`

---

## Configuration

You can customize the application's behavior by editing the `config.toml` file:

```toml
[transcription]
# Whisper model size: tiny, base, small, medium, large-v3
model_size = "base"

# Output directory for transcriptions
output_dir = "transcriptions"

[audio]
# Sampling rate (default is 16000)
sample_rate = 16000

# Duration of each audio chunk in seconds
chunk_duration = 30
```

## Troubleshooting

-   **No Audio Detected**: Ensure your System Output is set to your "Multi-Output" device and you've selected the correct "Aggregate" device in the app.
-   **Slow Transcription**: If the transcription lags significantly behind real-time, try a smaller model (e.g., `tiny` or `base`).
-   **Permissions**: Ensure your terminal or IDE has permission to access the Microphone in System Settings > Privacy & Security.
