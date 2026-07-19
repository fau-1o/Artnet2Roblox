# 🎛️ DMX Art-Net → Roblox Bridge

Proyek ini memungkinkan kamu mengontrol lighting/DMX di dalam game Roblox secara real-time menggunakan sinyal Art-Net dari software DMX seperti MA3, QLC+, atau sejenisnya.

---

## ⚠️ PERINGATAN PENTING — BACA SEBELUM MULAI

### Risiko Penggunaan Executor Roblox

Script Roblox (`Roblox_Script.lua`) dijalankan menggunakan **executor** (seperti Synapse X, KRNL, Delta, dll). Penggunaan executor memiliki risiko nyata:

- 🚫 **Melanggar Syarat & Ketentuan Roblox (ToS)** — akunmu bisa **dibanned permanen** tanpa peringatan.
- 🔒 **Risiko keamanan** — executor pihak ketiga bisa berisi malware atau mencuri data akunmu.
- 👁️ **Tidak ada jaminan keamanan** — Roblox secara aktif mendeteksi dan memblokir executor.

> **🔴 SANGAT DIREKOMENDASIKAN: Gunakan akun Roblox alternatif (bukan akun utama) saat menggunakan executor ini. Jangan pernah memasukkan password akun utamamu di PC yang sama dengan executor.**

---

## 📁 Deskripsi File

| File | Fungsi |
|------|--------|
| `artnet2WSS.py` | Aplikasi GUI — menerima sinyal Art-Net UDP lalu mengirimnya ke server via WebSocket |
| `server.py` | Server lokal — menerima data dari `artnet2WSS.py` dan menyimpannya untuk di-polling |
| `Roblox_Script.lua` | Script executor di Roblox — mengambil data dari server dan mengirimnya ke kendaraan |

---

## 🎮 Game yang Didukung

| Game | Developer | Status |
|------|-----------|--------|
| [Clarity Over Resonance](https://www.roblox.com/search/universal?q=Clarity+Over+Resonance) | Beyond Clarity Studio | ✅ Didukung |

> Ingin menambahkan game lain? Pastikan game tersebut memiliki sistem kendaraan dengan `RemoteEvent` bernama `Data` di dalam folder `Vehicles` pada workspace-nya.

---

## 🧩 Cara Kerja Sistem

```
[Software DMX]
    ↓ Art-Net UDP (port 6454)
[artnet2WSS.py]
    ↓ WebSocket (ws://127.0.0.1:5311)
[server.py]
    ↓ HTTP GET /polling
[Roblox_Script.lua]  ←  dijalankan via executor di dalam Roblox
    ↓ FireServer (RemoteEvent)
[Kendaraan di Roblox]
```

---

## 🖥️ Persyaratan Sistem

- **OS:** Windows 10/11 (direkomendasikan), macOS, atau Linux
- **Python:** versi 3.11 atau lebih baru → [Download Python](https://www.python.org/downloads/)
- **Roblox:** terinstal dan bisa dibuka
- **Executor:** Executor Roblox yang mendukung `http_request` (contoh: Synapse X, KRNL, Fluxus, Delta)
- **Software DMX:** MA3 on PC, QLC+, MagicQ, atau software Art-Net lainnya

---

## ⚙️ Instalasi

### 1. Install Python

Unduh dan install Python dari [python.org](https://www.python.org/downloads/).

> Saat instalasi, **centang "Add Python to PATH"** agar bisa dijalankan dari Command Prompt.

### 2. Install Dependensi Python

Buka **Command Prompt** (tekan `Win + R`, ketik `cmd`, Enter), lalu jalankan:

```bash
pip install -r requirements.txt
```

---

## 🚀 Cara Menjalankan (1 Server per Server Roblox)

> **Penting:** Satu `server.py` hanya untuk **satu server Roblox**. Jangan menjalankan lebih dari satu `server.py` untuk server Roblox yang sama.

### Langkah 1 — Jalankan `server.py`

Buka Command Prompt di folder proyek, lalu:

```bash
python server.py
```

Jika berhasil, kamu akan melihat:

```
==================================================
Art-Net Bridge Server — READY
  WebSocket      : ws://0.0.0.0:5311/
  HTTP polling   : http://0.0.0.0:5311/polling
==================================================
```

Biarkan jendela ini **tetap terbuka** selama bermain.

---

### Langkah 2 — Jalankan `artnet2WSS.py`

Buka Command Prompt baru (jangan tutup yang pertama), lalu:

```bash
python artnet2WSS.py
```

Aplikasi GUI akan terbuka. Isi:
- **Username** → masukkan username Roblox kamu (harus sama persis, case-sensitive)
- **WebSocket URL** → biarkan `ws://127.0.0.1:5311` (default, untuk koneksi lokal)
- **Network Adapter** → pilih adapter jaringanmu (biasanya biarkan "All Adapters")
- **Net / Subnet / Universe** → sesuaikan dengan pengaturan software DMX-mu

Jika koneksi ke server berhasil, indikator **"WebSocket connected"** akan menyala hijau.

---

### Langkah 3 — Buka Roblox dan Jalankan Script Executor

1. Buka game Roblox yang memiliki fitur DMX/kendaraan
2. Buka executormu
3. Copy-paste isi `Roblox_Script.lua` ke executor
4. Klik **Execute / Inject**

Jika berhasil, di output executor akan muncul:
```
[DMX] Bridge ready.
[DMX] Polling thread started → http://127.0.0.1:5311/polling
```

---

### Langkah 4 — Kirim Sinyal dari Software DMX

Arahkan output Art-Net dari software DMX-mu ke:
- **IP:** `127.0.0.1` (jika di PC yang sama) atau IP lokal PC yang menjalankan `server.py`
- **Port:** `6454` (port Art-Net standar)
- **Universe:** sesuaikan dengan yang diset di `artnet2WSS.py`

Lampu/DMX di Roblox akan bergerak mengikuti sinyal real-time! ✨

---

## 🌐 Mengizinkan Player Lain Bergabung (Beda Internet/Lokasi)

Secara default, `server.py` hanya bisa diakses dari komputer yang sama (localhost). Untuk memungkinkan player lain yang ada di **jaringan/internet berbeda** menghubungkan `artnet2WSS.py` mereka ke servermu, gunakan **Cloudflare Quick Tunnel**.

### Cara Membuat Cloudflare Quick Tunnel

#### Langkah A — Install `cloudflared`

- **Windows:** Unduh dari [https://github.com/cloudflare/cloudflared/releases](https://github.com/cloudflare/cloudflared/releases) → pilih `cloudflared-windows-amd64.exe`, simpan di folder proyek, rename menjadi `cloudflared.exe`
- **macOS:** `brew install cloudflare/cloudflare/cloudflared`
- **Linux:** `sudo apt install cloudflared` atau download dari link di atas

#### Langkah B — Jalankan Quick Tunnel

Pastikan `server.py` sudah berjalan, lalu buka Command Prompt baru dan jalankan:

```bash
cloudflared tunnel --url http://localhost:5311
```

Tunggu beberapa detik, akan muncul output seperti:

```
Your quick Tunnel has been created! Visit it at (it may take some time to start up):
https://xxxx-xxxx-xxxx.trycloudflare.com
```

#### Langkah C — Bagikan URL ke Player Lain

Player lain yang ingin bergabung tinggal:
1. Jalankan `artnet2WSS.py` di PC mereka masing-masing
2. Ubah **WebSocket URL** menjadi:
   ```
   wss://xxxx-xxxx-xxxx.trycloudflare.com
   ```
   (ganti `xxxx-xxxx-xxxx` dengan URL tunnel yang kamu dapatkan — perhatikan `wss://` bukan `ws://`)
3. Masukkan **username Roblox mereka sendiri**
4. Klik Connect / jalankan script Roblox mereka

> **Catatan:** URL Quick Tunnel bersifat sementara — berubah setiap kali `cloudflared` dijalankan ulang. Untuk URL permanen, perlu akun Cloudflare (gratis).

---

## 🔄 Menghentikan Script di Roblox

Untuk menghentikan script Lua tanpa keluar dari game, jalankan di executor:

```lua
_G.ResetSpesificScripts = true
```

Script akan berhenti sendiri saat flag ini dideteksi.

---

## ❓ Troubleshooting

**`server.py` tidak bisa dijalankan / error modul tidak ditemukan**
→ Pastikan sudah menjalankan `pip install -r requirements.txt`

**Indikator WebSocket tidak menyala hijau di `artnet2WSS.py`**
→ Pastikan `server.py` sudah berjalan terlebih dahulu. Cek apakah port 5311 tidak diblokir firewall.

**Art-Net tidak terdeteksi (indikator biru tidak menyala)**
→ Pastikan software DMX mengirim ke IP dan port yang benar (`6454`). Coba pilih adapter jaringan yang spesifik (bukan "All Adapters").

**Lampu di Roblox tidak bergerak**
→ Pastikan username di `artnet2WSS.py` sama persis dengan username Roblox (huruf besar/kecil diperhatikan). Pastikan kendaraanmu sudah masuk ke dalam folder `Vehicles` di workspace.

**Cloudflare tunnel tidak bisa terhubung**
→ Pastikan menggunakan `wss://` (bukan `ws://`) saat menggunakan URL Cloudflare. URL tunnel berubah setiap restart.

**Script executor langsung error / crash**
→ Pastikan executormu mendukung fungsi `http_request`. Tidak semua executor gratis mendukung fitur ini.

---

## 📝 Catatan Tambahan

- Satu `server.py` = satu server Roblox. Jika ada 2 server Roblox berbeda, perlu 2 instance `server.py` di port berbeda (ubah `SERVER_PORT` di `server.py`).
- Data DMX channel yang bernilai `0` tidak dikirim untuk menghemat bandwidth — ini perilaku normal.
- Frame queue di script Roblox dibatasi 30 frame (±0.5 detik buffer) untuk mencegah penumpukan.
- Idle user (tidak mengirim data selama 60 detik) akan dibersihkan otomatis dari memori server.

---

## 📄 Lisensi

Proyek ini untuk keperluan pribadi/eksperimen. Penggunaan sepenuhnya tanggung jawab pengguna.
