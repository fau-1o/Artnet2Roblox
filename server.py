import asyncio
import json
import time
from datetime import datetime, timezone
from collections import deque

from aiohttp import web

# ============================================================
# KONFIGURASI SERVER
# ============================================================
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5311

# Berapa frame per polling request yang disimpan
POLLING_FRAMES = 100

# Throttle broadcast ke subscriber WebSocket (detik)
# Contoh: 0.033 = ~30fps, 0.022 = ~44fps
BROADCAST_INTERVAL = 0.033

# Berapa detik tanpa data sampai user dianggap tidak aktif (untuk cleanup)
USER_IDLE_TIMEOUT = 60.0

# Jeda reconnect: jika jarak antar frame lebih dari ini, kosongkan ember
RECONNECT_GAP_THRESHOLD = 0.5

# ============================================================
# STATE GLOBAL
# ============================================================
global_dmx_data: dict = {}
user_buffers: dict[str, deque] = {}
user_last_seen: dict[str, float] = {}
subscribers: set = set()

# Flag agar broadcast tidak ditrigger terlalu sering
_broadcast_pending = False


# ============================================================
# HELPERS
# ============================================================

def normalize_dmx_payload(payload: dict):
    """
    Parse payload masuk. Return (username, processed_data) atau (None, None).
    processed_data TIDAK menyertakan channel bernilai 0 (efisiensi ukuran).
    """
    if not isinstance(payload, dict):
        return None, None

    username = (
        payload.get("Username")
        or payload.get("username")
        or payload.get("name")
    )
    raw_data = (
        payload.get("data")
        or payload.get("dmx")
        or payload.get("channels")
    )

    if not username or not isinstance(raw_data, dict):
        return None, None

    processed_data: dict[str, int] = {}
    for channel_str, value in raw_data.items():
        try:
            channel = int(channel_str)
            val = int(value)
        except (TypeError, ValueError):
            continue

        if 1 <= channel <= 512:
            clamped = max(0, min(255, val))
            if clamped > 0:  # Skip channel bernilai 0 — hemat bandwidth
                processed_data[str(channel)] = clamped

    return str(username), processed_data


async def safe_send(websocket: web.WebSocketResponse, payload: dict) -> bool:
    """Kirim JSON ke websocket. Return False jika gagal (koneksi mati)."""
    try:
        await websocket.send_str(json.dumps(payload, separators=(",", ":")))
        return True
    except Exception:
        return False


# ============================================================
# BROADCAST THROTTLED
# ============================================================

async def schedule_broadcast():
    """
    Jadwalkan satu broadcast ke semua subscriber.
    Jika sudah ada broadcast pending, skip — tidak perlu double trigger.
    Ini mencegah spam broadcast kalau data Art-Net masuk 40+ frame/detik.
    """
    global _broadcast_pending
    if _broadcast_pending:
        return
    _broadcast_pending = True
    await asyncio.sleep(BROADCAST_INTERVAL)
    _broadcast_pending = False
    await broadcast_state()


async def broadcast_state():
    """Kirim state terkini ke semua subscriber aktif."""
    if not subscribers:
        return

    message = json.dumps(
        {
            "type": "state",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "data": global_dmx_data,
        },
        separators=(",", ":"),
    )

    stale: list[web.WebSocketResponse] = []
    for ws in list(subscribers):
        try:
            await ws.send_str(message)
        except Exception:
            stale.append(ws)

    for ws in stale:
        subscribers.discard(ws)


# ============================================================
# CLEANUP IDLE USERS
# ============================================================

async def cleanup_idle_users():
    """
    Background task: hapus user_buffers dan global_dmx_data untuk user
    yang sudah lama tidak mengirim data.
    Mencegah memory leak jika banyak client sementara masuk lalu pergi.
    """
    while True:
        await asyncio.sleep(30)  # Cek tiap 30 detik
        now = time.time()
        idle_users = [
            username
            for username, last_seen in list(user_last_seen.items())
            if now - last_seen > USER_IDLE_TIMEOUT
        ]
        for username in idle_users:
            user_buffers.pop(username, None)
            global_dmx_data.pop(username, None)
            user_last_seen.pop(username, None)

        if idle_users:
            print(f"[Cleanup] Removed {len(idle_users)} idle user(s): {idle_users}")


# ============================================================
# MESSAGE PROCESSING
# ============================================================

async def process_ws_message(websocket: web.WebSocketResponse, raw_message: str) -> bool:
    """
    Proses satu pesan WebSocket.
    Return True  → websocket ini adalah subscriber (bukan pengirim data).
    Return False → data DMX diproses, atau ada error.
    """
    try:
        payload = json.loads(raw_message)
    except json.JSONDecodeError:
        await safe_send(websocket, {"type": "error", "message": "Data bukan JSON yang valid."})
        return False

    if not isinstance(payload, dict):
        await safe_send(websocket, {"type": "error", "message": "Payload harus berupa objek JSON."})
        return False

    # --- Subscribe request ---
    if payload.get("type") == "subscribe":
        subscribers.add(websocket)
        await safe_send(
            websocket,
            {"type": "subscribed", "data": global_dmx_data},
        )
        return True  # Tandai sebagai subscriber

    # --- DMX data ---
    username, processed_data = normalize_dmx_payload(payload)
    if username is None:
        await safe_send(websocket, {"type": "error", "message": "Payload DMX tidak valid."})
        return False

    # Update waktu terakhir aktif
    now = time.time()
    user_last_seen[username] = now

    # --- RECONNECT GUARD ---
    # Jika ada jeda panjang sejak frame terakhir (klien baru reconnect atau
    # lama idle), kosongkan ember agar tidak ada frame lama yang ikut terkirim.
    if username in user_buffers and len(user_buffers[username]) > 0:
        last_frame_time = user_buffers[username][-1]["timestamp"]
        if now - last_frame_time > RECONNECT_GAP_THRESHOLD:
            user_buffers[username].clear()
    # ----------------------

    # Buat ember jika user baru
    if username not in user_buffers:
        user_buffers[username] = deque(maxlen=POLLING_FRAMES)

    # Simpan ke global state dan ember
    global_dmx_data[username] = processed_data
    user_buffers[username].append(
        {
            "timestamp": now,
            "channels": processed_data,
        }
    )

    # Jadwalkan broadcast (throttled, tidak langsung)
    asyncio.create_task(schedule_broadcast())

    return False


# ============================================================
# WEBSOCKET HANDLER
# ============================================================

async def websocket_handler(request: web.Request):
    """Tangani koneksi WebSocket atau HTTP GET biasa di path yang sama."""
    ws = web.WebSocketResponse(heartbeat=30)
    ready = ws.can_prepare(request)

    if not ready.ok:
        # Bukan WebSocket upgrade — kirim info endpoint saja
        return web.json_response(
            {
                "message": "Art-Net bridge ready.",
                "websocket": {"primary": "/", "alternate": "/ws"},
                "http": {"state": "/state", "polling": "/polling"},
            }
        )

    await ws.prepare(request)
    is_subscriber = False

    await safe_send(ws, {"type": "hello", "message": "Art-Net bridge ready."})

    try:
        async for message in ws:
            if message.type == web.WSMsgType.TEXT:
                is_sub = await process_ws_message(ws, message.data)
                if is_sub:
                    is_subscriber = True
            elif message.type in (web.WSMsgType.ERROR, web.WSMsgType.CLOSE):
                break
    finally:
        if is_subscriber:
            subscribers.discard(ws)

    return ws


# ============================================================
# HTTP ENDPOINTS
# ============================================================

async def get_state(_request: web.Request) -> web.Response:
    """HTTP GET /state — snapshot terkini, satu frame per user."""
    return web.json_response(
        {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "data": global_dmx_data,
        },
        headers={"Cache-Control": "no-store"},
    )


async def get_polling_data(_request: web.Request) -> web.Response:
    """
    HTTP GET /polling — ambil semua frame terakumulasi per user,
    format ke t1, t2, ..., tN, lalu kosongkan ember.
    """
    response_data: dict = {}

    for username, buffer in list(user_buffers.items()):
        if not buffer:
            continue

        frames_list = list(buffer)
        buffer.clear()  # Kosongkan setelah diambil

        response_data[username] = {
            f"t{i + 1}": frame for i, frame in enumerate(frames_list)
        }

    return web.json_response(
        {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "data": response_data,
        },
        headers={"Cache-Control": "no-store"},
    )


# ============================================================
# APP SETUP
# ============================================================

def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", websocket_handler)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_get("/state", get_state)
    app.router.add_get("/polling", get_polling_data)
    return app


async def main():
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, SERVER_HOST, SERVER_PORT)
    await site.start()

    # Jalankan background cleanup task
    asyncio.create_task(cleanup_idle_users())

    print("=" * 50)
    print("Art-Net Bridge Server — READY")
    print(f"  WebSocket      : ws://0.0.0.0:{SERVER_PORT}/")
    print(f"  WebSocket alt  : ws://0.0.0.0:{SERVER_PORT}/ws")
    print(f"  HTTP state     : http://0.0.0.0:{SERVER_PORT}/state")
    print(f"  HTTP polling   : http://0.0.0.0:{SERVER_PORT}/polling")
    print(f"  Broadcast rate : ~{1/BROADCAST_INTERVAL:.0f} fps (throttled)")
    print(f"  Idle cleanup   : after {USER_IDLE_TIMEOUT:.0f}s")
    print("=" * 50)

    try:
        await asyncio.Future()  # Block selamanya
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())