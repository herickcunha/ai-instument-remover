# Instrument Remover

Desktop application to remove musical instruments or vocals from YouTube audio using AI. The audio is downloaded, separated into stems (drums, bass, guitar, piano, other, vocals) using the **Demucs HTDEMUCS-6S** model, and the selected stems are removed from the final output.

Additionally, you can export the removed instrument(s) as a separate audio file and choose the separation quality.

## Features

- YouTube audio download (from highest video quality available)
- AI-powered separation into 6 stems: Drums, Bass, Guitar, Piano, Other, Vocals
- Multi-select checkboxes to choose which stems to remove
- **Export removed instrument as a separate file** (optional, enabled by default)
- **Separation quality slider** (shifts 1–10): higher shifts = better quality, slower processing
- Automatic BPM detection (appended to the filename)
- Export as MP3 320 kbps
- **Custom destination folder** with auto-save on completion
- Playback directly for both backing track and removed instrument

## Prerequisites

- **Windows** (works on Linux/macOS with adjustments)
- **Python 3.10 to 3.14** (tested on Python 3.14)
- **FFmpeg** (installed and accessible via PATH)
- **Internet connection** (for audio download and AI model loading)

## Installation

### 1. Install Python

Download the installer from [python.org](https://python.org) and install it, checking **"Add Python to PATH"**.

Verify the installation:

```cmd
python --version
```

### 2. Install FFmpeg

Open **PowerShell as Administrator** and run:

```powershell
winget install "FFmpeg (Essentials Build)"
```

Close and reopen the terminal for the PATH to update.

Verify the installation:

```cmd
ffmpeg -version
```

### 3. Download the project

Copy the entire project folder to the target computer.

### 4. Install dependencies

Open the terminal in the project folder and run:

```cmd
pip install -r requirements.txt
```

> **CUDA note**: PyTorch is installed with CUDA 12.6 support (NVIDIA GPU). On computers without an NVIDIA GPU, PyTorch will use the CPU automatically — it works the same, only slower.

### 5. Run

```cmd
python main.py
```

Or double-click the **`Open.bat`** file.

## How to use

1. **Select stems to remove**: check the boxes for which instruments/vocals you want to remove (Guitar is pre-checked by default)
2. **(Optional) Export removed**: check "Also export removed instrument as separate file" to generate a second file with only the removed stems
3. **Adjust quality**: use the **Shifts** slider — higher values improve separation quality but increase processing time (1× to 10× slower)
4. **Choose destination**: click **"Browse..."** to select where the files will be saved automatically (defaults to `output/`)
5. **Paste the YouTube link**: enter the URL of the desired video
6. **Click "Process"**: the download and processing will begin
7. **Follow the progress**: the progress bar and status show each step
8. **Play**: when finished, use **"Play Backing Track"** or **"Play Removed Instrument"** to open the file in your default player

### Example output filenames

```
Music - Backing Track (without Guitar) [128 BPM].mp3
Music - Removed (Guitar) [128 BPM].mp3
```

## Project structure

```
Instrument Remover/
├── main.py           # GUI (CustomTkinter)
├── processor.py      # Audio processing logic
├── requirements.txt  # Python dependencies
├── Open.bat          # Windows launcher
├── README.md         # This file
├── output/           # Processed audio files
└── temp/             # Temporary working directories
```

## Technologies

| Component | Technology |
|---|---|
| Interface | CustomTkinter |
| Audio separation | Demucs (HTDEMUCS-6S) |
| BPM detection | Librosa |
| Download | yt-dlp |
| Conversion | FFmpeg |
| Processing | PyTorch (CUDA or CPU) |

---

Built with vibe coding using [OpenCode](https://opencode.ai) on DeepSeek V4 Flash Free.
