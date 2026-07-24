# effects.py
import cv2
import numpy as np

def warp_wajah_dinamis(img, titik_pusat, kekuatan, radius, arah_y=0, arah_x=0):
    """ Rumus sakti distorsi elastis wajah """
    h, w, _ = img.shape
    map_x, map_y = np.meshgrid(np.arange(w), np.arange(h))
    map_x = map_x.astype(np.float32)
    map_y = map_y.astype(np.float32)
    
    px, py = titik_pusat
    distansi = np.sqrt((map_x - px)**2 + (map_y - py)**2)
    
    masker = distansi < radius
    with np.errstate(divide='ignore', invalid='ignore'):
        faktor = (radius - distansi) / radius
        faktor = np.where(masker, faktor, 0)
        
    map_y = np.where(masker, map_y + (arah_y * kekuatan * faktor), map_y)
    map_x = np.where(masker, map_x + (arah_x * kekuatan * faktor), map_x)
    return cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR)

def gambar_pipi_merona(frame, cx_r, cy_r, cx_l, cy_l):
    """ Efek Blush On Bahagia """
    overlay = frame.copy()
    cv2.circle(overlay, (cx_r, cy_r), 25, (0, 0, 255), -1)
    cv2.circle(overlay, (cx_l, cy_l), 25, (0, 0, 255), -1)
    return cv2.addWeighted(overlay, 0.4, frame, 0.6, 0)