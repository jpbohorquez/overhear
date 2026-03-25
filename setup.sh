#!/bin/bash

# Meeting Transcription App - Environment Setup Script
# Works on macOS/Linux. For Windows, use PowerShell equivalents.

echo "Setting up local transcription environment..."

# 1. Check for Python 3.9+ (Faster-Whisper requirement)
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

# 2. Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

# 3. Activate environment
source .venv/bin/activate

# 4. Upgrade pip
pip install --upgrade pip

# 5. Install dependencies
echo "Installing requirements from requirements.txt..."
pip install -r requirements.txt

# 6. Additional system requirements (Instructional)
echo "-------------------------------------------------------"
echo "SYSTEM SETUP STEPS FOR MULTIPLE SCENARIOS:"
echo ""
echo "For each setup (e.g., 'Headphones', 'Mac Speakers', 'Second Headphones'):"
echo ""
echo "A. Create a Multi-Output Device (Where YOU hear):"
echo "   1. Open 'Audio MIDI Setup' and create a 'Multi-Output Device'."
echo "   2. Name it clearly (e.g., 'Multi-Out Headphones')."
echo "   3. Include 'BlackHole 2ch' AND your target output (e.g., 'External Headphones')."
echo "   4. Set 'Master Device' to your target output (e.g., 'External Headphones')."
echo ""
echo "B. Create an Aggregate Device (Where the APP records):"
echo "   1. Create an 'Aggregate Device' in 'Audio MIDI Setup'."
echo "   2. Name it clearly (e.g., 'Aggregate - Headphones')."
echo "   3. Include 'BlackHole 2ch' AND your Microphone."
echo ""
echo "C. To Record:"
echo "   1. Switch System Output (Volume Icon) to the 'Multi-Output' device for your current setup."
echo "   2. Launch the App and select the corresponding 'Aggregate' device from the dropdown."
echo "-------------------------------------------------------"

echo "Setup complete. Run 'source .venv/bin/activate && python main.py' to start."
