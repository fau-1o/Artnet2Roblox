import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog
import threading
import asyncio
import websockets
import json
import socket
import struct
import time
import platform
import os

# ============================================================
# KONFIGURASI DEFAULT
# ============================================================
ARTNET_PORT = 6454

# Jeda pendek untuk menggabungkan beberapa universe yang datang hampir bersamaan
# jadi satu pesan WebSocket. Pengiriman dipicu langsung oleh paket Art-Net (realtime).
SEND_COALESCE = 0.004

# File kecil di samping script untuk mengingat username terakhir
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artnet2wss_config.json")

# Harus sama dengan MAX_UNIVERSES di Server_multi_universe_polling.py
MAX_UNIVERSES = 8


def calculate_broadcast_address(ip_address: str) -> str:
    if ip_address == "0.0.0.0" or "All Adapters" in ip_address:
        return "255.255.255.255"
    elif ip_address == "127.0.0.1":
        return "127.255.255.255"
    try:
        parts = ip_address.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.255"
    except Exception:
        return "255.255.255.255"


def get_local_ip_addresses() -> list[str]:
    addresses = ["0.0.0.0 (All Adapters)"]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        if local_ip and local_ip != "0.0.0.0":
            addresses.append(local_ip)
    except Exception:
        pass
    if "127.0.0.1" not in addresses:
        addresses.append("127.0.0.1")
    return addresses


class ArtNetGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Art-Net to Roblox DMX - Multi Universe")
        self.root.geometry("500x480")
        self.root.resizable(False, False)

        self.username = ""
        self.is_running = True

        # Buffer DMX per universe (index 0 = server universe 1)
        self.dmx_buffers: list[list[int]] = [[0] * 512 for _ in range(MAX_UNIVERSES)]
        self._dirty: list[bool] = [False] * MAX_UNIVERSES
        self.last_artnet_time: float = 0.0
        self.last_send_time: float = 0.0
        self._send_event: asyncio.Event | None = None

        # State WebSocket
        self.ws_connected = False
        self.websocket = None

        # Adapter tersedia
        self.available_adapters = get_local_ip_addresses()

        # Output window state
        self.output_window: tk.Toplevel | None = None
        self.dmx_labels: list[tk.Label] = []
        self.view_var: tk.StringVar | None = None

        self.setup_ui()
        self.ask_for_key()

        self.root.after(100, self.update_gui_loop)

        # Thread jaringan (asyncio loop terpisah dari tkinter)
        self.loop = asyncio.new_event_loop()
        self.net_thread = threading.Thread(
            target=self._run_network_loop, daemon=True
        )
        self.net_thread.start()

    # ----------------------------------------------------------
    # SETUP UI
    # ----------------------------------------------------------

    def setup_ui(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_command(label="Show Output", command=self.open_output_window)
        self.root.config(menu=menubar)

        # WebSocket URL
        url_frame = tk.Frame(self.root, padx=10, pady=5)
        url_frame.pack(fill=tk.X)
        tk.Label(url_frame, text="WebSocket URL:").pack(side=tk.LEFT)
        self.ws_url_var = tk.StringVar(value="ws://127.0.0.1:5311")
        tk.Entry(url_frame, textvariable=self.ws_url_var, width=35).pack(
            side=tk.LEFT, padx=5
        )

        # Indikator + adapter
        top_frame = tk.Frame(self.root, padx=10, pady=5)
        top_frame.pack(fill=tk.X)

        ind_frame = tk.Frame(top_frame)
        ind_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.canvas_ws = tk.Canvas(ind_frame, width=15, height=15, highlightthickness=0)
        self.ind_ws = self.canvas_ws.create_oval(2, 2, 13, 13, fill="gray")
        self.canvas_ws.grid(row=0, column=0, pady=2)
        tk.Label(ind_frame, text="WebSocket connected").grid(row=0, column=1, sticky=tk.W)

        self.canvas_artnet = tk.Canvas(ind_frame, width=15, height=15, highlightthickness=0)
        self.ind_artnet = self.canvas_artnet.create_oval(2, 2, 13, 13, fill="gray")
        self.canvas_artnet.grid(row=1, column=0, pady=2)
        tk.Label(ind_frame, text="Art-Net detected").grid(row=1, column=1, sticky=tk.W)

        tk.Label(ind_frame, text="Network adapter:").grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0)
        )
        self.adapter_combo = ttk.Combobox(
            ind_frame, values=self.available_adapters, state="readonly", width=20
        )
        self.adapter_combo.current(0)
        self.adapter_combo.grid(row=4, column=0, columnspan=2, sticky=tk.W)

        # Net / Subnet / Start Universe / Jumlah Universe
        set_frame = tk.Frame(top_frame)
        set_frame.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(set_frame, text="Receive Net:").grid(row=0, column=0, sticky=tk.E)
        self.net_var = tk.StringVar(value="0")
        ttk.Combobox(
            set_frame, textvariable=self.net_var,
            values=[str(i) for i in range(128)], width=5
        ).grid(row=0, column=1, pady=2)

        tk.Label(set_frame, text="Receive Subnet:").grid(row=1, column=0, sticky=tk.E)
        self.subnet_var = tk.StringVar(value="0")
        ttk.Combobox(
            set_frame, textvariable=self.subnet_var,
            values=[str(i) for i in range(16)], width=5
        ).grid(row=1, column=1, pady=2)

        tk.Label(set_frame, text="Start Universe:").grid(row=2, column=0, sticky=tk.E)
        self.uni_var = tk.StringVar(value="0")
        ttk.Combobox(
            set_frame, textvariable=self.uni_var,
            values=[str(i) for i in range(16)], width=5
        ).grid(row=2, column=1, pady=2)

        tk.Label(set_frame, text="Jumlah Universe:").grid(row=3, column=0, sticky=tk.E)
        self.count_var = tk.StringVar(value=str(MAX_UNIVERSES))
        ttk.Combobox(
            set_frame, textvariable=self.count_var,
            values=[str(i) for i in range(1, MAX_UNIVERSES + 1)], width=5,
            state="readonly"
        ).grid(row=3, column=1, pady=2)

        tk.Label(
            set_frame,
            text=f"Art-Net universe Start..Start+N-1\n→ server universe 1..N (maks {MAX_UNIVERSES})",
            justify=tk.LEFT, fg="gray", font=("TkDefaultFont", 8),
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        self.log_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=10)
        self.log_area.pack(padx=10, pady=(0, 10), fill=tk.BOTH, expand=True)

    def ask_for_key(self):
        saved = ""
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = str(json.load(f).get("username", ""))
        except Exception:
            pass
        key = simpledialog.askstring(
            "Username", "Masukkan username Roblox Anda:",
            parent=self.root, initialvalue=saved,
        )
        self.username = key.strip() if key and key.strip() else (saved or "Guest_User")
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"username": self.username}, f)
        except Exception:
            pass
        self.log(f"✓ Username: {self.username}")

    # ----------------------------------------------------------
    # LOGGING (thread-safe)
    # ----------------------------------------------------------

    def log(self, message: str):
        """Thread-safe log ke text area."""
        self.root.after(0, self._append_log, message)

    def _append_log(self, message: str):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    # ----------------------------------------------------------
    # OUTPUT WINDOW
    # ----------------------------------------------------------

    def open_output_window(self):
        if self.output_window is not None and tk.Toplevel.winfo_exists(self.output_window):
            self.output_window.lift()
            return

        self.output_window = tk.Toplevel(self.root)
        self.output_window.title("DMX Output")
        self.output_window.geometry("500x430")

        # Pemilih universe yang ditampilkan
        top_bar = tk.Frame(self.output_window, padx=6, pady=4)
        top_bar.pack(side="top", fill="x")
        tk.Label(top_bar, text="Universe (server):").pack(side=tk.LEFT)
        self.view_var = tk.StringVar(value="1")
        ttk.Combobox(
            top_bar, textvariable=self.view_var,
            values=[str(i) for i in range(1, MAX_UNIVERSES + 1)],
            width=4, state="readonly"
        ).pack(side=tk.LEFT, padx=5)

        canvas = tk.Canvas(self.output_window, bg="white")
        scrollbar = ttk.Scrollbar(self.output_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")
        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.dmx_labels = []
        for i in range(512):
            row = i // 8
            col = i % 8
            if col == 0:
                tk.Label(
                    scrollable_frame, text=f"{i + 1:03d}", width=4, bg="lightgray"
                ).grid(row=row, column=0, padx=1, pady=1)
            lbl = tk.Label(
                scrollable_frame, text="000", width=4, bg="white",
                borderwidth=1, relief="solid"
            )
            lbl.grid(row=row, column=col + 1, padx=1, pady=1)
            self.dmx_labels.append(lbl)

    # ----------------------------------------------------------
    # GUI UPDATE LOOP (berjalan di main thread)
    # ----------------------------------------------------------

    def update_gui_loop(self):
        now = time.time()

        # Update indikator
        self.canvas_ws.itemconfig(
            self.ind_ws, fill="green" if self.ws_connected else "gray"
        )
        self.canvas_artnet.itemconfig(
            self.ind_artnet,
            fill="green" if now - self.last_artnet_time < 1.0 else "gray",
        )

        # Update output window hanya jika terbuka
        if (
            self.output_window is not None
            and tk.Toplevel.winfo_exists(self.output_window)
            and self.view_var is not None
        ):
            try:
                idx = int(self.view_var.get()) - 1
            except ValueError:
                idx = 0
            idx = max(0, min(MAX_UNIVERSES - 1, idx))
            for i, val in enumerate(self.dmx_buffers[idx]):
                text = f"{val:03d}"
                if self.dmx_labels[i].cget("text") != text:
                    self.dmx_labels[i].config(text=text)

        if self.is_running:
            self.root.after(100, self.update_gui_loop)

    # ----------------------------------------------------------
    # CLOSE
    # ----------------------------------------------------------

    def on_closing(self):
        self.is_running = False
        try:
            self.output_window.destroy()
        except Exception:
            pass
        try:
            # Hentikan asyncio loop
            self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    # ----------------------------------------------------------
    # NETWORK LOOP (asyncio di thread terpisah)
    # ----------------------------------------------------------

    def _run_network_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._network_tasks())

    async def _network_tasks(self):
        self._send_event = asyncio.Event()
        await asyncio.gather(
            self._artnet_receiver(),
            self._websocket_manager(),
            self._sender_loop(),
        )

    # ----------------------------------------------------------
    # WEBSOCKET MANAGER
    # ----------------------------------------------------------

    async def _websocket_manager(self):
        """
        Kelola koneksi ke server. Auto-reconnect jika putus.
        Punya timeout kirim untuk menghindari hang.
        """
        current_url = ""

        while self.is_running:
            target_url = self.ws_url_var.get().strip()

            # URL baru — log sekali
            if target_url != current_url:
                self.log(f"Mencoba connect ke: {target_url}")
                current_url = target_url

            try:
                async with websockets.connect(
                    target_url,
                    compression=None,     # tanpa kompresi: latensi minimum
                    open_timeout=5,       # Batas waktu handshake
                    close_timeout=3,      # Batas waktu close
                    ping_interval=20,     # Keepalive otomatis
                    ping_timeout=10,      # Putus jika ping tidak dijawab 10s
                ) as websocket:
                    self.websocket = websocket
                    self.ws_connected = True
                    self.log(f"✓ Terhubung ke {target_url}")

                    # Tunggu sampai URL berubah atau koneksi mati atau app ditutup
                    while (
                        self.is_running
                        and self.ws_connected
                        and self.ws_url_var.get().strip() == current_url
                    ):
                        await asyncio.sleep(0.05)

            except Exception:
                # Koneksi gagal / putus — tidak perlu log spam
                pass
            finally:
                self.ws_connected = False
                self.websocket = None

            if self.is_running:
                await asyncio.sleep(2)  # Jeda sebelum retry

    # ----------------------------------------------------------
    # ART-NET RECEIVER
    # ----------------------------------------------------------

    async def _artnet_receiver(self):
        """
        Terima paket Art-Net UDP untuk beberapa universe sekaligus.
        Setiap paket disimpan ke buffer universe-nya dan ditandai dirty;
        pengiriman ke WebSocket dilakukan oleh _sender_loop.
        """
        while self.is_running:
            sock = None
            try:
                selected = self.adapter_combo.get()
                bind_addr = (
                    "0.0.0.0"
                    if "All Adapters" in selected
                    else selected.split()[0]
                )

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if platform.system() == "Windows":
                    try:
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 0)
                    except Exception:
                        pass
                sock.bind((bind_addr, ARTNET_PORT))
                sock.setblocking(False)

                loop = asyncio.get_running_loop()
                self.log(f"Art-Net listening on {bind_addr}:{ARTNET_PORT}")

                while self.is_running:
                    # Re-read pengaturan setiap iterasi (bisa berubah di UI)
                    base_address, count = self._get_address_range()

                    try:
                        data, _addr = await asyncio.wait_for(
                            loop.sock_recvfrom(sock, 1024), timeout=0.5
                        )
                    except asyncio.TimeoutError:
                        continue

                    if not (data.startswith(b"Art-Net\x00") and len(data) >= 18):
                        continue

                    opcode = struct.unpack("<H", data[8:10])[0]
                    if opcode != 0x5000:
                        continue

                    packet_address = struct.unpack("<H", data[14:16])[0]
                    rel = packet_address - base_address
                    if not 0 <= rel < count:
                        continue

                    # Parse DMX payload
                    length = struct.unpack(">H", data[16:18])[0]
                    dmx_data = list(data[18: 18 + length])
                    if len(dmx_data) < 512:
                        dmx_data.extend([0] * (512 - len(dmx_data)))

                    self.dmx_buffers[rel] = dmx_data[:512]
                    self._dirty[rel] = True
                    self.last_artnet_time = time.time()
                    if self._send_event is not None:
                        self._send_event.set()

            except Exception as e:
                self.log(f"Art-Net error: {e}")
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass

            if self.is_running:
                await asyncio.sleep(1)  # Jeda sebelum buka socket baru

    # ----------------------------------------------------------
    # SENDER (rate-limited, semua universe dalam satu pesan)
    # ----------------------------------------------------------

    async def _sender_loop(self):
        """
        Dipicu langsung saat paket Art-Net masuk. Semua universe yang berubah dalam
        jeda SEND_COALESCE digabung dalam satu pesan WebSocket:
        {"Username": ..., "universes": {"1": {"3": 255, ...}, "2": {...}}}
        Channel bernilai 0 tidak dikirim (server menganggapnya 0).
        """
        while self.is_running:
            try:
                await asyncio.wait_for(self._send_event.wait(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            self._send_event.clear()
            await asyncio.sleep(SEND_COALESCE)

            _base, count = self._get_address_range()
            dirty_idx = [i for i in range(count) if self._dirty[i]]
            if not dirty_idx:
                continue

            if not (self.ws_connected and self.websocket):
                # Belum terhubung: data tetap ditandai dirty, coba lagi sebentar lagi
                await asyncio.sleep(0.25)
                self._send_event.set()
                continue

            universes = {}
            for i in dirty_idx:
                self._dirty[i] = False
                universes[str(i + 1)] = {
                    str(ch + 1): val
                    for ch, val in enumerate(self.dmx_buffers[i]) if val
                }

            payload = {"Username": self.username, "universes": universes}
            self.last_send_time = time.time()
            try:
                await asyncio.wait_for(
                    self.websocket.send(json.dumps(payload, separators=(",", ":"))),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                self.log("⚠ Timeout kirim data — koneksi lambat")
                self.ws_connected = False
                for i in dirty_idx:
                    self._dirty[i] = True  # kirim ulang setelah reconnect
            except Exception:
                self.ws_connected = False
                for i in dirty_idx:
                    self._dirty[i] = True

    def _get_address_range(self) -> tuple[int, int]:
        """
        Hitung alamat Art-Net universe pertama (Net/Subnet/Start Universe)
        dan jumlah universe yang didengarkan (1..MAX_UNIVERSES).
        """
        try:
            net = int(self.net_var.get())
            subnet = int(self.subnet_var.get())
            uni = int(self.uni_var.get())
            count = int(self.count_var.get())
        except ValueError:
            return 0, 1
        count = max(1, min(MAX_UNIVERSES, count))
        return (net << 8) | (subnet << 4) | uni, count


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = ArtNetGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
