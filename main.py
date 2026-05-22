import json
import threading
import os
import shutil
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from processor import process_url, OUTPUT_DIR, STEM_NAMES_EN


CONFIG_PATH = Path(__file__).parent / "config.json"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Instrument Remover")
        self.geometry("780x680")
        self.minsize(680, 500)

        self.output_path = None
        self.removed_path = None
        self.config = self._load_config()

        self._build_ui()

    def _load_config(self) -> dict:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def _build_ui(self):
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(5, weight=1)

        title_label = ctk.CTkLabel(
            self, text="\U0001f3b5 Instrument Remover",
            font=ctk.CTkFont(size=26, weight="bold"),
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(22, 2), padx=20, sticky="n")

        subtitle = ctk.CTkLabel(
            self, text="Remove instruments or vocals from any YouTube audio",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        subtitle.grid(row=1, column=0, columnspan=2, pady=(0, 4), padx=20, sticky="n")

        separator = ctk.CTkFrame(self, height=1, fg_color="gray20")
        separator.grid(row=2, column=0, columnspan=2, padx=30, pady=(0, 10), sticky="ew")

        stems_frame = ctk.CTkFrame(self)
        stems_frame.grid(row=3, column=0, padx=(20, 10), pady=(0, 8), sticky="nsew")
        stems_frame.grid_columnconfigure((0, 1, 2), weight=1)
        stems_frame.grid_rowconfigure(0, weight=0)
        stems_frame.grid_rowconfigure(3, weight=0)

        ctk.CTkLabel(
            stems_frame, text="\u2699 Select what to remove:",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).grid(row=0, column=0, columnspan=3, padx=14, pady=(10, 6), sticky="w")

        self.stem_vars = {}
        stem_items = [
            ("drums", "Drums"),
            ("bass", "Bass"),
            ("guitar", "Guitar"),
            ("piano", "Piano"),
            ("other", "Other"),
            ("vocals", "Vocals"),
        ]
        for idx, (stem_key, stem_label) in enumerate(stem_items):
            row = 1 + idx // 3
            col = idx % 3
            var = ctk.BooleanVar(value=(stem_key == "guitar"))
            cb = ctk.CTkCheckBox(
                stems_frame, text=stem_label, variable=var,
                font=ctk.CTkFont(size=12),
                border_width=2,
                corner_radius=4,
            )
            cb.grid(row=row, column=col, padx=14, pady=3, sticky="w")
            self.stem_vars[stem_key] = var

        self.export_removed_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            stems_frame, text="Also export removed instrument as separate file",
            variable=self.export_removed_var,
            font=ctk.CTkFont(size=12),
            border_width=2,
            corner_radius=4,
        ).grid(row=1 + len(stem_items) // 3, column=0, columnspan=3, padx=14, pady=(8, 10), sticky="w")

        quality_frame = ctk.CTkFrame(self)
        quality_frame.grid(row=3, column=1, padx=(10, 20), pady=(0, 8), sticky="nsew")
        quality_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            quality_frame, text="\u2699 Separation Quality",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).grid(row=0, column=0, padx=14, pady=(10, 6), sticky="w")

        self.shifts_label = ctk.CTkLabel(
            quality_frame, text="Shifts: 1",
            font=ctk.CTkFont(size=12), anchor="w",
        )
        self.shifts_label.grid(row=1, column=0, padx=14, pady=(0, 2), sticky="w")

        self.shifts_var = ctk.IntVar(value=1)
        ctk.CTkSlider(
            quality_frame, from_=1, to=10, variable=self.shifts_var,
            number_of_steps=9, command=self._on_shift_change,
            button_corner_radius=6,
            button_length=18,
        ).grid(row=2, column=0, padx=14, pady=(4, 2), sticky="ew")

        ctk.CTkLabel(
            quality_frame, text="Higher shifts = better separation, 1\u00d7\u201310\u00d7 slower",
            font=ctk.CTkFont(size=10), text_color="gray", anchor="w",
        ).grid(row=3, column=0, padx=14, pady=(0, 10), sticky="w")

        url_frame = ctk.CTkFrame(self)
        url_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 8), sticky="ew")
        url_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(url_frame, text="\U0001f517 Source & Output", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(10, 0), sticky="w")

        ctk.CTkLabel(url_frame, text="YouTube Link:", anchor="w").grid(
            row=1, column=0, padx=14, pady=(6, 0), sticky="w"
        )

        self.url_entry = ctk.CTkEntry(
            url_frame, placeholder_text="https://youtube.com/watch?v=..."
        )
        self.url_entry.grid(row=2, column=0, columnspan=2, padx=14, pady=(4, 6), sticky="ew")

        self.process_btn = ctk.CTkButton(
            url_frame, text="\u25b6 Process",
            command=self._start_processing,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
        )
        self.process_btn.grid(row=3, column=0, columnspan=2, padx=14, pady=(2, 0), sticky="ew")

        dest_frame = ctk.CTkFrame(url_frame, fg_color="transparent")
        dest_frame.grid(row=4, column=0, columnspan=2, padx=14, pady=(6, 10), sticky="ew")
        dest_frame.grid_columnconfigure(0, weight=1)

        default_dest = self.config.get("dest_dir", str(OUTPUT_DIR))
        self.dest_dir_var = ctk.StringVar(value=default_dest)
        dest_entry = ctk.CTkEntry(dest_frame, textvariable=self.dest_dir_var, state="readonly")
        dest_entry.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            dest_frame, text="\U0001f4c2 Browse", command=self._browse_dest, width=100,
            corner_radius=6,
        ).grid(row=0, column=1, padx=(6, 0))

        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=5, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="nsew")
        progress_frame.grid_columnconfigure((0, 1), weight=1)

        self.status_icon = "\u25cb"
        self.status_label = ctk.CTkLabel(
            progress_frame, text=f"{self.status_icon} Waiting for URL...", anchor="w",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.grid(row=0, column=0, columnspan=2, padx=14, pady=(8, 2), sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(progress_frame, corner_radius=4)
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=14, pady=(0, 2), sticky="ew")
        self.progress_bar.set(0)

        self.result_label = ctk.CTkLabel(
            progress_frame, text="", anchor="w", wraplength=700,
            font=ctk.CTkFont(size=11),
        )
        self.result_label.grid(row=2, column=0, columnspan=2, padx=14, pady=(2, 0), sticky="ew")

        self.bt_play_btn = ctk.CTkButton(
            progress_frame, text="\u25b6 Play Backing Track",
            command=self._play_audio, state="disabled",
            corner_radius=6,
        )
        self.bt_play_btn.grid(row=3, column=0, padx=(14, 6), pady=(6, 10), sticky="ew")

        self.removed_play_btn = ctk.CTkButton(
            progress_frame, text="\u25b6 Play Removed Instrument",
            command=self._play_removed_audio, state="disabled",
            corner_radius=6,
        )
        self.removed_play_btn.grid(row=3, column=1, padx=(6, 14), pady=(6, 10), sticky="ew")

        footer = ctk.CTkLabel(
            self, text="Powered by Demucs \u00b7 PyTorch \u00b7 NVIDIA RTX 3060",
            font=ctk.CTkFont(size=10), text_color="gray",
        )
        footer.grid(row=6, column=0, columnspan=2, pady=(0, 12), sticky="s")

    def _update_progress(self, text, value):
        prefix = "\u25b6" if 0 < value < 1.0 else "\u2713" if value >= 1.0 else "\u25cb"
        self.status_label.configure(text=f"{prefix} {text}")
        self.progress_bar.set(value)
        self.update_idletasks()

    def _on_shift_change(self, value):
        self.shifts_label.configure(text=f"Shifts: {int(float(value))}")

    def _start_processing(self):
        stems_to_remove = [
            key for key, var in self.stem_vars.items() if var.get()
        ]
        if not stems_to_remove:
            messagebox.showwarning(
                "Warning", "Select at least one instrument/vocal to remove."
            )
            return
        if len(stems_to_remove) == len(self.stem_vars):
            messagebox.showwarning(
                "Warning",
                "Removing all stems will result in silent audio. "
                "Uncheck at least one instrument/vocal to keep.",
            )
            return

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Paste a YouTube link first.")
            return

        self.process_btn.configure(state="disabled", text="Processing...")
        self.bt_play_btn.configure(state="disabled")
        self.removed_play_btn.configure(state="disabled")
        self.result_label.configure(text="")
        self.progress_bar.set(0)
        self.output_path = None
        self.removed_path = None

        thread = threading.Thread(
            target=self._process, args=(url, stems_to_remove), daemon=True
        )
        thread.start()

    def _process(self, url, stems_to_remove):
        try:
            export_removed = self.export_removed_var.get()
            shifts = self.shifts_var.get()
            bt_path, removed_path = process_url(
                url, stems_to_remove, export_removed, shifts, self._update_progress
            )

            dest_dir = self.dest_dir_var.get()
            Path(dest_dir).mkdir(parents=True, exist_ok=True)

            bt_name = os.path.basename(bt_path)
            bt_dest = os.path.join(dest_dir, bt_name)
            shutil.copy2(bt_path, bt_dest)
            self.output_path = bt_dest

            self.removed_path = None
            if removed_path:
                rem_name = os.path.basename(removed_path)
                rem_dest = os.path.join(dest_dir, rem_name)
                shutil.copy2(removed_path, rem_dest)
                self.removed_path = rem_dest

            self.after(0, lambda: self.result_label.configure(
                text=f"✓ Saved to: {dest_dir}"
            ))
            self.after(0, lambda: self.bt_play_btn.configure(state="normal"))
            self.after(0, lambda: self.progress_bar.set(1.0))

            if self.removed_path:
                self.after(0, lambda: self.removed_play_btn.configure(state="normal"))

        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda m=err_msg: self.status_label.configure(
                text=f"\u2717 Error: {m}"
            ))
            self.after(0, lambda: self.result_label.configure(
                text="Check the URL, your connection, or try again."
            ))
        finally:
            self.after(0, lambda: self.process_btn.configure(
                state="normal", text="Process"
            ))

    def _play_audio(self):
        if self.output_path and os.path.exists(self.output_path):
            os.startfile(self.output_path)

    def _play_removed_audio(self):
        if self.removed_path and os.path.exists(self.removed_path):
            os.startfile(self.removed_path)

    def _browse_dest(self):
        folder = filedialog.askdirectory(initialdir=self.dest_dir_var.get())
        if folder:
            self.dest_dir_var.set(folder)
            self.config["dest_dir"] = folder
            self._save_config()


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    app = App()
    app.protocol("WM_DELETE_WINDOW", lambda: (app._save_config(), app.destroy()))
    app.mainloop()
