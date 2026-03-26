# Overhear: Local Meeting Transcriber & Summarizer

**Overhear** is a privacy-first, offline-capable desktop application for transcribing meetings in real-time and generating intelligent summaries using LLMs. It captures both your microphone and system audio (e.g., Zoom, Google Meet, Teams) to provide a complete, timestamped transcript and an actionable summary of your conversations.

## Features

-   **100% Local Processing (Transcription)**: Transcriptions are performed on your machine using `faster-whisper`. No audio data ever leaves your computer.
-   **Agnostic Summarization (LLM)**: Generate summaries using any provider supported by `litellm` (Gemini, OpenAI, Anthropic, etc.).
-   **Auto-Summarize**: Automatically trigger a summary generation immediately after a recording stops.
-   **Meeting-Relative Timestamps**: Generates transcripts with `[HH:MM:SS - HH:MM:SS]` timestamps relative to the start of the meeting.
-   **Automatic Organization**: Transcripts and summaries are saved as Markdown files (`.md`) and organized by date.
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
To capture both your microphone and system audio (e.g., Zoom/Google Meet), configure **Audio MIDI Setup**. You can create as many common configurations as you like (e.g. speakers, headphones, airpods, etc.)

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
Before starting your meeting, click the Volume icon in your macOS menu bar (or Windows Sound Settings) and set your output to your virtual loopback device (e.g., **Overhear - Listen** on Mac or **VB-Cable** on Windows)

### 2. Launch the Application
-   **macOS**: Double-click `launch.command`.
-   **Windows**: Double-click `launch.bat`.

### 3. Summarization Setup
1.  Go to the **Settings** tab.
2.  Select your **API Provider** (e.g., GEMINI).
3.  Enter your **API Key**.
4.  The **LLM Model** dropdown will dynamically populate with available models for that provider.
5.  Click **Save Settings**.

### 4. Transcribe & Summarize
1.  **Recording Tab**: Enter meeting name, select device, and click **Record**.
2.  **Auto-Summarize**: Toggle "Auto-Summarize after stop" to get an instant summary when you finish.
3.  **Summarization Tab**: Manually process any existing transcript by selecting it and clicking **Generate Summary**.

---

## Configuration

Settings are stored in `config.toml`. Secrets are stored in `.secrets.toml` (which is git-ignored).

```toml
[transcription]
model_size = "base"
output_dir = "transcriptions"

[summarization]
model_name = "gemini/gemini-1.5-flash"
summaries_dir = "summaries"
system_prompt = "..."
```

---

## Troubleshooting

-   **No Audio**: Verify MIDI/Sound settings and ensure the correct Aggregate/CABLE device is selected in the app.
-   **LLM Errors**: Ensure your API key is correct and you have internet access for the summarization phase.
-   **Permissions**: Grant Microphone permissions to your terminal/Python in System Settings.
