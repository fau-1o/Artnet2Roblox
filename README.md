# 🎛️ Art-Net → Roblox DMX Bridge

**Kontrol lighting/DMX di dalam game Roblox secara real-time**, langsung dari software DMX profesional seperti **MA3 (grandMA3)**, **QLC+**, **MagicQ**, atau software Art-Net lainnya. ✨

Sinyal Art-Net dari console/software DMX-mu akan diteruskan lewat bridge ini menuju kendaraan/objek di dalam game Roblox, sehingga lighting di dunia nyata bisa "dicerminkan" langsung ke dalam game.

---

## 📚 Daftar Isi

1. [⚠️ Peringatan Penting](#️-peringatan-penting--baca-sebelum-mulai)
2. [🧩 Cara Kerja Sistem](#-cara-kerja-sistem)
3. [📁 Struktur & Fungsi File](#-struktur--fungsi-file)
4. [🎮 Game yang Didukung](#-game-yang-didukung)
5. [🖥️ Persyaratan Sistem](#️-persyaratan-sistem)
6. [⚙️ Instalasi](#️-instalasi)
7. [🖱️ Cara Pakai File .bat (Windows, Sekali Klik)](#️-cara-pakai-file-bat-windows-sekali-klik)
8. [🚀 Cara Menjalankan](#-cara-menjalankan-1-server-per-server-roblox)
9. [🌐 Multiplayer Lewat Internet (Cloudflare Tunnel)](#-mengizinkan-player-lain-bergabung-beda-internetlokasi)
10. [🔄 Menghentikan Script di Roblox](#-menghentikan-script-di-roblox)
11. [🔌 Referensi Endpoint Server](#-referensi-endpoint-server)
12. [❓ Troubleshooting](#-troubleshooting)
13. [📝 Catatan Tambahan](#-catatan-tambahan)
14. [📄 Lisensi](#-lisensi)

---

## ⚠️ PERINGATAN PENTING — BACA SEBELUM MULAI

### 🎯 Risiko Penggunaan Executor Roblox

Script Roblox (`Roblox_Script.lua`) dijalankan menggunakan **executor** (seperti Synapse X, KRNL, Delta, Xeno, dll). Penggunaan executor memiliki risiko nyata yang perlu kamu pahami:

| Risiko | Penjelasan |
|--------|------------|
| 🚫 **Pelanggaran ToS Roblox** | Executor melanggar Syarat & Ketentuan Roblox — akunmu bisa **dibanned/disuspend permanen** tanpa peringatan. |
| 🔒 **Risiko keamanan** | Executor pihak ketiga (terutama versi gratis/bajakan) bisa berisi malware atau mencuri data akun & informasi pribadimu. |
| 👁️ **Tidak ada jaminan aman** | Roblox secara aktif mengembangkan sistem deteksi anti-cheat/anti-executor. Tidak ada executor yang 100% "aman" selamanya. |

> **🔴 SANGAT DIREKOMENDASIKAN:** Gunakan **akun Roblox alternatif** (bukan akun utama) saat menggunakan executor ini. **Jangan pernah** login akun utamamu di PC yang sama dengan executor.

> **⚠️ DISCLAIMER RESMI**
>
> **Kami TIDAK merekomendasikan penggunaan executor.** Proyek ini dibagikan apa adanya (*as-is*) untuk keperluan eksperimen/pribadi. Dengan menggunakan proyek ini, kamu memahami dan menyetujui bahwa:
>
> - ✅ Segala risiko — termasuk kemungkinan **akun Roblox-mu terkena banned/suspend** — sepenuhnya menjadi **tanggung jawab pengguna sendiri**.
> - ❌ **Kami tidak bertanggung jawab** atas kerugian apa pun (banned, hilang item, hilang data, dll.) dan **tidak bisa membantu memulihkan akun** yang terkena banned akibat penggunaan executor ini.
> - 🛠️ Saat ini sedang dikembangkan **metode alternatif tanpa executor** (misalnya melalui plugin Studio resmi atau API resmi Roblox) agar penggunaannya lebih aman dan sesuai ToS. Namun metode tersebut **masih dalam tahap pengembangan** dan **belum tersedia**. Pantau terus repo ini untuk update-nya. 👀

---

## 🧩 Cara Kerja Sistem

```
🖥️ Software DMX (MA3 / QLC+ / MagicQ)
        │  Art-Net UDP → port 6454
        ▼
🐍 artnet2WSS.py  (aplikasi GUI Python)
        │  parsing paket Art-Net → JSON per channel
        │  WebSocket → ws://127.0.0.1:5311
        ▼
🌐 server.py  (server lokal async)
        │  menyimpan frame DMX per username
        │  HTTP GET /polling (atau broadcast via WebSocket)
        ▼
🎮 Roblox_Script.lua  (dijalankan via executor di dalam game)
        │  polling ~44x/detik → antre di frame queue
        │  drain 1 frame per Heartbeat (~60fps) → smooth, anti-burst
        │  kirim data ke sistem lighting di dalam game
        ▼
🚗 Kendaraan/Objek di Roblox bergerak & menyala real-time ✨
```

**Kenapa ada dua thread di script Roblox (polling + drain)?**
Polling mengambil banyak frame sekaligus dari server (batch), lalu frame-frame itu dimasukkan ke antrian dan dikeluarkan **satu per satu setiap Heartbeat**. Hasilnya gerakan lighting terasa mulus seperti video 60fps, bukan patah-patah/burst.

---

## 📁 Struktur & Fungsi File

| File | Bahasa | Fungsi |
|------|--------|--------|
| 🖼️ `artnet2WSS.py` | Python (GUI/Tkinter) | Menerima sinyal Art-Net UDP di PC-mu, menampilkan status koneksi & nilai channel secara visual, lalu mengirim data ke `server.py` via WebSocket. |
| 🌐 `server.py` | Python (aiohttp, async) | Server lokal yang menampung data DMX dari satu atau banyak client (`artnet2WSS.py`), menyediakan endpoint HTTP/WebSocket untuk diambil oleh script Roblox. |
| 🎮 `Roblox_Script.lua` | Lua (Roblox executor) | Berjalan di dalam game [Clarity Over Resonance](https://www.roblox.com/games/18218605381/Clarity-Over-Resonance) — polling data dari `server.py`, lalu meneruskannya ke sistem lighting/kendaraan di dalam game sesuai username. |
| 📦 `requirements.txt` | — | Daftar dependensi Python yang dibutuhkan (`aiohttp`, `websockets`). |
| 🖱️ `1_INSTALL_DEPENDENSI.bat` | Windows Batch | Sekali klik untuk install semua library Python yang dibutuhkan (pengganti `pip install -r requirements.txt`). |
| 🖱️ `2_JALANKAN_SERVER.bat` | Windows Batch | Sekali klik untuk menjalankan `server.py` tanpa perlu buka Command Prompt manual. |
| 🖱️ `3_JALANKAN_ARTNET2WSS.bat` | Windows Batch | Sekali klik untuk menjalankan `artnet2WSS.py` tanpa perlu buka Command Prompt manual. |
| 🖱️ `START_SEMUA.bat` | Windows Batch | Sekali klik: install dependensi (jika belum) **dan** langsung menjalankan `server.py` + `artnet2WSS.py` bersamaan di dua jendela terpisah — cara tercepat untuk mulai main. |

---

## 🎮 Game yang Didukung

Proyek ini dibuat **khusus** untuk satu game berikut dan tidak dijamin kompatibel dengan game Roblox lain:

| Game | Studio | Status |
|------|--------|--------|
| [Clarity Over Resonance](https://www.roblox.com/games/18218605381/Clarity-Over-Resonance) | Beyond Clarity Studio | ✅ Didukung |

---

## 🖥️ Persyaratan Sistem

- 💻 **OS:** Windows 10/11 (direkomendasikan), macOS, atau Linux
- 🐍 **Python:** versi 3.11 atau lebih baru → [Download Python](https://www.python.org/downloads/)
- 🎮 **Roblox:** terinstal dan bisa dibuka
- 🧩 **Executor:** Executor Roblox yang mendukung fungsi `http_request` / `request` (contoh: Synapse X, KRNL, Fluxus, Delta) — lihat [⚠️ peringatan di atas](#️-peringatan-penting--baca-sebelum-mulai)
- 🎚️ **Software DMX:** MA3 on PC, QLC+, MagicQ, atau software Art-Net lain yang bisa broadcast ke port `6454`

---

## ⚙️ Instalasi

### 1️⃣ Install Python

Unduh dan install Python dari [python.org](https://www.python.org/downloads/).

> ✅ Saat instalasi, **centang "Add Python to PATH"** agar bisa dijalankan dari Command Prompt.

### 2️⃣ Install Dependensi Python

Buka **Command Prompt** (tekan `Win + R`, ketik `cmd`, Enter), arahkan ke folder proyek, lalu jalankan:

```bash
pip install -r requirements.txt
```

Ini akan menginstall:
- `aiohttp` — untuk menjalankan `server.py`
- `websockets` — untuk menjalankan `artnet2WSS.py`

> ℹ️ `tkinter` (untuk GUI `artnet2WSS.py`) biasanya sudah termasuk dalam instalasi Python di Windows/macOS. Pengguna Linux mungkin perlu install manual:
> ```bash
> sudo apt install python3-tk       # Debian/Ubuntu
> sudo dnf install python3-tkinter  # Fedora
> ```

> 💡 **Pengguna Windows:** tidak perlu buka Command Prompt manual. Tinggal **double-click `1_INSTALL_DEPENDENSI.bat`** — sekali klik, semua library otomatis terinstall. Lihat bagian [🖱️ Cara Pakai File .bat (Windows, Sekali Klik)](#️-cara-pakai-file-bat-windows-sekali-klik) di bawah.

---

## 🖱️ Cara Pakai File `.bat` (Windows, Sekali Klik)

Untuk pengguna Windows yang tidak ingin repot mengetik perintah di Command Prompt, project ini sudah menyediakan 4 file `.bat` siap pakai — tinggal **double-click**, tanpa perlu ketik apa pun:

| File | Kapan dipakai |
|------|---------------|
| `1_INSTALL_DEPENDENSI.bat` | Jalankan **sekali saja** di awal (atau setiap ada update library) untuk install semua dependensi Python secara otomatis |
| `2_JALANKAN_SERVER.bat` | Pengganti `python server.py` — double-click untuk menyalakan server |
| `3_JALANKAN_ARTNET2WSS.bat` | Pengganti `python artnet2WSS.py` — double-click untuk membuka GUI Art-Net |
| `START_SEMUA.bat` | **Paling praktis.** Sekali klik: otomatis cek & install dependensi (jika belum), lalu langsung membuka `server.py` dan `artnet2WSS.py` bersamaan di dua jendela terpisah |

**Rekomendasi pemakaian tercepat:**
1. Double-click `START_SEMUA.bat`
2. Tunggu sampai dua jendela Command Prompt terbuka (Server + GUI Art-Net)
3. Isi Username di jendela GUI, lalu lanjut ke [Langkah 3 — Buka Roblox & Jalankan Script Executor](#langkah-3--buka-roblox--jalankan-script-executor-) di bawah

> Semua file `.bat` otomatis mendeteksi apakah Python di sistemmu terdaftar sebagai `python` atau `py`, jadi tetap berfungsi meski cara instalasi Python-nya berbeda-beda. File `.bat` ini **hanya untuk Windows** — pengguna macOS/Linux tetap menjalankan lewat perintah `python3 server.py` dll seperti biasa.

---

## 🚀 Cara Menjalankan (1 Server per Server Roblox)

> 📌 **Penting:** Satu `server.py` hanya untuk **satu server Roblox**. Jangan menjalankan lebih dari satu instance `server.py` di port yang sama untuk server Roblox yang berbeda — karena semua data DMX akan tercampur.

### Langkah 1 — Jalankan `server.py` 🌐

Buka Command Prompt di folder proyek, lalu:

```bash
python server.py
```

Jika berhasil, kamu akan melihat log seperti ini:

```
==================================================
Art-Net Bridge Server — READY
  WebSocket      : ws://0.0.0.0:5311/
  WebSocket alt  : ws://0.0.0.0:5311/ws
  HTTP state     : http://0.0.0.0:5311/state
  HTTP polling   : http://0.0.0.0:5311/polling
  Broadcast rate : ~30 fps (throttled)
  Idle cleanup   : after 60s
==================================================
```

📌 Biarkan jendela ini **tetap terbuka** selama bermain.

> 🖱️ **Windows:** cukup double-click `2_JALANKAN_SERVER.bat` sebagai gantinya.

### Langkah 2 — Jalankan `artnet2WSS.py` 🖼️

Buka Command Prompt **baru** (jangan tutup yang pertama), lalu:

```bash
python artnet2WSS.py
```

Aplikasi GUI akan terbuka dan memintamu memasukkan **username** — ini digunakan untuk mencocokkan data DMX dengan kendaraanmu di Roblox. Selanjutnya atur:

| Kolom | Keterangan |
|-------|------------|
| **WebSocket URL** | Biarkan `ws://127.0.0.1:5311` (default, untuk koneksi lokal) |
| **Network Adapter** | Pilih adapter jaringanmu (biasanya biarkan `0.0.0.0 (All Adapters)`) |
| **Receive Net / Subnet / Universe** | Sesuaikan dengan pengaturan output di software DMX-mu |

Jika koneksi ke server berhasil, indikator **🟢 "WebSocket connected"** akan menyala hijau. Saat paket Art-Net mulai diterima, indikator **🔵 "Art-Net detected"** juga akan menyala.

> 💡 Klik menu **File → Show Output** untuk membuka jendela yang menampilkan nilai real-time seluruh 512 channel DMX.

> 🖱️ **Windows:** cukup double-click `3_JALANKAN_ARTNET2WSS.bat` sebagai gantinya.

### Langkah 3 — Buka Roblox & Jalankan Script Executor 🎮

1. Buka game Roblox yang mendukung fitur DMX/kendaraan (lihat [daftar game](#-game-yang-didukung))
2. Buka executormu
3. Copy-paste seluruh isi `Roblox_Script.lua` ke executor
4. Klik **Execute / Inject**

Jika berhasil, di output/console executor akan muncul:

```
[DMX] Polling thread started → http://127.0.0.1:5311/polling
[DMX] Cached: <username kendaraan>
[DMX] Bridge ready.
```

### Langkah 4 — Kirim Sinyal dari Software DMX 🎚️

Arahkan output Art-Net dari software DMX-mu ke:

| Parameter | Nilai |
|-----------|-------|
| **IP Tujuan** | `127.0.0.1` (jika di PC yang sama) atau IP lokal PC yang menjalankan `server.py` |
| **Port** | `6454` (port Art-Net standar) |
| **Net / Subnet / Universe** | Harus sama persis dengan yang diset di `artnet2WSS.py` |

Lampu/DMX di Roblox akan bergerak mengikuti sinyal real-time! ✨

---

## 🌐 Mengizinkan Player Lain Bergabung (Beda Internet/Lokasi)

Secara default, `server.py` hanya bisa diakses dari komputer yang sama (`localhost`). Untuk mengizinkan player lain yang berada di **jaringan/internet berbeda** menghubungkan `artnet2WSS.py` mereka ke servermu, gunakan **Cloudflare Quick Tunnel**. 🚇

### Langkah A — Install `cloudflared`

- 🪟 **Windows:** Unduh dari [github.com/cloudflare/cloudflared/releases](https://github.com/cloudflare/cloudflared/releases) → pilih `cloudflared-windows-amd64.exe`, simpan di folder proyek, rename menjadi `cloudflared.exe`
- 🍎 **macOS:** `brew install cloudflare/cloudflare/cloudflared`
- 🐧 **Linux:** `sudo apt install cloudflared` atau download dari link di atas

### Langkah B — Jalankan Quick Tunnel

Pastikan `server.py` sudah berjalan, lalu buka Command Prompt baru dan jalankan:

```bash
cloudflared tunnel --url http://localhost:5311
```

Tunggu beberapa detik, akan muncul output seperti:

```
Your quick Tunnel has been created! Visit it at (it may take some time to start up):
https://xxxx-xxxx-xxxx.trycloudflare.com
```

### Langkah C — Bagikan URL ke Player Lain

Player lain yang ingin bergabung tinggal:

1. Jalankan `artnet2WSS.py` di PC mereka masing-masing
2. Ubah **WebSocket URL** menjadi:
   ```
   wss://xxxx-xxxx-xxxx.trycloudflare.com
   ```
   (ganti `xxxx-xxxx-xxxx` dengan URL tunnel yang kamu dapatkan — perhatikan `wss://`, bukan `ws://`)
3. Masukkan **username Roblox mereka sendiri**
4. Jalankan/connect seperti biasa

> 📝 **Catatan:** URL Quick Tunnel bersifat sementara — berubah setiap kali `cloudflared` dijalankan ulang. Untuk URL permanen, perlu akun Cloudflare (gratis).

---

## 🔄 Menghentikan Script di Roblox

Untuk menghentikan script Lua tanpa keluar dari game, jalankan baris berikut di executor:

```lua
_G.ResetSpesificScripts = true
```

Script akan mendeteksi flag ini pada iterasi polling berikutnya, mencetak log `[DMX] Dihentikan via ResetSpesificScripts`, lalu menghentikan dirinya sendiri (`script:Destroy()`).

---

## 🔌 Referensi Endpoint Server

`server.py` menyediakan beberapa endpoint HTTP & WebSocket di port `5311` (default):

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/` atau `/ws` | WebSocket | Kirim data DMX (dari `artnet2WSS.py`) atau subscribe untuk menerima broadcast state real-time |
| `/state` | `GET` | Snapshot terkini — satu frame terakhir per user |
| `/polling` | `GET` | Semua frame terakumulasi (`t1`, `t2`, ... `tN`) per user sejak polling terakhir, lalu buffer dikosongkan — inilah yang dipakai `Roblox_Script.lua` |

---

## ❓ Troubleshooting

**🔴 `server.py` tidak bisa dijalankan / error modul tidak ditemukan**
→ Pastikan sudah menjalankan `pip install -r requirements.txt`.

**🔴 Indikator WebSocket tidak menyala hijau di `artnet2WSS.py`**
→ Pastikan `server.py` sudah berjalan terlebih dahulu. Cek apakah port `5311` tidak diblokir firewall.

**🔴 Art-Net tidak terdeteksi (indikator biru tidak menyala)**
→ Pastikan software DMX mengirim ke IP dan port yang benar (`6454`). Coba pilih adapter jaringan yang spesifik (bukan "All Adapters"). Pastikan **Net/Subnet/Universe** di `artnet2WSS.py` sama persis dengan output software DMX-mu.

**🔴 Lampu di Roblox tidak bergerak**
→ Pastikan username di `artnet2WSS.py` sama persis dengan username Roblox (huruf besar/kecil diperhatikan). Pastikan kamu sedang berada di game [Clarity Over Resonance](https://www.roblox.com/games/18218605381/Clarity-Over-Resonance) dan kendaraanmu sudah muncul/ter-spawn di dalam game.

**🔴 Cloudflare tunnel tidak bisa terhubung**
→ Pastikan menggunakan `wss://` (bukan `ws://`) saat menggunakan URL Cloudflare. Ingat, URL tunnel berubah setiap kali `cloudflared` di-restart.

**🔴 `artnet2WSS.py` error `'ProactorEventLoop' object has no attribute 'sock_recvfrom'`**
→ Ini bug kompatibilitas asyncio di Windows (event loop default `ProactorEventLoop` baru mendukung `sock_recvfrom` mulai Python 3.11). Sudah diperbaiki di `artnet2WSS.py` versi ini dengan memaksa pemakaian `SelectorEventLoop` khusus di Windows. Jika masih muncul, pastikan kamu memakai file `artnet2WSS.py` versi terbaru dari repo ini.

**🔴 Script executor langsung error / crash**
→ Pastikan executormu mendukung fungsi `http_request`/`request`. Tidak semua executor gratis mendukung fitur ini — script akan menampilkan error `"Executor tidak mendukung HTTP request"` jika tidak didukung.

---

## 📝 Catatan Tambahan

- 🔁 Satu `server.py` = satu server Roblox. Jika ada 2 server Roblox berbeda yang berjalan bersamaan, perlu 2 instance `server.py` di port berbeda (ubah `SERVER_PORT` di `server.py`).
- 📉 Data DMX channel bernilai `0` tidak dikirim ke script Roblox untuk menghemat bandwidth — ini perilaku normal, bukan bug.
- 🧵 Frame queue di script Roblox dibatasi maksimal **30 frame** (± 0.5 detik buffer) agar tidak menumpuk saat polling lebih cepat dari drain (mencegah memory leak/lag).
- 🧹 User yang idle (tidak mengirim data selama 60 detik) akan dibersihkan otomatis dari memori server.
- ⚡ Data dikirim ke server dengan rate limit ~44 fps dari `artnet2WSS.py`, lalu dibroadcast ke subscriber WebSocket dengan throttle ~30 fps, dan di-drain ke Roblox 1 frame per Heartbeat (~60fps) agar gerakan tetap smooth.

---

## 📄 Lisensi

Proyek ini dibuat untuk keperluan pribadi/eksperimen. Penggunaan sepenuhnya menjadi tanggung jawab pengguna. Lihat juga bagian [⚠️ Peringatan Penting](#️-peringatan-penting--baca-sebelum-mulai) di atas sebelum menggunakan proyek ini.
