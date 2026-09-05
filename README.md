# 🎛️ Art-Net → Roblox DMX Bridge

**Kontrol lampu/DMX di dalam game Roblox secara real-time**, langsung dari software DMX seperti **MA3**, **QLC+**, atau **MagicQ**. ✨

Sinyal dari console/software DMX-mu akan diteruskan ke game Roblox, sehingga lampu di dunia nyata bisa ditiru langsung di dalam game.

---

## 📚 Daftar Isi

1. [⚠️ Peringatan Penting](#️-peringatan-penting)
2. [🧩 Cara Kerja](#-cara-kerja)
3. [📁 Isi Folder](#-isi-folder)
4. [🎮 Game yang Didukung](#-game-yang-didukung)
5. [🖥️ Yang Dibutuhkan](#️-yang-dibutuhkan)
6. [⚙️ Instalasi](#️-instalasi)
7. [🚀 Cara Menjalankan](#-cara-menjalankan)
8. [❓ Masalah Umum](#-masalah-umum)
9. [📄 Lisensi](#-lisensi)

---

## ⚠️ Peringatan Penting

Script `Roblox_Script.lua` dijalankan pakai **tool pihak ketiga** (bukan cara resmi dari Roblox). Sebelum coba, pahami ini:

- 🚫 Akunmu **bisa kena banned/suspend** sewaktu-waktu.
- 🔒 Tool pihak ketiga (apalagi yang gratis) **bisa mengandung malware**. Unduh hanya dari sumber yang kamu percaya.
- 🔴 **Gunakan akun cadangan**, jangan akun utama.

Proyek ini dibagikan apa adanya untuk keperluan pribadi/eksperimen. Segala risiko (banned, hilang data, dll.) sepenuhnya tanggung jawab pengguna sendiri.

---

## 🧩 Cara Kerja

```
Software DMX (MA3 / QLC+ / MagicQ)
        ▼  kirim sinyal Art-Net
artnet2WSS.py  (aplikasi Python)
        ▼  ubah jadi data & kirim
server.py  (server lokal)
        ▼  simpan & sediakan data
Roblox_Script.lua  (jalan di dalam game)
        ▼
Lampu/objek di Roblox menyala & bergerak real-time ✨
```

---

## 📁 Isi Folder

| File | Fungsi |
|------|--------|
| `artnet2WSS.py` | Aplikasi dengan tampilan (GUI) untuk menerima sinyal Art-Net di PC-mu |
| `server.py` | Server yang meneruskan data ke Roblox |
| `Roblox_Script.lua` | Script yang dijalankan di dalam game Roblox |
| `requirements.txt` | Daftar library Python yang dibutuhkan |
| `1_INSTALL_DEPENDENSI.bat` | Klik untuk install semua library otomatis (Windows) |
| `2_JALANKAN_SERVER.bat` | Klik untuk menjalankan server (Windows) |
| `3_JALANKAN_ARTNET2WSS.bat` | Klik untuk membuka aplikasi Art-Net (Windows) |
| `START_SEMUA.bat` | Klik sekali untuk install + jalankan semuanya (Windows, paling praktis) |

---

## 🎮 Game yang Didukung

| Game | Studio |
|------|--------|
| [Clarity Over Resonance](https://www.roblox.com/games/18218605381/Clarity-Over-Resonance) | Beyond Clarity Studio |

---

## 🖥️ Yang Dibutuhkan

- Windows, macOS, atau Linux
- Python 3.11+ → [Download di sini](https://www.python.org/downloads/)
- Roblox terinstal
- Tool/script runner pihak ketiga (lihat peringatan di atas)
- Software DMX (MA3, QLC+, MagicQ, dll)

---

## ⚙️ Instalasi

1. Install Python dari [python.org](https://www.python.org/downloads/) — saat instalasi, centang **"Add Python to PATH"**.
2. Install library yang dibutuhkan. Cara termudah: **double-click `1_INSTALL_DEPENDENSI.bat`**.
   - Atau lewat Command Prompt: `pip install -r requirements.txt`

---

## 🚀 Cara Menjalankan

**Cara tercepat (Windows):**
1. Double-click `START_SEMUA.bat`
2. Isi Username di jendela yang terbuka
3. Buka Roblox, jalankan `Roblox_Script.lua` lewat tool-mu

**Catatan:** Satu server hanya untuk satu server Roblox. Jangan pakai server yang sama untuk 2 server Roblox berbeda.

**Cara manual:**
1. Jalankan `python server.py` — biarkan tetap terbuka
2. Jalankan `python artnet2WSS.py`, isi Username, pastikan indikator **WebSocket** dan **Art-Net** menyala hijau
3. Buka Roblox, jalankan `Roblox_Script.lua` lewat tool-mu
4. Arahkan output Art-Net dari software DMX-mu ke IP `127.0.0.1`, port `6454`

Untuk menghentikan script di Roblox, jalankan:
```lua
_G.ResetSpesificScripts = true
```

---

## ❓ Masalah Umum

**Server error / modul tidak ditemukan** → Jalankan `pip install -r requirements.txt`.

**Indikator WebSocket tidak hijau** → Pastikan `server.py` sudah jalan duluan, cek firewall.

**Art-Net tidak terdeteksi** → Cek IP/port (`6454`) dan Net/Subnet/Universe di software DMX-mu.

**Lampu di Roblox tidak bergerak** → Cek username sama persis, pastikan sedang di game yang didukung.

**Script langsung error** → Tool-mu mungkin tidak mendukung `http_request`.

---

## 📄 Lisensi

Proyek ini dibuat untuk keperluan pribadi/eksperimen. Penggunaan sepenuhnya tanggung jawab pengguna. Baca [⚠️ Peringatan Penting](#️-peringatan-penting) sebelum menggunakan.