"""Desktop GUI for a free, local-only prototype."""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from misophonia.audio import process_file
from misophonia.store import TargetStore


class MisophoniaApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Misophonia Desktop — 音の選択的減衰（試作版）")
        self.root.geometry("740x650")
        self.root.minsize(640, 580)
        self.store = TargetStore()
        self.targets: list[dict[str, str]] = []
        self.source = tk.StringVar()
        self.destination = tk.StringVar()
        self.status = tk.StringVar(value="登録音と処理対象のファイルを指定してください。")
        self.strength = tk.DoubleVar(value=80)
        self.threshold = tk.DoubleVar(value=48)
        self.busy = False
        self._draw()
        self._refresh()

    def _draw(self):
        panel = ttk.Frame(self.root, padding=18)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Misophonia Desktop", font=("", 18, "bold")).pack(anchor="w")
        ttk.Label(
            panel,
            text="登録した音に似た周波数成分を減衰する、無料・オフラインの試作アプリ",
            wraplength=680,
        ).pack(anchor="w", pady=(3, 8))
        ttk.Label(
            panel,
            text="※ AIによる厳密な音源分離・リアルタイムANCではありません。重要な音も減衰する可能性があります。",
            foreground="#9a4f1a", wraplength=680,
        ).pack(anchor="w", pady=(0, 12))

        soundbox = ttk.LabelFrame(panel, text="1. トリガー音を登録・選択", padding=10)
        soundbox.pack(fill="both", pady=(0, 10))
        self.listbox = tk.Listbox(soundbox, selectmode=tk.EXTENDED, height=6, exportselection=False)
        self.listbox.pack(fill="x", pady=(0, 8))
        buttons = ttk.Frame(soundbox)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="音声ファイルを登録", command=self._add).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="マイクで4秒録音", command=self._record).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="すべて選択", command=lambda: self.listbox.select_set(0, tk.END)).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="選択音を削除", command=self._delete).pack(side="left")
        ttk.Label(soundbox, text="複数選択は Ctrl または Shift キー。録音データはPC内のみに保存。").pack(anchor="w", pady=(8, 0))

        filebox = ttk.LabelFrame(panel, text="2. 処理対象と保存先", padding=10)
        filebox.pack(fill="x", pady=(0, 10))
        self._file_row(filebox, "入力ファイル", self.source, self._choose_source)
        self._file_row(filebox, "出力WAV", self.destination, self._choose_destination)

        settings = ttk.LabelFrame(panel, text="3. 減衰パラメータ", padding=10)
        settings.pack(fill="x", pady=(0, 10))
        self._slider_row(settings, "減衰の強さ", self.strength, 0, 100, "%")
        self._slider_row(settings, "判定の厳しさ", self.threshold, 10, 90, "%")
        ttk.Label(
            settings,
            text="音が消えない場合は判定を緩め、ほかの音まで変化する場合は厳しくしてください。",
            wraplength=650,
        ).pack(anchor="w")

        self.process_button = ttk.Button(panel, text="4. ファイルを処理してWAV保存", command=self._process)
        self.process_button.pack(fill="x", ipady=6, pady=(2, 8))
        ttk.Label(panel, textvariable=self.status, wraplength=690).pack(anchor="w")
        ttk.Label(
            panel, text="音声処理は完全ローカル。初回のライブラリ導入以外に通信・会員登録・課金は不要。",
            foreground="#666666", wraplength=690,
        ).pack(anchor="w", pady=(8, 0))

    def _file_row(self, parent, caption, variable, callback):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=caption, width=12).pack(side="left")
        ttk.Entry(row, textvariable=variable, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(row, text="参照…", command=callback).pack(side="right")

    def _slider_row(self, parent, label, variable, start, end, unit):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=14).pack(side="left")
        ttk.Scale(row, variable=variable, from_=start, to=end).pack(side="left", fill="x", expand=True)
        value = ttk.Label(row, width=6)
        value.pack(side="left", padx=(10, 0))
        variable.trace_add("write", lambda *_: value.configure(text=f"{variable.get():.0f}{unit}"))
        value.configure(text=f"{variable.get():.0f}{unit}")

    def _refresh(self):
        self.targets = self.store.list()
        self.listbox.delete(0, tk.END)
        for record in self.targets:
            self.listbox.insert(tk.END, record["name"])
        if self.targets:
            self.listbox.select_set(0, tk.END)

    def _add(self):
        if self.busy:
            return
        source = filedialog.askopenfilename(
            title="登録する音を選択", filetypes=[("音声", "*.wav *.flac *.ogg"), ("すべて", "*.*")]
        )
        if not source:
            return
        try:
            self.store.add_file(source)
            self._refresh()
            self.status.set("トリガー音を登録しました。")
        except Exception as error:
            messagebox.showerror("登録エラー", str(error))

    def _delete(self):
        if self.busy:
            return
        indices = self.listbox.curselection()
        if not indices:
            return
        names = ", ".join(self.targets[i]["name"] for i in indices)
        if not messagebox.askyesno("登録音の削除", f"登録音を削除しますか？\n{names}"):
            return
        self.store.delete({self.targets[i]["id"] for i in indices})
        self._refresh()
        self.status.set("選択した登録音を削除しました。")

    def _record(self):
        if self.busy:
            return
        self._set_busy(True, "4秒間、マイクから録音しています…")
        def worker():
            try:
                import sounddevice as sd
                import numpy as np
                audio = sd.rec(4 * 44100, samplerate=44100, channels=1, dtype="float32")
                sd.wait()
                if float(np.max(np.abs(audio))) < 0.0001:
                    raise ValueError("録音がほぼ無音でした。マイクを確認してください。")
                self.store.add_recording(audio, 44100)
                self.root.after(0, self._record_done)
            except Exception as error:
                self.root.after(0, lambda text=str(error): self._failed(text))
        threading.Thread(target=worker, daemon=True).start()

    def _record_done(self):
        self._refresh()
        self._set_busy(False, "4秒間の録音を登録しました。")

    def _choose_source(self):
        source = filedialog.askopenfilename(
            title="処理する音声", filetypes=[("音声", "*.wav *.flac *.ogg"), ("すべて", "*.*")]
        )
        if source:
            self.source.set(source)
            target = Path(source)
            self.destination.set(str(target.with_name(target.stem + "_filtered.wav")))

    def _choose_destination(self):
        dest = filedialog.asksaveasfilename(
            title="WAVの保存先", defaultextension=".wav",
            filetypes=[("WAV音声", "*.wav")],
            initialfile=Path(self.destination.get()).name if self.destination.get() else "filtered.wav",
        )
        if dest:
            self.destination.set(dest)

    def _set_busy(self, busy: bool, msg: str):
        self.busy = busy
        self.process_button.configure(state="disabled" if busy else "normal")
        self.status.set(msg)

    def _failed(self, reason: str):
        self._set_busy(False, "処理できませんでした。")
        messagebox.showerror("エラー", reason)

    def _process(self):
        if self.busy:
            return
        indices = self.listbox.curselection()
        if not indices:
            messagebox.showinfo("確認", "登録音を1つ以上選択してください。")
            return
        src, dest = self.source.get(), self.destination.get()
        if not src or not dest:
            messagebox.showinfo("確認", "入力ファイルと保存先を指定してください。")
            return
        if Path(dest).exists() and not messagebox.askyesno("上書き確認", "出力ファイルが存在します。上書きしますか？"):
            return
        sample_paths = [self.store.path(self.targets[i]) for i in indices]
        strength = self.strength.get() / 100.0
        threshold = self.threshold.get() / 100.0
        self._set_busy(True, "音声ファイルを処理しています…")
        def worker():
            try:
                process_file(src, sample_paths, dest, strength, threshold)
                self.root.after(0, lambda: self._set_busy(False, f"保存しました：{dest}"))
            except Exception as error:
                self.root.after(0, lambda text=str(error): self._failed(text))
        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    MisophoniaApp(root)
    root.mainloop()
