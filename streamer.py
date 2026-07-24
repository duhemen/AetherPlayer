# streamer.py
import subprocess
import os
import sys
import shutil

def inisialisasi_stream_rtmp(url_rtmp, stream_key, width=640, height=480, fps=30):
    """
    Fungsi untuk membuka jalur pipa (pipeline) FFmpeg menuju server
    """
    if not stream_key or stream_key.strip() == "":
        print("[ERROR] Stream Key tidak boleh kosong!")
        return None
    
    if not url_rtmp or url_rtmp.strip() == "":
        print("[ERROR] URL RTMP tidak boleh kosong!")
        return None
    
    tujuan_live = f"{url_rtmp}/{stream_key}"
    
    # Cek FFmpeg
    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        print("[ERROR] FFmpeg tidak ditemukan!")
        print("[INFO] Download FFmpeg: https://ffmpeg.org/download.html")
        print("[INFO] Pastikan ffmpeg.exe ada di PATH atau folder yang sama")
        return None
    
    perintah_ffmpeg = [
        ffmpeg_path,
        '-y',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', f"{width}x{height}",
        '-r', str(fps),
        '-i', '-',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-f', 'flv',
        tujuan_live
    ]
    
    print(f"[STREAMER] 🟢 Membuka pipa RTMP: {url_rtmp}")
    print(f"[STREAMER] 🔑 Stream Key: {stream_key}")
    
    try:
        # Gunakan CREATE_NO_WINDOW untuk menyembunyikan console FFmpeg
        process = subprocess.Popen(
            perintah_ffmpeg,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return process
    except Exception as e:
        print(f"[ERROR] Gagal memulai FFmpeg: {e}")
        return None