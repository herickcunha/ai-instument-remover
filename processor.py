import os
import re
import subprocess
import shutil
import tempfile
from pathlib import Path

import yt_dlp
import torch
import numpy as np
import soundfile as sf
import librosa


FFMPEG_PATH = shutil.which("ffmpeg") or "ffmpeg"

BASE_DIR = Path(__file__).parent.resolve()
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.strip().rstrip(". ")
    return name or "audio"


def download_audio(url: str, output_dir: Path, progress_callback=None) -> str:
    if progress_callback:
        progress_callback("Downloading YouTube audio...", 0.05)

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "audio")
            files = list(output_dir.glob("*.mp3"))
            if not files:
                raise RuntimeError("MP3 file not found after download")
            return title, str(files[0])
    except Exception as e:
        raise RuntimeError(f"Error downloading audio: {e}")


def convert_to_wav(mp3_path: str, output_dir: Path, progress_callback=None) -> str:
    if progress_callback:
        progress_callback("Converting to WAV...", 0.15)

    wav_path = str(output_dir / "audio_input.wav")
    cmd = [
        FFMPEG_PATH,
        "-i", mp3_path,
        "-ar", "44100",
        "-ac", "2",
        "-sample_fmt", "s16",
        "-y", wav_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return wav_path


def detect_bpm(wav_path: str, progress_callback=None) -> int:
    if progress_callback:
        progress_callback("Detecting BPM...", 0.17)

    y, sr = librosa.load(wav_path, sr=None, mono=True)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    if isinstance(tempo, np.ndarray):
        tempo = tempo.item()
    return round(float(tempo))


def separate_sources(wav_path: str, output_dir: Path, device: str, shifts: int = 1, progress_callback=None):
    if progress_callback:
        progress_callback("Loading Demucs model (htdemucs_6s)...", 0.20)

    from demucs.apply import apply_model
    from demucs.pretrained import get_model
    from demucs.audio import AudioFile, convert_audio

    model = get_model("htdemucs_6s")
    model.to(device)
    model.eval()

    if progress_callback:
        progress_callback("Separating sources...", 0.35)

    audio = AudioFile(wav_path)
    wav = audio.read()
    sr = audio.samplerate()
    wav = convert_audio(wav, sr, model.samplerate, model.audio_channels)

    wav = wav.to(device)

    with torch.no_grad():
        sources = apply_model(model, wav, shifts=shifts, overlap=0.25, progress=True)[0]

    sources = sources.cpu()

    stems_dir = output_dir / "stems"
    stems_dir.mkdir(exist_ok=True)

    stem_names = model.sources
    for idx, name in enumerate(stem_names):
        stem_path = stems_dir / f"{name}.wav"
        stem_audio = sources[idx].numpy().T
        sf.write(str(stem_path), stem_audio, model.samplerate)
        if progress_callback:
            pct = 0.35 + (idx + 1) / len(stem_names) * 0.35
            progress_callback(f"Processed: {name}", pct)

    return stems_dir, stem_names, model.samplerate


STEM_NAMES_EN = {
    "drums": "Drums",
    "bass": "Bass",
    "guitar": "Guitar",
    "piano": "Piano",
    "other": "Other",
    "vocals": "Vocals",
}


def mix_without_stems(stems_dir: Path, stem_names, sample_rate: int, title: str, stems_to_remove: list[str], bpm: int | None = None, progress_callback=None):
    removed_labels = [STEM_NAMES_EN.get(s, s.capitalize()) for s in stems_to_remove]
    removed_str = "+".join(removed_labels)
    if progress_callback:
        progress_callback(f"Remixing audio without {removed_str}...", 0.75)

    remove_idxs = set()
    for name in stems_to_remove:
        for i, sn in enumerate(stem_names):
            if sn.lower() == name.lower():
                remove_idxs.add(i)
                break

    if not remove_idxs:
        raise RuntimeError("No valid stems selected for removal")

    mixed = None
    for i, name in enumerate(stem_names):
        if i in remove_idxs:
            continue
        stem_path = stems_dir / f"{name}.wav"
        stem_audio, _ = sf.read(str(stem_path))
        if mixed is None:
            mixed = stem_audio.astype(np.float64)
        else:
            mixed += stem_audio.astype(np.float64)

    mixed = np.clip(mixed, -1.0, 1.0)

    temp_wav = stems_dir / "temp_mix.wav"
    sf.write(str(temp_wav), mixed, sample_rate)

    if progress_callback:
        progress_callback("Converting to MP3...", 0.90)

    safe_title = sanitize_filename(title)
    bpm_suffix = f" [{bpm} BPM]" if bpm else ""
    output_filename = f"{safe_title} - Backing Track (without {removed_str}){bpm_suffix}.mp3"
    output_path = OUTPUT_DIR / output_filename

    cmd = [
        FFMPEG_PATH,
        "-i", str(temp_wav),
        "-codec:a", "libmp3lame",
        "-b:a", "320k",
        "-y", str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    return str(output_path)


def mix_removed_stems(stems_dir: Path, stem_names, sample_rate: int, title: str, stems_to_remove: list[str], bpm: int | None = None, progress_callback=None):
    removed_labels = [STEM_NAMES_EN.get(s, s.capitalize()) for s in stems_to_remove]
    removed_str = "+".join(removed_labels)
    if progress_callback:
        progress_callback(f"Mixing removed stems ({removed_str})...", 0.80)

    remove_idxs = set()
    for name in stems_to_remove:
        for i, sn in enumerate(stem_names):
            if sn.lower() == name.lower():
                remove_idxs.add(i)
                break

    if not remove_idxs:
        raise RuntimeError("No valid stems selected for removal")

    mixed = None
    for i, name in enumerate(stem_names):
        if i not in remove_idxs:
            continue
        stem_path = stems_dir / f"{name}.wav"
        stem_audio, _ = sf.read(str(stem_path))
        if mixed is None:
            mixed = stem_audio.astype(np.float64)
        else:
            mixed += stem_audio.astype(np.float64)

    mixed = np.clip(mixed, -1.0, 1.0)

    temp_wav = stems_dir / "temp_removed.wav"
    sf.write(str(temp_wav), mixed, sample_rate)

    if progress_callback:
        progress_callback("Converting removed stems to MP3...", 0.93)

    safe_title = sanitize_filename(title)
    bpm_suffix = f" [{bpm} BPM]" if bpm else ""
    output_filename = f"{safe_title} - Removed ({removed_str}){bpm_suffix}.mp3"
    output_path = OUTPUT_DIR / output_filename

    cmd = [
        FFMPEG_PATH,
        "-i", str(temp_wav),
        "-codec:a", "libmp3lame",
        "-b:a", "320k",
        "-y", str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    return str(output_path)


def cleanup_temp(output_dir: Path):
    shutil.rmtree(output_dir, ignore_errors=True)


def process_url(url: str, stems_to_remove: list[str] | None = None, export_removed: bool = True, shifts: int = 1, progress_callback=None) -> tuple[str, str | None]:
    if not url or not url.strip():
        raise ValueError("Invalid URL")

    if not stems_to_remove:
        stems_to_remove = ["guitar"]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if progress_callback:
        progress_callback(f"Starting processing (device: {device.upper()})...", 0.0)

    OUTPUT_DIR.mkdir(exist_ok=True)

    work_dir = Path(tempfile.mkdtemp(dir=str(TEMP_DIR)))
    TEMP_DIR.mkdir(exist_ok=True)

    title, mp3_path = download_audio(url, work_dir, progress_callback)

    wav_path = convert_to_wav(mp3_path, work_dir, progress_callback)

    bpm = detect_bpm(wav_path, progress_callback)

    stems_dir, stem_names, sample_rate = separate_sources(
        wav_path, work_dir, device, shifts, progress_callback
    )

    output_path = mix_without_stems(
        stems_dir, stem_names, sample_rate, title, stems_to_remove, bpm, progress_callback
    )

    removed_path = None
    if export_removed:
        removed_path = mix_removed_stems(
            stems_dir, stem_names, sample_rate, title, stems_to_remove, bpm, progress_callback
        )

    if progress_callback:
        progress_callback("Done!", 1.0)

    return output_path, removed_path
