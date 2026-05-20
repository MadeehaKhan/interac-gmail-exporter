"""Simple tkinter GUI for INTERAC e-Transfer export."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .export_job import run_export

DEFAULT_OUTPUT = "output/interac_transfers.csv"


class InteracExportApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("INTERAC E-Transfer Export")
        self.geometry("520x420")
        self.minsize(480, 380)

        self._running = False
        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 4}
        main = ttk.Frame(self, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="INTERAC E-Transfer → CSV", font=("", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        ttk.Label(main, text="Save to:").grid(row=1, column=0, sticky="w", **pad)
        self.output_var = tk.StringVar(value=DEFAULT_OUTPUT)
        output_entry = ttk.Entry(main, textvariable=self.output_var, width=42)
        output_entry.grid(row=1, column=1, sticky="ew", **pad)

        save_btn = ttk.Button(main, text="💾", width=3, command=self._pick_save_path)
        save_btn.grid(row=1, column=2, **pad)

        ttk.Label(main, text="After (YYYY/MM/DD):").grid(row=2, column=0, sticky="w", **pad)
        self.after_var = tk.StringVar()
        ttk.Entry(main, textvariable=self.after_var, width=20).grid(
            row=2, column=1, sticky="w", **pad
        )

        ttk.Label(main, text="Before (YYYY/MM/DD):").grid(row=3, column=0, sticky="w", **pad)
        self.before_var = tk.StringVar()
        ttk.Entry(main, textvariable=self.before_var, width=20).grid(
            row=3, column=1, sticky="w", **pad
        )

        ttk.Label(main, text="Max emails:").grid(row=4, column=0, sticky="w", **pad)
        self.max_var = tk.StringVar(value="500")
        ttk.Entry(main, textvariable=self.max_var, width=10).grid(
            row=4, column=1, sticky="w", **pad
        )

        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=12)
        self.export_btn = ttk.Button(btn_frame, text="Export", command=self._on_export)
        self.export_btn.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Quit", command=self.destroy).pack(side=tk.LEFT)

        ttk.Label(main, text="Status:").grid(row=6, column=0, sticky="nw", **pad)
        self.status = scrolledtext.ScrolledText(main, height=12, width=55, state="disabled")
        self.status.grid(row=6, column=1, columnspan=2, sticky="nsew", **pad)

        main.columnconfigure(1, weight=1)
        main.rowconfigure(6, weight=1)

    def _pick_save_path(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save CSV as",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=Path(self.output_var.get()).name or "interac_transfers.csv",
            initialdir=str(Path(self.output_var.get()).parent)
            if self.output_var.get()
            else ".",
        )
        if path:
            self.output_var.set(path)

    def _log(self, message: str) -> None:
        def update() -> None:
            self.status.configure(state="normal")
            self.status.insert(tk.END, message + "\n")
            self.status.see(tk.END)
            self.status.configure(state="disabled")

        self.after(0, update)

    def _set_running(self, running: bool) -> None:
        self._running = running
        state = "disabled" if running else "normal"
        self.export_btn.configure(state=state)

    def _on_export(self) -> None:
        if self._running:
            return

        output = self.output_var.get().strip()
        if not output:
            messagebox.showerror("Error", "Please choose an output file path.")
            return

        try:
            max_results = int(self.max_var.get().strip() or "500")
            if max_results < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Max emails must be a positive number.")
            return

        after = self.after_var.get().strip() or None
        before = self.before_var.get().strip() or None

        self.status.configure(state="normal")
        self.status.delete("1.0", tk.END)
        self.status.configure(state="disabled")
        self._set_running(True)

        def worker() -> None:
            try:
                result = run_export(
                    output_path=output,
                    after=after,
                    before=before,
                    max_results=max_results,
                    on_progress=self._log,
                )
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Export complete",
                        f"Found {result.messages_found} emails.\n"
                        f"Fully parsed: {result.parse_ok_count}\n"
                        f"New rows written: {result.rows_written}\n"
                        f"Saved to: {result.output_path}",
                    ),
                )
            except FileNotFoundError as e:
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Missing credentials",
                        str(e) + "\n\nSee README for Google Cloud setup.",
                    ),
                )
            except Exception as e:
                self._log(f"Error: {e}")
                self.after(0, lambda: messagebox.showerror("Export failed", str(e)))
            finally:
                self.after(0, lambda: self._set_running(False))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    app = InteracExportApp()
    app.mainloop()


if __name__ == "__main__":
    main()
