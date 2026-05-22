# Instrument Remover

Remove instruments/vocals from YouTube audio using Demucs.

## Stack
- Python 3.10+, CustomTkinter (UI), PyTorch + Demucs (separation), yt-dlp (download), librosa (BPM), ffmpeg (conversion)

## Source files
- `main.py` — GUI layer (CustomTkinter). Contains the `App` class (subclasses `ctk.CTk`).
- `processor.py` — Processing pipeline: download → WAV → separation → remix → file copy.

## Design decisions
- Dark mode (`"dark"`) with blue accent theme (`"blue"`)
- Window starts at `700x660`, minimum `650x580`
- Checkboxes use `border_width=2`, buttons use `corner_radius=6-8`
- Status icon prefix: ○ idle, ▶ processing, ✓ done, ✗ error

## Config persistence
- `config.json` in the project root
- Persists `dest_dir` (output folder) on browse and on window close
- `CONFIG_PATH = Path(__file__).parent / "config.json"`

## Processing pipeline
1. Download MP3 from YouTube via yt-dlp
2. Convert to 44.1kHz WAV via ffmpeg
3. Detect BPM via librosa
4. Separate stems with htdemucs_6s model (Demucs)
5. Remix without selected stems → 320kbps MP3
6. Optionally: remix only the removed stems
7. Copy output files to the chosen destination folder

## Directory layout
- `output/` — default output directory
- `temp/` — temporary working files (cleaned up after processing)
- `config.json` — user preferences
