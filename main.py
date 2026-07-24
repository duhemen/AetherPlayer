# main.py - Versi GUI dengan CustomTkinter (Sinkronisasi Presisi)
import cv2
import cvzone
import time
import os
import threading
import subprocess
import sys
import shutil  # ⭐ PERBAIKAN: import shutil
from datetime import datetime
import re

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np

# Import modul kita
import config
import effects
import streamer

# --- SETUP CUSTOMTKINTER ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AetherPlayerApp:
    def __init__(self):
        # --- WINDOW UTAMA ---
        self.root = ctk.CTk()
        self.root.title("🎭 AetherPlayer - Studio Live & Karaoke")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # --- STATE ---
        self.url_medsos = config.DEFAULT_RTMP_URL
        self.stream_key_text = config.DEFAULT_STREAM_KEY
        self.is_streaming = False
        self.pipa_stream = None
        
        # Media state
        self.media_file = None
        self.media_name = "Belum ada media"
        self.is_playing = False
        self.is_video_mode = False
        self.video_capture = None
        self.video_fps = 30
        self.video_total_frames = 0
        self.current_frame = 0
        self.last_frame_time = 0
        self.video_start_time = 0
        self.video_paused_time = 0
        
        # Audio state untuk video
        self.video_audio_loaded = False
        self.audio_position = 0
        
        # --- SINKRONISASI LIRIK ---
        self.lyrics = []
        self.current_lyric_index = 0
        self.lyrics_loaded = False
        
        # Camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Tidak dapat mengakses kamera!")
            sys.exit(1)
        
        self.cam_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.cam_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # AI Face Detection
        from cvzone.FaceMeshModule import FaceMeshDetector
        self.detektor = FaceMeshDetector(maxFaces=1)
        
        # Audio
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # --- LANDMARK INDICES ---
        self.RIGHT_EYE = 159
        self.LEFT_EYE = 386
        self.RIGHT_CHEEK = 50
        self.LEFT_CHEEK = 280
        self.LIP_LEFT = 61
        self.LIP_RIGHT = 291
        self.LIP_TOP = 0
        self.LIP_BOTTOM = 17
        self.NOSE_TIP = 4
        self.RIGHT_BROW_TOP = 70
        self.LEFT_BROW_TOP = 300
        
        self.terakhir_bergerak_time = time.time()
        self.posisi_mulut_lama = 0
        self.tear_y_offset = 0
        
        # --- BUILD UI ---
        self.build_ui()
        
        # --- START CAMERA THREAD ---
        self.running = True
        self.thread = threading.Thread(target=self.update_camera, daemon=True)
        self.thread.start()
        
        # --- START UPDATE LOOP ---
        self.update_ui()
        
    def build_ui(self):
        """Build UI components"""
        # Main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)
        
        # --- LEFT PANEL: Video Display ---
        self.video_frame = ctk.CTkFrame(self.main_frame, width=800, height=600)
        self.video_frame.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=(0, 10))
        self.video_frame.pack_propagate(False)
        
        # Video label
        self.video_label = ctk.CTkLabel(self.video_frame, text="Loading Camera...", 
                                        font=("Segoe UI", 16))
        self.video_label.pack(fill=ctk.BOTH, expand=True)
        
        # --- RIGHT PANEL: Controls ---
        self.control_frame = ctk.CTkFrame(self.main_frame, width=350)
        self.control_frame.pack(side=ctk.RIGHT, fill=ctk.BOTH, padx=(0, 0))
        self.control_frame.pack_propagate(False)
        
        # Status
        self.status_label = ctk.CTkLabel(self.control_frame, text="🔴 STANDBY", 
                                         font=("Segoe UI", 18, "bold"), text_color="red")
        self.status_label.pack(pady=10)
        
        # Media info
        self.media_label = ctk.CTkLabel(self.control_frame, text="🎵 Belum ada media", 
                                        font=("Segoe UI", 12))
        self.media_label.pack(pady=5)
        
        self.mode_label = ctk.CTkLabel(self.control_frame, text="Mode: Standby", 
                                       font=("Segoe UI", 11), text_color="gray")
        self.mode_label.pack(pady=5)
        
        # --- LIRIK DISPLAY ---
        self.lyric_label = ctk.CTkLabel(self.control_frame, text="🎤 Lirik: -", 
                                        font=("Segoe UI", 13, "bold"), text_color="#00bcd4",
                                        wraplength=300)
        self.lyric_label.pack(pady=5)
        
        # Separator
        ctk.CTkFrame(self.control_frame, height=2, fg_color="gray").pack(fill=ctk.X, pady=10)
        
        # --- Tombol Media ---
        btn_frame = ctk.CTkFrame(self.control_frame)
        btn_frame.pack(fill=ctk.X, pady=5)
        
        self.btn_audio = ctk.CTkButton(btn_frame, text="🎵 Pilih Audio", 
                                       command=self.load_audio,
                                       height=40, font=("Segoe UI", 13))
        self.btn_audio.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
        
        self.btn_video = ctk.CTkButton(btn_frame, text="🎬 Pilih Video (Karaoke)", 
                                       command=self.load_video,
                                       height=40, font=("Segoe UI", 13))
        self.btn_video.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
        
        # --- Tombol Kontrol Playback ---
        play_frame = ctk.CTkFrame(self.control_frame)
        play_frame.pack(fill=ctk.X, pady=5)
        
        self.btn_play = ctk.CTkButton(play_frame, text="▶️ Play", 
                                      command=self.toggle_play,
                                      height=45, font=("Segoe UI", 14, "bold"),
                                      fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_play.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
        
        self.btn_stop = ctk.CTkButton(play_frame, text="⏹️ Stop", 
                                      command=self.stop_media,
                                      height=45, font=("Segoe UI", 14, "bold"),
                                      fg_color="#c62828", hover_color="#b71c1c")
        self.btn_stop.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
        
        # Separator
        ctk.CTkFrame(self.control_frame, height=2, fg_color="gray").pack(fill=ctk.X, pady=10)
        
        # --- Tombol Streaming ---
        self.btn_live = ctk.CTkButton(self.control_frame, text="📡 GO LIVE", 
                                      command=self.toggle_live,
                                      height=50, font=("Segoe UI", 16, "bold"),
                                      fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_live.pack(fill=ctk.X, padx=5, pady=5)
        
        # --- Tombol Settings ---
        self.btn_settings = ctk.CTkButton(self.control_frame, text="⚙️ Settings", 
                                          command=self.open_settings,
                                          height=40, font=("Segoe UI", 13),
                                          fg_color="#1a237e", hover_color="#0d47a1")
        self.btn_settings.pack(fill=ctk.X, padx=5, pady=5)
        
        # --- Status Streaming ---
        self.stream_status = ctk.CTkLabel(self.control_frame, text="URL: rtmp://localhost/live", 
                                          font=("Segoe UI", 10), text_color="gray")
        self.stream_status.pack(pady=5)
        
        # --- Ekspresi ---
        self.expression_label = ctk.CTkLabel(self.control_frame, text="🎭 Ekspresi: Normal", 
                                             font=("Segoe UI", 12))
        self.expression_label.pack(pady=5)
        
        # --- Progress Bar ---
        self.progress = ctk.CTkProgressBar(self.control_frame, height=8)
        self.progress.pack(fill=ctk.X, padx=5, pady=10)
        self.progress.set(0)
        
        # --- Shortcut Info ---
        shortcut_text = "⌨️ Shortcut: Space=Play/Pause | S=Stop | L=Live"
        ctk.CTkLabel(self.control_frame, text=shortcut_text, 
                     font=("Segoe UI", 9), text_color="gray").pack(pady=5)
    
    def cari_ffmpeg(self):
        """Mencari ffmpeg di berbagai lokasi"""
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path
        
        lokasi_umum = [
            'C:\\ffmpeg\\bin\\ffmpeg.exe',
            'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
            'C:\\ffmpeg\\ffmpeg.exe',
            os.path.join(os.path.dirname(__file__), 'ffmpeg.exe'),
            os.path.join(os.path.dirname(__file__), 'bin', 'ffmpeg.exe'),
        ]
        
        for lokasi in lokasi_umum:
            if os.path.exists(lokasi):
                return lokasi
        
        return None
    
    def load_lyrics_from_file(self, file_path):
        """Load lirik dari file .lrc atau .txt"""
        self.lyrics = []
        self.lyrics_loaded = False
        
        base_name = os.path.splitext(file_path)[0]
        lrc_files = [f"{base_name}.lrc", f"{base_name}.txt"]
        
        for lrc_file in lrc_files:
            if os.path.exists(lrc_file):
                try:
                    with open(lrc_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                match = re.match(r'\[(\d+):(\d+)(?:\.(\d+))?\]\s*(.+)', line)
                                if match:
                                    minutes = int(match.group(1))
                                    seconds = int(match.group(2))
                                    centiseconds = int(match.group(3) or 0)
                                    timestamp = minutes * 60 + seconds + centiseconds / 100
                                    lyric_text = match.group(4).strip()
                                    if lyric_text:
                                        self.lyrics.append((timestamp, lyric_text))
                    
                    if self.lyrics:
                        self.lyrics_loaded = True
                        print(f"[LYRICS] ✅ Loaded {len(self.lyrics)} lines from {lrc_file}")
                        break
                except Exception as e:
                    print(f"[LYRICS] ⚠️ Error loading {lrc_file}: {e}")
        
        if not self.lyrics_loaded:
            print("[LYRICS] ℹ️ No lyrics file found")
    
    def load_audio(self):
        """Load audio file"""
        file_path = filedialog.askopenfilename(
            title="Pilih file audio",
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.flac *.m4a")]
        )
        if file_path:
            self.load_media(file_path, is_video=False)
    
    def load_video(self):
        """Load video file for karaoke"""
        file_path = filedialog.askopenfilename(
            title="Pilih file video untuk Karaoke",
            filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov *.flv *.webm")]
        )
        if file_path:
            self.load_media(file_path, is_video=True)
    
    def load_media(self, file_path, is_video):
        """Load media file"""
        try:
            # Stop current media
            self.stop_media()
            
            if self.video_capture:
                self.video_capture.release()
                self.video_capture = None
            
            self.media_file = file_path
            self.media_name = os.path.basename(file_path)
            self.is_video_mode = is_video
            self.is_playing = False
            self.video_audio_loaded = False
            self.current_frame = 0
            self.video_start_time = 0
            self.video_paused_time = 0
            
            # Load lirik
            self.load_lyrics_from_file(file_path)
            
            if is_video:
                # --- LOAD VIDEO ---
                self.video_capture = cv2.VideoCapture(file_path)
                if not self.video_capture.isOpened():
                    messagebox.showerror("Error", f"Tidak bisa membuka video:\n{file_path}")
                    return
                
                self.video_fps = self.video_capture.get(cv2.CAP_PROP_FPS)
                if self.video_fps <= 0:
                    self.video_fps = 30
                
                self.video_total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                self.current_frame = 0
                self.last_frame_time = 0
                
                # --- EKSTRAK AUDIO DARI VIDEO ---
                print(f"[VIDEO] Mencoba ekstrak audio dari: {file_path}")
                
                ffmpeg_path = self.cari_ffmpeg()
                
                if ffmpeg_path:
                    audio_temp = os.path.join(os.path.dirname(file_path), "temp_audio.mp3")
                    
                    try:
                        cmd = [
                            ffmpeg_path, '-i', file_path, 
                            '-vn', '-acodec', 'libmp3lame', 
                            '-ab', '128k', '-ar', '44100', 
                            '-y', audio_temp
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        
                        if os.path.exists(audio_temp) and os.path.getsize(audio_temp) > 0:
                            pygame.mixer.music.load(audio_temp)
                            self.video_audio_loaded = True
                            print(f"[VIDEO] ✅ Audio berhasil diekstrak")
                            try:
                                os.remove(audio_temp)
                            except:
                                pass
                        else:
                            print(f"[VIDEO] ⚠️ Gagal ekstrak audio")
                            try:
                                pygame.mixer.music.load(file_path)
                                self.video_audio_loaded = True
                                print(f"[VIDEO] ✅ Audio dimuat langsung dari video")
                            except:
                                print(f"[VIDEO] ❌ Tidak bisa memuat audio dari video")
                                
                    except subprocess.TimeoutExpired:
                        print(f"[VIDEO] ⚠️ Timeout ekstrak audio")
                    except Exception as e:
                        print(f"[VIDEO] ⚠️ Error ekstrak audio: {e}")
                else:
                    print(f"[VIDEO] ⚠️ FFmpeg tidak ditemukan, video tanpa audio")
                
                if not self.video_audio_loaded:
                    try:
                        pygame.mixer.music.load(file_path)
                        self.video_audio_loaded = True
                        print(f"[VIDEO] ✅ Audio dimuat langsung (fallback)")
                    except:
                        pass
                
                self.mode_label.configure(text="🎬 Mode: KARAOKE", text_color="#00bcd4")
                print(f"[VIDEO] ✅ Video dimuat: {self.media_name}")
                print(f"[VIDEO] FPS: {self.video_fps}, Total frames: {self.video_total_frames}")
                print(f"[VIDEO] Audio tersedia: {self.video_audio_loaded}")
                
            else:
                # --- LOAD AUDIO ---
                try:
                    pygame.mixer.music.load(file_path)
                    self.mode_label.configure(text="🎵 Mode: AUDIO", text_color="#4caf50")
                    print(f"[AUDIO] ✅ Audio dimuat: {self.media_name}")
                except Exception as e:
                    messagebox.showerror("Error", f"Gagal memuat audio:\n{str(e)}")
                    return
            
            self.media_label.configure(text=f"🎵 {self.media_name[:40]}...")
            self.btn_play.configure(text="▶️ Play", fg_color="#2e7d32")
            self.progress.set(0)
            self.lyric_label.configure(text="🎤 Lirik: -")
            
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memuat media:\n{str(e)}")
    
    def toggle_play(self):
        """Play/Pause media dengan sinkronisasi presisi"""
        if not self.media_file:
            messagebox.showinfo("Info", "Silakan pilih media terlebih dahulu!")
            return
        
        if self.is_playing:
            # --- PAUSE ---
            self.is_playing = False
            self.btn_play.configure(text="▶️ Play", fg_color="#2e7d32")
            
            try:
                self.audio_position = pygame.mixer.music.get_pos()
            except:
                self.audio_position = 0
            
            try:
                pygame.mixer.music.pause()
            except:
                pass
            
            self.video_paused_time = time.time() - self.video_start_time
            
            if self.is_video_mode:
                print("[VIDEO] ⏸️ Video dijeda")
            else:
                print("[AUDIO] ⏸️ Audio dijeda")
        else:
            # --- PLAY ---
            self.is_playing = True
            self.btn_play.configure(text="⏸️ Pause", fg_color="#ff8f00")
            
            if self.is_video_mode:
                if self.video_capture and self.current_frame > 0:
                    self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                
                if self.video_audio_loaded:
                    try:
                        if self.audio_position > 0:
                            pygame.mixer.music.play(start=self.audio_position / 1000)
                        else:
                            pygame.mixer.music.play()
                    except:
                        pygame.mixer.music.play()
                else:
                    print("[VIDEO] ⚠️ Tanpa audio (tidak tersedia)")
                
                self.video_start_time = time.time() - self.video_paused_time
                self.last_frame_time = time.time()
                print(f"[VIDEO] ▶️ Video diputar dari frame {self.current_frame}")
                
            else:
                try:
                    if self.audio_position > 0:
                        pygame.mixer.music.play(start=self.audio_position / 1000)
                    else:
                        if pygame.mixer.music.get_pos() == -1:
                            pygame.mixer.music.play(-1)
                        else:
                            pygame.mixer.music.unpause()
                    print("[AUDIO] ▶️ Audio diputar")
                except Exception as e:
                    print(f"[AUDIO] Error play: {e}")
                    try:
                        pygame.mixer.music.play(-1)
                    except:
                        pass
    
    def stop_media(self):
        """Stop media"""
        if not self.media_file:
            return
        
        self.is_playing = False
        self.btn_play.configure(text="▶️ Play", fg_color="#2e7d32")
        self.current_frame = 0
        self.audio_position = 0
        self.video_start_time = 0
        self.video_paused_time = 0
        self.current_lyric_index = 0
        self.lyric_label.configure(text="🎤 Lirik: -")
        
        if self.is_video_mode and self.video_capture:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        try:
            pygame.mixer.music.stop()
        except:
            pass
        
        self.progress.set(0)
        print("[MEDIA] ⏹️ Media dihentikan")
    
    def toggle_live(self):
        """Toggle live streaming"""
        if self.is_streaming:
            if self.pipa_stream:
                try:
                    self.pipa_stream.stdin.close()
                    self.pipa_stream.wait(timeout=3)
                except:
                    self.pipa_stream.kill()
                self.pipa_stream = None
            
            self.is_streaming = False
            self.status_label.configure(text="🔴 STANDBY", text_color="red")
            self.btn_live.configure(text="📡 GO LIVE", fg_color="#2e7d32")
            print("[LIVE] 🔴 Streaming dihentikan")
        else:
            if not self.stream_key_text:
                messagebox.showerror("Error", "Stream Key belum diatur!\nKlik Settings ⚙️")
                return
            
            self.pipa_stream = streamer.inisialisasi_stream_rtmp(
                self.url_medsos, self.stream_key_text, 640, 480, config.FPS
            )
            
            if self.pipa_stream:
                self.is_streaming = True
                self.status_label.configure(text="🟢 ON AIR", text_color="lime")
                self.btn_live.configure(text="🔴 STOP LIVE", fg_color="#c62828")
                print("[LIVE] 🟢 Streaming dimulai")
            else:
                messagebox.showerror("Error", "Gagal memulai streaming!\nPastikan FFmpeg terinstal.")
    
    def open_settings(self):
        """Open settings dialog - PERBAIKAN"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("⚙️ Pengaturan Streaming")
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.attributes('-topmost', True)
        dialog.grab_set()
        
        # Center
        dialog.update_idletasks()
        x = (self.root.winfo_width() - 450) // 2 + self.root.winfo_x()
        y = (self.root.winfo_height() - 350) // 2 + self.root.winfo_y()
        dialog.geometry(f"+{x}+{y}")
        
        # Content - PERBAIKAN: tanpa parameter padding
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="🌐 Pengaturan Streaming", 
                    font=("Segoe UI", 18, "bold")).pack(pady=(0, 15))
        
        # URL
        ctk.CTkLabel(main_frame, text="URL Streaming:", font=("Segoe UI", 12)).pack(anchor="w")
        url_entry = ctk.CTkEntry(main_frame, width=350, height=35, font=("Segoe UI", 12))
        url_entry.insert(0, self.url_medsos)
        url_entry.pack(pady=(5, 10))
        
        # Stream Key
        ctk.CTkLabel(main_frame, text="Stream Key:", font=("Segoe UI", 12)).pack(anchor="w")
        key_entry = ctk.CTkEntry(main_frame, width=350, height=35, font=("Segoe UI", 12), show="•")
        key_entry.insert(0, self.stream_key_text)
        key_entry.pack(pady=(5, 10))
        
        # Info
        ctk.CTkLabel(main_frame, text="💡 Stream Key akan disembunyikan", 
                    font=("Segoe UI", 10), text_color="gray").pack()
        
        # Buttons
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill=ctk.X, pady=15)
        
        def save_settings():
            url = url_entry.get().strip()
            key = key_entry.get().strip()
            if url and key:
                self.url_medsos = url
                self.stream_key_text = key
                self.stream_status.configure(text=f"URL: {url}")
                dialog.destroy()
                messagebox.showinfo("Sukses", "✅ Pengaturan berhasil disimpan!")
            else:
                messagebox.showerror("Error", "URL dan Key tidak boleh kosong!")
        
        ctk.CTkButton(btn_frame, text="💾 Simpan", command=save_settings, 
                     height=40, font=("Segoe UI", 13, "bold")).pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
        
        ctk.CTkButton(btn_frame, text="❌ Batal", command=dialog.destroy, 
                     height=40, font=("Segoe UI", 13), fg_color="gray").pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
    
    def update_lyrics(self, current_time):
        """Update lirik berdasarkan waktu"""
        if not self.lyrics_loaded or not self.lyrics:
            return
        
        for i, (timestamp, text) in enumerate(self.lyrics):
            if timestamp <= current_time:
                if i != self.current_lyric_index:
                    self.current_lyric_index = i
                    self.lyric_label.configure(text=f"🎤 {text}")
                    print(f"[LYRICS] {text}")
            else:
                break
    
    def process_frame(self, frame):
        """Process frame with face detection and AR effects"""
        frame = cv2.flip(frame, 1)
        frame, faces = self.detektor.findFaceMesh(frame, draw=False)
        
        expression_text = "🎭 Ekspresi: Normal"
        
        if faces:
            face = faces[0]
            
            l_lip = face[self.LIP_LEFT]
            r_lip = face[self.LIP_RIGHT]
            t_lip = face[self.LIP_TOP]
            b_lip = face[self.LIP_BOTTOM]
            nose = face[self.NOSE_TIP]
            r_brow = face[self.RIGHT_BROW_TOP]
            l_brow = face[self.LEFT_BROW_TOP]
            
            lip_width = abs(l_lip[0] - r_lip[0])
            lip_height = abs(t_lip[1] - b_lip[1])
            smile_ratio = lip_width / (lip_height + 0.0001)
            alis_diff = abs(r_brow[1] - l_brow[1])
            
            if abs(lip_width - self.posisi_mulut_lama) > 1.5 or alis_diff > 4:
                self.terakhir_bergerak_time = time.time()
            self.posisi_mulut_lama = lip_width
            
            if self.is_playing:
                if alis_diff > 7.0 and smile_ratio < 3.0:
                    expression_text = "🎭 Mode: SINIS 🤨"
                    frame = effects.warp_wajah_dinamis(frame, (nose[0], nose[1]), 15, 40, arah_y=-1)
                elif nose[1] < self.cam_h * 0.45 and smile_ratio < 2.5:
                    expression_text = "🎭 Mode: SULTAN 👑"
                    frame = effects.warp_wajah_dinamis(frame, (nose[0], nose[1]), 30, 60, arah_y=-1)
                elif smile_ratio > 3.2:
                    expression_text = "🎭 Mode: BAHAGIA 😍"
                    frame = effects.gambar_pipi_merona(frame, 
                                                      face[self.RIGHT_CHEEK][0], face[self.RIGHT_CHEEK][1],
                                                      face[self.LEFT_CHEEK][0], face[self.LEFT_CHEEK][1])
                elif smile_ratio < 2.2:
                    expression_text = "🎭 Mode: GALAU 😭"
                    frame = effects.warp_wajah_dinamis(frame, (nose[0], nose[1] + 30), 25, 120, arah_y=1)
                    self.tear_y_offset = (self.tear_y_offset + 5) if self.tear_y_offset < 60 else 0
                    cv2.circle(frame, (face[self.RIGHT_EYE][0], face[self.RIGHT_EYE][1] + 15 + self.tear_y_offset), 
                              6, (255, 100, 0), -1)
                    cv2.circle(frame, (face[self.LEFT_EYE][0], face[self.LEFT_EYE][1] + 15 + self.tear_y_offset), 
                              6, (255, 100, 0), -1)
                elif time.time() - self.terakhir_bergerak_time > 3.0:
                    expression_text = "🎭 Mode: BLANK 🧠"
                    frame = effects.warp_wajah_dinamis(frame, (nose[0], nose[1] + 60), 45, 150, arah_y=1)
        
        self.expression_label.configure(text=expression_text)
        return frame
    
    def update_camera(self):
        """Camera update thread dengan sinkronisasi presisi"""
        frame_counter = 0
        last_fps_update = time.time()
        
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                
                frame = self.process_frame(frame)
                
                # --- VIDEO OVERLAY (KARAOKE) dengan SINKRONISASI PRESISI ---
                if self.is_video_mode and self.is_playing and self.video_capture:
                    current_time = time.time()
                    elapsed_time = current_time - self.video_start_time
                    target_frame = int(elapsed_time * self.video_fps)
                    
                    if target_frame < self.video_total_frames:
                        if target_frame != self.current_frame:
                            self.current_frame = target_frame
                            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                            
                            ret, video_frame = self.video_capture.read()
                            if ret:
                                video_frame = cv2.resize(video_frame, (frame.shape[1], frame.shape[0]))
                                frame = cv2.addWeighted(frame, 0.4, video_frame, 0.6, 0)
                    else:
                        if self.video_total_frames > 0:
                            self.current_frame = 0
                            self.video_start_time = time.time()
                            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            
                            ret, video_frame = self.video_capture.read()
                            if ret:
                                video_frame = cv2.resize(video_frame, (frame.shape[1], frame.shape[0]))
                                frame = cv2.addWeighted(frame, 0.4, video_frame, 0.6, 0)
                    
                    if self.lyrics_loaded:
                        self.update_lyrics(elapsed_time)
                
                # Convert to PIL for display
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                
                if hasattr(self, 'video_label'):
                    width = self.video_label.winfo_width()
                    height = self.video_label.winfo_height()
                    if width > 10 and height > 10:
                        img = img.resize((width, height), Image.Resampling.LANCZOS)
                
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(width, height) if width > 10 else (1, 1))
                
                if hasattr(self, 'video_label'):
                    self.video_label.configure(image=ctk_img)
                    self.video_label.image = ctk_img
                
                # Streaming
                if self.is_streaming and self.pipa_stream:
                    try:
                        stream_frame = cv2.resize(frame, (640, 480))
                        self.pipa_stream.stdin.write(stream_frame.tobytes())
                    except Exception as e:
                        print(f"[ERROR] Streaming error: {e}")
                        self.is_streaming = False
                        self.pipa_stream = None
                        self.status_label.configure(text="🔴 STANDBY", text_color="red")
                        self.btn_live.configure(text="📡 GO LIVE", fg_color="#2e7d32")
                
                # Update progress
                if self.is_video_mode and self.video_capture and self.video_total_frames > 0:
                    progress = self.current_frame / self.video_total_frames
                    self.progress.set(min(progress, 1.0))
                
                frame_counter += 1
                if time.time() - last_fps_update > 1:
                    frame_counter = 0
                    last_fps_update = time.time()
                
                time.sleep(0.005)
                
            except Exception as e:
                print(f"[ERROR] Camera thread: {e}")
                time.sleep(0.1)
    
    def update_ui(self):
        """Main UI update loop"""
        if not self.running:
            return
        self.root.after(50, self.update_ui)
    
    def on_close(self):
        """Cleanup on close"""
        self.running = False
        if self.cap:
            self.cap.release()
        if self.video_capture:
            self.video_capture.release()
        if self.pipa_stream:
            try:
                self.pipa_stream.stdin.close()
                self.pipa_stream.wait(timeout=3)
            except:
                self.pipa_stream.kill()
        pygame.mixer.quit()
        self.root.destroy()
        print("[INFO] ✅ AetherPlayer ditutup dengan aman")

# --- MAIN ---
if __name__ == "__main__":
    print("=" * 60)
    print("🎭 AETHERPLAYER - Studio Live & Karaoke v4.0 (GUI)")
    print("=" * 60)
    print("📌 Catatan:")
    print("  - Untuk video karaoke, pastikan FFmpeg terinstal")
    print("  - Letakkan file lirik (.lrc) dengan nama yang sama untuk lirik")
    print("  - Format lirik: [mm:ss.cc] Teks lirik")
    print("=" * 60)
    
    app = AetherPlayerApp()
    app.root.protocol("WM_DELETE_WINDOW", app.on_close)
    app.root.mainloop()