"""
app_ui.py — WhatsApp Bulk Sender GUI
Clean, modern layout. All HTTP calls in background threads.
"""

import os
import io
import sys
import time
import base64
import threading
import subprocess
import requests
import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog, END
from PIL import Image

import whatsapp_auto

SERVER_URL  = "http://127.0.0.1:3000"
_server_proc = None
_log_index   = 0


def api(method, path, **kwargs):
    try:
        r = getattr(requests, method)(f"{SERVER_URL}{path}", timeout=8, **kwargs)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────

class WhatsAppApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("nyoba 123 @dimardnugroho")
        self.geometry("780x700")
        self.minsize(700, 600)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        self.configure(fg_color="#25D366")
        self.after(200, self._show_splash)

    # ─── Splash ──────────────────────────────────────────────────────────────

    def _show_splash(self):
        self._splash = ctk.CTkLabel(
            self, text="💬 Dimas gans123",
            font=("Poppins", 34, "bold"), text_color="#ffffff"
        )
        self._splash.place(relx=0.5, rely=0.5, anchor="center")

        for i in range(20):
            self.update()
            time.sleep(0.04)

        time.sleep(0.6)
        self._splash.destroy()
        self._build_ui()

    # ─── Main UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Root container (scrollable card)
        self.card = ctk.CTkScrollableFrame(self, fg_color="#f7fdf8", corner_radius=20)
        self.card.pack(fill="both", expand=True, padx=14, pady=14)

        # ── Title ────────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self.card, text="💬 Dimas gans123",
            font=("Poppins", 22, "bold"), text_color="#128C7E"
        ).pack(pady=(18, 10))

        # ── Engine Mode Switch ───────────────────────────────────────────────
        self.engine_mode = ctk.StringVar(value="Mode Cepat (Node.js)")
        self.engine_selector = ctk.CTkSegmentedButton(
            self.card, values=["Mode Cepat (Node.js)", "Mode Aman (Selenium)"],
            variable=self.engine_mode,
            command=self._on_engine_change,
            font=("Poppins", 12), height=34,
            fg_color="#eafaf1", selected_color="#128C7E", selected_hover_color="#0a6b5e"
        )
        self.engine_selector.pack(fill="x", padx=30, pady=(0, 18))

        # ── Status row ───────────────────────────────────────────────────────
        self._build_status_row()

        # ── QR slot (hidden until needed) ────────────────────────────────────
        self.qr_slot = ctk.CTkFrame(self.card, fg_color="transparent", height=0)
        self.qr_slot.pack(fill="x", padx=30)
        self._qr_inner   = None
        self._qr_visible = False
        
        # ── Form ─────────────────────────────────────────────────────────────
        self._build_form()

        # ── Action buttons ───────────────────────────────────────────────────
        self._build_action_buttons()

        # ── Progress bar ─────────────────────────────────────────────────────
        self._build_progress()

        # ── Log area ─────────────────────────────────────────────────────────
        self._build_log()

        # ── Start background threads ──────────────────────────────────────────
        threading.Thread(target=self._status_worker,   daemon=True).start()
        threading.Thread(target=self._log_worker,      daemon=True).start()
        threading.Thread(target=self._progress_worker, daemon=True).start()

    def _on_engine_change(self, value):
        if value == "Mode Aman (Selenium)":
            self.start_btn.configure(text="🌐 Buka Chrome (Selenium)", command=self._start_selenium)
            self.stop_btn.configure(text="⏹ Tutup Chrome", command=self._stop_selenium)
            self._hide_qr()
            self.status_dot.configure(text="⚪")
            self.status_lbl.configure(text="Klik Start untuk membuka Browser Chrome.", text_color="#888")
            self.send_btn.configure(state="normal")
        else:
            self.start_btn.configure(text="▶ Start WA Server", command=self._start_server_thread)
            self.stop_btn.configure(text="⏹ Ganti Akun", command=self._stop_server_thread)
            self.status_dot.configure(text="⚪")
            self.status_lbl.configure(text="Server belum berjalan", text_color="#888")
            self.send_btn.configure(state="disabled")

    def _start_selenium(self):
        self.start_btn.configure(state="disabled", text="⏳ Membuka...")
        self.status_lbl.configure(text="Membuka browser Chrome...", text_color="#128C7E")
        def run():
            try:
                whatsapp_auto.launch_chrome()
                self.after(0, lambda: self._append_log("🌐 Chrome terbuka. Silakan hubungkan WhatsApp/scan QR secara manual di browser tersebut."))
                self.after(0, lambda: self.status_lbl.configure(text="Chrome aktif", text_color="#128C7E"))
                self.after(0, lambda: self.status_dot.configure(text="🟢"))
                self.after(0, lambda: self.start_btn.configure(state="normal", text="✅ Chrome Terbuka"))
                self.after(0, lambda: self.send_btn.configure(state="normal"))
            except Exception as e:
                self.after(0, lambda: self._append_log(f"❌ Gagal buka Chrome: {e}"))
                self.after(0, lambda: self.start_btn.configure(state="normal", text="🌐 Buka Chrome (Selenium)"))
        threading.Thread(target=run, daemon=True).start()
        
    def _stop_selenium(self):
        whatsapp_auto.quit_driver()
        self.status_lbl.configure(text="Chrome ditutup.", text_color="#888")
        self.status_dot.configure(text="⚪")
        self.start_btn.configure(state="normal", text="🌐 Buka Chrome (Selenium)")
        self.send_btn.configure(state="disabled")

    # ─── Spintax Builder ─────────────────────────────────────────────────────

    def _open_spintax_builder(self):
        popup = ctk.CTkToplevel(self)
        popup.title("🛠 Buat Spintax Kustom")
        popup.geometry("450x320")
        popup.resizable(False, False)
        popup.grab_set()
        popup.lift()
        popup.focus_force()
        popup.configure(fg_color="#f7fdf8")

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 450) // 2
        y = self.winfo_y() + (self.winfo_height() - 320) // 2
        popup.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            popup, text="Buat Variasi Kata (Spintax)",
            font=("Poppins", 14, "bold"), text_color="#128C7E"
        ).pack(pady=(25, 5))

        ctk.CTkLabel(
            popup, text="Masukkan kata-kata pengganti dipisah dengan koma (,)",
            font=("Poppins", 11), text_color="#555"
        ).pack(pady=(0, 15))

        entry = ctk.CTkEntry(
            popup, font=("Poppins", 12), height=40, corner_radius=8,
            placeholder_text="Contoh: Halo, Hai, Selamat Pagi"
        )
        entry.pack(fill="x", padx=40, pady=(0, 20))
        
        def _apply():
            raw = entry.get()
            if not raw.strip(): return
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            if parts:
                spintax_str = "{" + "|".join(parts) + "}"
                self.msg_text.insert(ctk.END, spintax_str)
            popup.destroy()

        ctk.CTkButton(
            popup, text="➕ Tambahkan ke Pesan", height=40,
            fg_color="#25D366", hover_color="#1db954",
            font=("Poppins", 12, "bold"), corner_radius=8,
            command=_apply
        ).pack(fill="x", padx=40, pady=(0, 10))

        ctk.CTkButton(
            popup, text="Batal", height=40,
            fg_color="#bdc3c7", hover_color="#95a5a6", text_color="#333",
            font=("Poppins", 12), corner_radius=8,
            command=popup.destroy
        ).pack(fill="x", padx=40)

    # ─── Sub-builders ────────────────────────────────────────────────────────

    def _build_status_row(self):
        row = ctk.CTkFrame(self.card, fg_color="#e8f8f2", corner_radius=12)
        row.pack(fill="x", padx=30, pady=(0, 8))

        self.status_dot = ctk.CTkLabel(
            row, text="⚪", font=("Poppins", 16), width=28
        )
        self.status_dot.pack(side="left", padx=(14, 4), pady=10)

        self.status_lbl = ctk.CTkLabel(
            row, text="Server belum berjalan",
            font=("Poppins", 12), text_color="#888", anchor="w"
        )
        self.status_lbl.pack(side="left", pady=10, fill="x", expand=True)

        self.start_btn = ctk.CTkButton(
            row,
            text="▶  Start WA Server",
            width=160, height=34,
            fg_color="#128C7E", hover_color="#0a6b5e",
            font=("Poppins", 12, "bold"),
            corner_radius=8,
            command=self._start_server_thread,
        )
        self.start_btn.pack(side="right", padx=14, pady=10)

    def _build_form(self):
        P = {"padx": 30, "pady": (0, 4), "fill": "x"}

        # Contacts
        ctk.CTkLabel(
            self.card, text="File Kontak", font=("Poppins", 12, "bold"),
            anchor="w", text_color="#333"
        ).pack(**P)

        row1 = ctk.CTkFrame(self.card, fg_color="transparent")
        row1.pack(fill="x", padx=30, pady=(0, 10))
        self.contacts_entry = ctk.CTkEntry(
            row1, font=("Poppins", 12), height=36, corner_radius=8,
            placeholder_text="Pilih file .txt berisi nomor kontak..."
        )
        self.contacts_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            row1, text="Browse", width=90, height=36,
            fg_color="#128C7E", hover_color="#0a6b5e",
            font=("Poppins", 12), corner_radius=8,
            command=self._browse_contacts
        ).pack(side="right")

        # Image
        ctk.CTkLabel(
            self.card, text="File Gambar  (opsional)", font=("Poppins", 12, "bold"),
            anchor="w", text_color="#333"
        ).pack(**P)

        row2 = ctk.CTkFrame(self.card, fg_color="transparent")
        row2.pack(fill="x", padx=30, pady=(0, 10))
        self.image_entry = ctk.CTkEntry(
            row2, font=("Poppins", 12), height=36, corner_radius=8,
            placeholder_text="Opsional — pilih gambar (.jpg / .png)..."
        )
        self.image_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            row2, text="Browse", width=90, height=36,
            fg_color="#128C7E", hover_color="#0a6b5e",
            font=("Poppins", 12), corner_radius=8,
            command=self._browse_image
        ).pack(side="right")

        # Message header
        msg_hdr = ctk.CTkFrame(self.card, fg_color="transparent")
        msg_hdr.pack(fill="x", padx=30, pady=(0, 4))
        ctk.CTkLabel(
            msg_hdr, text="Isi Pesan", font=("Poppins", 12, "bold"),
            anchor="w", text_color="#333"
        ).pack(side="left")
        ctk.CTkButton(
            msg_hdr, text="🛠 Buat Spintax", width=120, height=26,
            fg_color="#3498db", hover_color="#2980b9",
            font=("Poppins", 11), corner_radius=6,
            command=self._open_spintax_builder
        ).pack(side="right")

        msg_wrap = ctk.CTkFrame(
            self.card, fg_color="#fff",
            border_color="#b2dfdb", border_width=1, corner_radius=10
        )
        msg_wrap.pack(fill="x", padx=30, pady=(0, 2))
        self.msg_text = ctk.CTkTextbox(
            msg_wrap, height=90, font=("Poppins", 12),
            fg_color="transparent", border_width=0
        )
        self.msg_text.pack(fill="x", padx=6, pady=6)
        
        ctk.CTkLabel(
            self.card, text="💡 Tips: Gunakan format Spintax {Halo|Hai|Pagi} untuk mengacak variasi pesan.",
            font=("Poppins", 10, "italic"), text_color="#128C7E", anchor="w"
        ).pack(fill="x", padx=34, pady=(0, 10))

        # ── Pengaturan Pengiriman ────────────────────────────────────────────
        settings = ctk.CTkFrame(
            self.card, fg_color="#eafaf1", corner_radius=12
        )
        settings.pack(fill="x", padx=30, pady=(0, 10))

        ctk.CTkLabel(
            settings, text="⚙️  Pengaturan Pengiriman",
            font=("Poppins", 11, "bold"), text_color="#128C7E"
        ).pack(anchor="w", padx=14, pady=(10, 4))

        # Row 1 — random delay
        row_delay = ctk.CTkFrame(settings, fg_color="transparent")
        row_delay.pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkLabel(row_delay, text="Jeda Acak:", font=("Poppins", 11), width=80, anchor="w").pack(side="left")

        ctk.CTkLabel(row_delay, text="Min", font=("Poppins", 10), text_color="#888").pack(side="left", padx=(4, 2))
        self.min_delay_var = ctk.IntVar(value=1)
        self.min_delay_lbl = ctk.CTkLabel(row_delay, text="1s", font=("Poppins", 10, "bold"), text_color="#128C7E", width=28)
        ctk.CTkSlider(
            row_delay, from_=0, to=30, number_of_steps=30,
            variable=self.min_delay_var, width=130,
            command=lambda v: self.min_delay_lbl.configure(text=f"{int(float(v))}s")
        ).pack(side="left", padx=(0, 4))
        self.min_delay_lbl.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(row_delay, text="Max", font=("Poppins", 10), text_color="#888").pack(side="left", padx=(0, 2))
        self.max_delay_var = ctk.IntVar(value=5)
        self.max_delay_lbl = ctk.CTkLabel(row_delay, text="5s", font=("Poppins", 10, "bold"), text_color="#128C7E", width=28)
        ctk.CTkSlider(
            row_delay, from_=0, to=60, number_of_steps=60,
            variable=self.max_delay_var, width=130,
            command=lambda v: self.max_delay_lbl.configure(text=f"{int(float(v))}s")
        ).pack(side="left", padx=(0, 4))
        self.max_delay_lbl.pack(side="left")

        # Row 2 — batch mode
        row_batch = ctk.CTkFrame(settings, fg_color="transparent")
        row_batch.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(row_batch, text="Batch Mode:", font=("Poppins", 11), width=80, anchor="w").pack(side="left")

        self.batch_enabled = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            row_batch, text="", variable=self.batch_enabled,
            width=24, checkbox_width=20, checkbox_height=20,
            fg_color="#128C7E", hover_color="#0a6b5e",
            command=self._toggle_batch_ui
        ).pack(side="left", padx=(0, 8))

        self.batch_size_lbl = ctk.CTkLabel(row_batch, text="Setiap", font=("Poppins", 11), text_color="#555")
        self.batch_size_lbl.pack(side="left")

        self.batch_size_var = ctk.StringVar(value="50")
        self.batch_size_entry = ctk.CTkEntry(
            row_batch, textvariable=self.batch_size_var,
            width=60, height=28, font=("Poppins", 11), justify="center"
        )
        self.batch_size_entry.pack(side="left", padx=6)

        self.batch_pause_lbl1 = ctk.CTkLabel(row_batch, text="pesan, istirahat", font=("Poppins", 11), text_color="#555")
        self.batch_pause_lbl1.pack(side="left")

        self.batch_pause_var = ctk.StringVar(value="5")
        self.batch_pause_entry = ctk.CTkEntry(
            row_batch, textvariable=self.batch_pause_var,
            width=52, height=28, font=("Poppins", 11), justify="center"
        )
        self.batch_pause_entry.pack(side="left", padx=6)

        self.batch_pause_lbl2 = ctk.CTkLabel(row_batch, text="menit", font=("Poppins", 11), text_color="#555")
        self.batch_pause_lbl2.pack(side="left")

        # Initial batch UI state
        self._toggle_batch_ui()

    def _toggle_batch_ui(self):
        enabled = self.batch_enabled.get()
        state   = "normal" if enabled else "disabled"
        color   = "#333" if enabled else "#aaa"
        for w in (self.batch_size_lbl, self.batch_pause_lbl1, self.batch_pause_lbl2):
            w.configure(text_color=color)
        self.batch_size_entry.configure(state=state)
        self.batch_pause_entry.configure(state=state)

    def _build_action_buttons(self):
        outer = ctk.CTkFrame(self.card, fg_color="transparent")
        outer.pack(fill="x", padx=30, pady=(0, 10))

        # Row 1 — Send (full width)
        self.send_btn = ctk.CTkButton(
            outer,
            text="🚀  Kirim Pesan",
            height=46,
            fg_color="#25D366", hover_color="#1db954",
            font=("Poppins", 14, "bold"),
            corner_radius=10,
            command=self._preview_send,
            state="disabled",
        )
        self.send_btn.pack(fill="x", pady=(0, 8))

        # Row 2 — Restart | Stop Kirim | Stop & Ganti Akun
        row2 = ctk.CTkFrame(outer, fg_color="transparent")
        row2.pack(fill="x")
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)
        row2.columnconfigure(2, weight=1)

        self.restart_btn = ctk.CTkButton(
            row2,
            text="🔄  Restart Server",
            height=38,
            fg_color="#128C7E", hover_color="#0a6b5e",
            font=("Poppins", 11),
            corner_radius=10,
            command=lambda: threading.Thread(
                target=lambda: api("post", "/restart"), daemon=True
            ).start(),
        )
        self.restart_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.stop_send_btn = ctk.CTkButton(
            row2,
            text="⏹  Stop Kirim",
            height=38,
            fg_color="#e67e22", hover_color="#ca6f1e",
            font=("Poppins", 11),
            corner_radius=10,
            command=self._stop_send_action,
        )
        self.stop_send_btn.grid(row=0, column=1, sticky="ew", padx=(0, 5))

        self.stop_btn = ctk.CTkButton(
            row2,
            text="⏹  Ganti Akun",
            height=38,
            fg_color="#c0392b", hover_color="#a93226",
            font=("Poppins", 11),
            corner_radius=10,
            command=self._stop_server_thread,
        )
        self.stop_btn.grid(row=0, column=2, sticky="ew")

    def _build_log(self):
        ctk.CTkLabel(
            self.card, text="Log Aktivitas", font=("Poppins", 12, "bold"),
            anchor="w", text_color="#333"
        ).pack(fill="x", padx=30, pady=(0, 3))

        log_wrap = ctk.CTkFrame(
            self.card, fg_color="#fff",
            border_color="#b2dfdb", border_width=1, corner_radius=10,
            height=200
        )
        log_wrap.pack_propagate(False) # prevent shrinking
        log_wrap.pack(fill="x", padx=30, pady=(0, 16))
        self.log_box = ctk.CTkTextbox(
            log_wrap, font=("Poppins", 11),
            fg_color="transparent", border_width=0,
            text_color="#333"
        )
        self.log_box.pack(fill="both", expand=True, padx=6, pady=6)

    def _build_progress(self):
        """Progress bar panel — hidden until a send session is active."""
        self.progress_frame = ctk.CTkFrame(
            self.card, fg_color="#eafaf1", corner_radius=12
        )
        # Do NOT pack yet — will be revealed when sending starts

        inner = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkLabel(
            inner, text="📨 Progress Pengiriman",
            font=("Poppins", 11, "bold"), text_color="#128C7E"
        ).pack(side="left")

        self.progress_count_lbl = ctk.CTkLabel(
            inner, text="0 dari 0 pesan",
            font=("Poppins", 11, "bold"), text_color="#128C7E"
        )
        self.progress_count_lbl.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            height=18, corner_radius=9,
            fg_color="#c8f0e0",
            progress_color="#25D366",
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=(4, 6))

        self.progress_pct_lbl = ctk.CTkLabel(
            self.progress_frame, text="0%",
            font=("Poppins", 10), text_color="#555"
        )
        self.progress_pct_lbl.pack(pady=(0, 8))


    # ─── Background workers ───────────────────────────────────────────────────

    def _status_worker(self):
        while True:
            if not hasattr(self, 'engine_mode') or self.engine_mode.get() != "Mode Aman (Selenium)":
                data = api("get", "/status")
                if data:
                    self.after(0, lambda d=data: self._update_status_ui(d))
            time.sleep(2)

    def _log_worker(self):
        global _log_index
        while True:
            if not hasattr(self, 'engine_mode') or self.engine_mode.get() != "Mode Aman (Selenium)":
                data = api("get", f"/logs?since={_log_index}")
                if data:
                    for entry in data:
                        self.after(0, lambda m=entry["msg"]: self._append_log(m))
                        _log_index = max(_log_index, entry["index"] + 1)
            time.sleep(1)

    def _progress_worker(self):
        """Poll /progress every second and update progress bar UI."""
        while True:
            if not hasattr(self, 'engine_mode') or self.engine_mode.get() != "Mode Aman (Selenium)":
                data = api("get", "/progress")
                if data:
                    self.after(0, lambda d=data: self._update_progress_ui(d))
            time.sleep(1)

    # ─── UI updaters (main thread) ────────────────────────────────────────────

    def _update_status_ui(self, data):
        state = data.get("state", "")
        ready = data.get("ready", False)

        if ready:
            self.status_dot.configure(text="🟢")
            self.status_lbl.configure(
                text="WhatsApp siap — bisa kirim pesan!", text_color="#128C7E"
            )
            self.send_btn.configure(state="normal")
            self._hide_qr()

        elif state == "QR_READY":
            self.status_dot.configure(text="🟡")
            self.status_lbl.configure(
                text="Scan QR di bawah ini dengan WhatsApp Anda", text_color="#e67e22"
            )
            self.send_btn.configure(state="disabled")
            if not self._qr_visible:
                threading.Thread(target=self._fetch_and_show_qr, daemon=True).start()

        elif state in ("INITIALIZING", "LOADING", "AUTHENTICATED"):
            self.status_dot.configure(text="🔵")
            self.status_lbl.configure(
                text=f"Memuat... ({state})", text_color="#3498db"
            )
            self.send_btn.configure(state="disabled")

        elif state == "DISCONNECTED":
            self.status_dot.configure(text="🔴")
            self.status_lbl.configure(
                text="Terputus dari WhatsApp", text_color="#e74c3c"
            )
            self.send_btn.configure(state="disabled")
            self._hide_qr()

        elif state == "AUTH_FAILURE":
            self.status_dot.configure(text="❌")
            self.status_lbl.configure(
                text="Autentikasi gagal — klik Restart Server", text_color="#e74c3c"
            )
            self.send_btn.configure(state="disabled")

    def _append_log(self, msg):
        self.log_box.insert(END, msg + "\n")
        self.log_box.see(END)

    def _update_progress_ui(self, data):
        """Reflect /progress data onto the progress bar panel."""
        sending = data.get("sending", False)
        sent    = data.get("sent",  0)
        total   = data.get("total", 0)

        if sending and total > 0:
            # Show panel (insert before log area, after action buttons)
            if not self.progress_frame.winfo_ismapped():
                self.progress_frame.pack(
                    fill="x", padx=30, pady=(0, 8),
                    before=self.log_box.master   # insert before log_wrap
                )
            ratio = sent / total
            self.progress_bar.set(ratio)
            self.progress_count_lbl.configure(
                text=f"{sent} dari {total} pesan"
            )
            self.progress_pct_lbl.configure(
                text=f"{int(ratio * 100)}%"
            )
        else:
            # Hide panel when done / idle
            if self.progress_frame.winfo_ismapped():
                self.progress_frame.pack_forget()

    # ─── QR ──────────────────────────────────────────────────────────────────

    def _fetch_and_show_qr(self):
        data = api("get", "/qr")
        if not data or not data.get("qr"):
            time.sleep(2)
            threading.Thread(target=self._fetch_and_show_qr, daemon=True).start()
            return
        try:
            b64 = data["qr"].split(",", 1)[1]
            img = Image.open(io.BytesIO(base64.b64decode(b64))).resize(
                (200, 200), Image.LANCZOS
            )
            ctk_img = ctk.CTkImage(light_image=img, size=(200, 200))
            self.after(0, lambda: self._render_qr(ctk_img))
        except Exception as e:
            self.after(0, lambda: self._append_log(f"⚠️ Gagal render QR: {e}"))

    def _render_qr(self, ctk_img):
        if self._qr_inner:
            self._qr_inner.destroy()

        self._qr_inner = ctk.CTkFrame(
            self.qr_slot, fg_color="#fff",
            corner_radius=12, border_color="#25D366", border_width=1
        )
        self._qr_inner.pack(fill="x", pady=(4, 8))

        inner_row = ctk.CTkFrame(self._qr_inner, fg_color="transparent")
        inner_row.pack(pady=10)

        lbl = ctk.CTkLabel(inner_row, text="", image=ctk_img)
        lbl.image = ctk_img
        lbl.pack(side="left", padx=12)

        ctk.CTkLabel(
            inner_row,
            text="📱 Buka WhatsApp di HP\n→ Perangkat Tertaut\n→ Tautkan Perangkat\n→ Scan QR ini",
            font=("Poppins", 12), text_color="#444",
            justify="left"
        ).pack(side="left", padx=12)

        self._qr_visible = True

    def _hide_qr(self):
        if self._qr_visible and self._qr_inner:
            self._qr_inner.destroy()
            self._qr_inner   = None
            self._qr_visible = False

    # ─── Server start ─────────────────────────────────────────────────────────

    def _start_server_thread(self):
        self.start_btn.configure(state="disabled", text="⏳  Memulai...")
        self.status_lbl.configure(text="Memulai server...", text_color="#e67e22")
        threading.Thread(target=self._start_server, daemon=True).start()

    def _stop_server_thread(self):
        self.stop_btn.configure(state="disabled", text="⏳  Menghentikan...")
        self.status_lbl.configure(text="Menghentikan server...", text_color="#e67e22")
        threading.Thread(target=self._stop_server, daemon=True).start()

    def _start_server(self):
        global _server_proc
        # 1. Kill any process on port 3000
        os.system("lsof -ti:3000 | xargs kill -9 2>/dev/null")
        # 2. Kill any lingering Chromium holding the wwebjs_auth lock
        os.system("pkill -f 'wwebjs_auth' 2>/dev/null")
        time.sleep(0.8)
        # 3. Delete stale lock files directly
        base = os.path.dirname(os.path.abspath(__file__))
        session_dir = os.path.join(base, "wwebjs_auth", "session")
        for lock in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            lp = os.path.join(session_dir, lock)
            if os.path.exists(lp):
                try:
                    os.remove(lp)
                except Exception:
                    pass

        script = os.path.join(base, "wa_server.js")
        _server_proc = subprocess.Popen(
            ["node", script],
            cwd=base,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(30):
            time.sleep(1)
            if api("get", "/status"):
                self.after(0, lambda: self.start_btn.configure(
                    state="normal", text="✅  Server Aktif"
                ))
                return

        self.after(0, lambda: (
            self.status_lbl.configure(text="❌ Server gagal dimulai", text_color="#e74c3c"),
            self.start_btn.configure(state="normal", text="▶  Start WA Server"),
        ))

    def _stop_server(self):
        """Stop the server and delete session so next start shows fresh QR."""
        global _server_proc

        self.after(0, lambda: self._append_log("🚪 Menghentikan server & menghapus sesi..."))

        # 1. Ask server to logout + delete its own session files
        api("post", "/logout")
        time.sleep(1.5)  # give node time to clean up before we force-kill

        # 2. Kill the server process
        if _server_proc:
            try:
                _server_proc.terminate()
                _server_proc.wait(timeout=3)
            except Exception:
                pass
            _server_proc = None

        # 3. Force-kill any lingering Chromium on wwebjs_auth
        os.system("pkill -f 'wwebjs_auth' 2>/dev/null")
        os.system("lsof -ti:3000 | xargs kill -9 2>/dev/null")

        # 4. Delete the entire wwebjs_auth folder (fresh start next time)
        base          = os.path.dirname(os.path.abspath(__file__))
        wwebjs_dir    = os.path.join(base, "wwebjs_auth")
        import shutil
        if os.path.exists(wwebjs_dir):
            try:
                shutil.rmtree(wwebjs_dir, ignore_errors=True)
            except Exception:
                pass

        # 5. Reset UI
        def _reset_ui():
            self._hide_qr()
            self.send_btn.configure(state="disabled")
            self.status_dot.configure(text="⚪")
            self.status_lbl.configure(
                text="Server dihentikan — tekan Start untuk akun baru",
                text_color="#888"
            )
            self.start_btn.configure(state="normal", text="▶  Start WA Server")
            self.stop_btn.configure(state="normal", text="⏹  Stop & Ganti Akun")
            self._append_log(
                "✅ Server dihentikan. Data sesi dihapus.\n"
                "   Klik '▶ Start WA Server' untuk login akun WA baru."
            )

        self.after(0, _reset_ui)

    # ─── Preview & Send ───────────────────────────────────────────────────────

    def _preview_send(self):
        """Validate inputs then show confirmation popup before sending."""
        contacts_file = self.contacts_entry.get().strip()
        message       = self.msg_text.get("1.0", END).strip()
        image_path    = self.image_entry.get().strip()
        min_delay     = self.min_delay_var.get()
        max_delay     = self.max_delay_var.get()

        # Ensure min <= max
        if min_delay > max_delay:
            min_delay, max_delay = max_delay, min_delay

        batch_size  = 0
        batch_pause = 5
        if self.batch_enabled.get():
            try:
                batch_size  = int(self.batch_size_var.get())
                batch_pause = float(self.batch_pause_var.get())
            except ValueError:
                self._append_log("⚠️ Batch size dan pause harus berupa angka.")
                return

        if not contacts_file or not os.path.exists(contacts_file):
            self._append_log("⚠️ Pilih file kontak yang valid.")
            return
        if not message and not (image_path and os.path.exists(image_path)):
            self._append_log("⚠️ Tulis pesan atau pilih gambar terlebih dahulu.")
            return

        with open(contacts_file, "r", encoding="utf-8") as f:
            contacts = [ln.strip() for ln in f if ln.strip()]

        if not contacts:
            self._append_log("⚠️ File kontak kosong.")
            return

        # ── Build & show confirmation popup ──────────────────────────────────
        popup = ctk.CTkToplevel(self)
        popup.title("Preview & Konfirmasi Pengiriman")
        popup.geometry("520x540")
        popup.resizable(False, False)
        popup.grab_set()          # modal
        popup.lift()
        popup.focus_force()
        popup.configure(fg_color="#f7fdf8")

        # Center relative to main window
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 540) // 2
        popup.geometry(f"520x540+{x}+{y}")

        # Title bar
        hdr = ctk.CTkFrame(popup, fg_color="#128C7E", corner_radius=0, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr, text="📋  Preview Pesan",
            font=("Poppins", 15, "bold"), text_color="#ffffff"
        ).pack(side="left", padx=20, pady=14)

        body = ctk.CTkScrollableFrame(popup, fg_color="#f7fdf8", corner_radius=0)
        body.pack(fill="both", expand=True, padx=0, pady=0)

        def _section(label, value, value_color="#222"):
            """Helper: renders one info row inside the popup."""
            row = ctk.CTkFrame(body, fg_color="#eafaf1", corner_radius=10)
            row.pack(fill="x", padx=20, pady=(8, 0))
            ctk.CTkLabel(
                row, text=label,
                font=("Poppins", 10, "bold"), text_color="#128C7E", anchor="w"
            ).pack(fill="x", padx=14, pady=(8, 2))
            ctk.CTkLabel(
                row, text=value,
                font=("Poppins", 11), text_color=value_color,
                anchor="w", wraplength=440, justify="left"
            ).pack(fill="x", padx=14, pady=(0, 8))

        # ── Info rows ────────────────────────────────────────────────────────
        _section("📇 Jumlah Kontak",
                 f"{len(contacts)} nomor  (dari {os.path.basename(contacts_file)})",
                 "#128C7E")

        # Message preview (truncate if long)
        msg_preview = message if message else "— (tidak ada teks) —"
        if len(msg_preview) > 280:
            msg_preview = msg_preview[:280] + "..."
        _section("💬 Isi Pesan", msg_preview)

        # Image info
        if image_path and os.path.exists(image_path):
            img_info = os.path.basename(image_path)
            size_kb  = os.path.getsize(image_path) // 1024
            _section("🖼️  Gambar", f"{img_info}  ({size_kb} KB)", "#128C7E")

            # Thumbnail
            try:
                thumb = Image.open(image_path)
                thumb.thumbnail((200, 120), Image.LANCZOS)
                ctk_thumb = ctk.CTkImage(light_image=thumb,
                                         size=(thumb.width, thumb.height))
                thumb_lbl = ctk.CTkLabel(body, text="", image=ctk_thumb,
                                         fg_color="transparent")
                thumb_lbl.image = ctk_thumb
                thumb_lbl.pack(pady=(4, 0))
            except Exception:
                pass
        else:
            _section("🖼️  Gambar", "— (tidak ada gambar)")

        _section("⏱️  Jeda Antar Pesan", f"{min_delay}s – {max_delay}s")

        if self.batch_enabled.get() and batch_size > 0:
            _section("📦 Batch Mode",
                     f"Setiap {batch_size} pesan → istirahat {batch_pause} menit")

        # Estimated time
        avg_delay   = (min_delay + max_delay) / 2
        est_seconds = len(contacts) * max(avg_delay, 1)
        if est_seconds < 60:
            est_str = f"~{int(est_seconds)} detik"
        else:
            est_str = f"~{est_seconds / 60:.1f} menit"
        _section("🕐 Estimasi Waktu", est_str, "#e67e22")

        # Warning note
        note = ctk.CTkLabel(
            body,
            text="⚠️  Pastikan semua data di atas sudah benar sebelum melanjutkan.",
            font=("Poppins", 10), text_color="#c0392b",
            wraplength=460, justify="left"
        )
        note.pack(padx=20, pady=(12, 4), anchor="w")

        # ── Footer buttons ───────────────────────────────────────────────────
        footer = ctk.CTkFrame(popup, fg_color="#e8f8f2", corner_radius=0, height=64)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        def _confirm():
            popup.destroy()
            self._do_send(contacts, message, image_path,
                          min_delay, max_delay, batch_size, batch_pause)

        ctk.CTkButton(
            footer, text="✅  Kirim Sekarang",
            width=200, height=40,
            fg_color="#25D366", hover_color="#1db954",
            font=("Poppins", 12, "bold"), corner_radius=10,
            command=_confirm
        ).pack(side="right", padx=16, pady=12)

        ctk.CTkButton(
            footer, text="✏️  Batal / Edit",
            width=160, height=40,
            fg_color="#bdc3c7", hover_color="#95a5a6",
            text_color="#333",
            font=("Poppins", 12), corner_radius=10,
            command=popup.destroy
        ).pack(side="right", padx=(0, 8), pady=12)

    def _stop_send_action(self):
        if hasattr(self, 'engine_mode') and self.engine_mode.get() == "Mode Aman (Selenium)":
            if hasattr(self, "_selenium_stop_event"):
                self._selenium_stop_event.set()
                self._append_log("⛔ Mengirim sinyal stop ke Selenium...")
        else:
            threading.Thread(target=lambda: api("post", "/stop-send"), daemon=True).start()

    def _do_send(self, contacts, message, image_path,
                 min_delay, max_delay, batch_size, batch_pause):
        """Actually send — called after user confirms in the preview popup."""
        mode = self.engine_mode.get() if hasattr(self, 'engine_mode') else "Mode Cepat (Node.js)"

        def _send_node():
            self.after(0, lambda: self.send_btn.configure(
                state="disabled", text="⏳  Mengirim..."
            ))
            resp = api("post", "/send", json={
                "contacts":   contacts,
                "message":    message,
                "imagePath":  image_path if image_path and os.path.exists(image_path) else "",
                "minDelay":   min_delay,
                "maxDelay":   max_delay,
                "batchSize":  batch_size,
                "batchPause": batch_pause,
            })
            if not resp or not resp.get("ok"):
                err = (resp or {}).get("error", "Gagal terhubung ke server.")
                self.after(0, lambda: self._append_log(f"❌ {err}"))
                self.after(0, lambda: self.send_btn.configure(
                    state="normal", text="🚀  Kirim Pesan"
                ))
                return
            total_ms = int((len(contacts) * max(max_delay, 0.5) + 12) * 1000)
            self.after(total_ms, lambda: self.send_btn.configure(
                state="normal", text="🚀  Kirim Pesan"
            ))

        def _send_selenium():
            self.after(0, lambda: self.send_btn.configure(state="disabled", text="⏳ Mengirim..."))
            self.after(0, lambda: self._update_progress_ui({"sending": True, "sent": 0, "total": len(contacts)}))
            
            self._selenium_stop_event = threading.Event()
            
            def pcb(sent, total):
                self.after(0, lambda: self._update_progress_ui({"sending": True, "sent": sent, "total": total}))
            
            res = whatsapp_auto.send_whatsapp_messages(
                contacts=contacts,
                message=message,
                image_path=image_path if image_path and os.path.exists(image_path) else None,
                delay=max_delay,
                log_callback=lambda msg: self.after(0, lambda: self._append_log(msg.strip())),
                progress_callback=pcb,
                stop_event=self._selenium_stop_event
            )
            
            self.after(0, lambda: self.send_btn.configure(state="normal", text="🚀 Kirim Pesan"))
            self.after(0, lambda: self._update_progress_ui({"sending": False}))
            
            if res:
                self._generate_html_report(res)

        if mode == "Mode Aman (Selenium)":
            threading.Thread(target=_send_selenium, daemon=True).start()
        else:
            threading.Thread(target=_send_node, daemon=True).start()

    def _generate_html_report(self, send_results):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_name = f"laporan_pengiriman_selenium_{timestamp}.html"
            html_file = os.path.join(os.getcwd(), file_name)
            
            success_count = sum(1 for r in send_results if r["status"] == "Berhasil")
            fail_count = sum(1 for r in send_results if r["status"] == "Gagal")
            
            rows = ""
            for r in send_results:
                is_gagal = r["status"] == "Gagal"
                bg = "#fff0f0" if is_gagal else "#ffffff"
                color = "#c62828" if is_gagal else "#333"
                icon = "❌" if is_gagal else "✅"
                rows += f'<tr style="background-color: {bg}; color: {color};"><td style="padding: 12px; border-bottom: 1px solid #ddd;">{r["number"]}</td><td style="padding: 12px; border-bottom: 1px solid #ddd; font-weight: bold;">{icon} {r["status"]}</td><td style="padding: 12px; border-bottom: 1px solid #ddd;">{r["detail"]}</td></tr>'
                
            html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Laporan Pengiriman (Selenium)</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 40px; color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        h2 {{ color: #128C7E; margin-top: 0; margin-bottom: 20px; }}
        .summary {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .card {{ padding: 15px 20px; border-radius: 8px; font-weight: bold; font-size: 16px; min-width: 120px; }}
        .card.success {{ background-color: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9;}}
        .card.fail {{ background-color: #ffebee; color: #c62828; border: 1px solid #ffcdd2;}}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }}
        th {{ background-color: #f8f9fa; text-align: left; padding: 12px; border-bottom: 2px solid #ddd; color: #555;}}
    </style>
</head>
<body>
    <div class="container">
        <h2>📊 Laporan Hasil Pengiriman (Mode Selenium)</h2>
        <div class="summary">
            <div class="card success">✅ Berhasil: {success_count}</div>
            <div class="card fail">❌ Gagal: {fail_count}</div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Nomor Tujuan</th>
                    <th>Status</th>
                    <th>Detail / Keterangan</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
</body>
</html>"""
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            self.after(0, lambda: self._append_log(f"📄 Laporan disimpan (HTML) di: {file_name}"))
            
            import subprocess
            if sys.platform == 'darwin':
                subprocess.Popen(['open', html_file])
            elif sys.platform == 'win32':
                os.startfile(html_file)
        except Exception as e:
            self.after(0, lambda: self._append_log(f"⚠️ Gagal menyimpan HTML: {e}"))

    # ─── File pickers ─────────────────────────────────────────────────────────

    def _browse_contacts(self):
        p = filedialog.askopenfilename(filetypes=[("Text / XML", "*.txt *.xml")])
        if p:
            self.contacts_entry.delete(0, END)
            self.contacts_entry.insert(0, p)

    def _browse_image(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if p:
            self.image_entry.delete(0, END)
            self.image_entry.insert(0, p)

    # ─── Cleanup ──────────────────────────────────────────────────────────────

    def _on_close(self):
        global _server_proc
        if _server_proc:
            try:
                _server_proc.terminate()
            except Exception:
                pass
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = WhatsAppApp()
    app.mainloop()
