# settings_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import win32gui
import win32con
import win32api

class SettingsWindow:
    def __init__(self, master, callback_save):
        self.master = master
        self.callback_save = callback_save
        self.window = None
        # ⭐ PERBAIKAN: Inisialisasi StringVar setelah window dibuat
        self.url_var = None
        self.key_var = None
        
    def buka(self, url_medsos, stream_key_text):
        """Buka window pengaturan"""
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            return
            
        # Buat window
        self.window = tk.Toplevel(self.master)
        self.window.title("⚙️ Pengaturan Streaming")
        self.window.geometry("420x320")
        self.window.resizable(False, False)
        self.window.transient(self.master)
        self.window.grab_set()
        self.window.attributes('-topmost', True)
        
        # ⭐ Inisialisasi StringVar setelah window dibuat
        self.url_var = tk.StringVar()
        self.key_var = tk.StringVar()
        self.url_var.set(url_medsos)
        self.key_var.set(stream_key_text)
        
        # Style
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Segoe UI', 11, 'bold'))
        style.configure('Info.TLabel', font=('Segoe UI', 8), foreground='gray')
        
        # --- UI CONTENT ---
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        ttk.Label(main_frame, text="🌐 Pengaturan Streaming", style='Title.TLabel').pack(pady=(0, 15))
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=(0, 15))
        
        # URL Streaming
        ttk.Label(main_frame, text="URL Streaming Server:", font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(5, 3))
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, font=("Segoe UI", 10), width=45)
        url_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Stream Key
        ttk.Label(main_frame, text="Stream Key:", font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(5, 3))
        key_frame = ttk.Frame(main_frame)
        key_frame.pack(fill=tk.X, pady=(0, 5))
        
        key_entry = ttk.Entry(key_frame, textvariable=self.key_var, font=("Segoe UI", 10), width=35, show="•")
        key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Tombol toggle show/hide key
        self.show_key = False
        btn_toggle = ttk.Button(key_frame, text="👁️", width=3, command=self.toggle_key_visibility)
        btn_toggle.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Info
        ttk.Label(main_frame, text="💡 Stream Key akan disembunyikan demi keamanan", style='Info.TLabel').pack(anchor=tk.W, pady=(0, 15))
        
        # Tombol Aksi
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="💾 Simpan", command=self.simpan, width=15).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(btn_frame, text="❌ Tutup", command=self.tutup, width=15).pack(side=tk.RIGHT, padx=5)
        
        # Fokus ke entry pertama
        url_entry.focus()
        url_entry.select_range(0, tk.END)
        
        # Bind Enter key untuk simpan
        self.window.bind('<Return>', lambda e: self.simpan())
        self.window.bind('<Escape>', lambda e: self.tutup())
        
    def toggle_key_visibility(self):
        """Toggle show/hide stream key"""
        self.show_key = not self.show_key
        # Cari entry widget di key_frame
        for child in self.window.winfo_children():
            for subchild in child.winfo_children():
                if isinstance(subchild, ttk.Entry) and subchild.cget('show') in ['•', '']:
                    subchild.config(show='' if self.show_key else '•')
        
    def simpan(self):
        """Simpan pengaturan"""
        url = self.url_var.get().strip()
        key = self.key_var.get().strip()
        
        if not url:
            messagebox.showerror("Error", "URL Streaming tidak boleh kosong!")
            return
        
        if not key:
            messagebox.showerror("Error", "Stream Key tidak boleh kosong!")
            return
            
        self.callback_save(url, key)
        messagebox.showinfo("Sukses", "✅ Pengaturan berhasil disimpan!")
        self.tutup()
        
    def tutup(self):
        """Tutup window"""
        if self.window:
            self.window.destroy()
            self.window = None