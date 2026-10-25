--[[
    DMX Bridge - Multi-Universe (release)

    Cara pakai:
      1. Jalankan Server_multi_universe_polling.py
      2. Jalankan artnet2WSS.py, isi username (sama dengan nama akun Roblox)
      3. Masuk ke game, jalankan script ini di executor

    Script ini mengambil frame dari server lokal (HTTP /polling) lalu mengirimnya ke:
      workspace.Vehicles["<username>'s Car"].UDP_DMXDATA

    Format FireServer (satu argumen berupa tabel):
      BATCH_MODE = false : { [universe] = buffer512 }
      BATCH_MODE = true  : { [universe] = { {buffer = buffer512, dt = 0}, {buffer = buffer512, dt = 25} } }
                           dt = jeda ms dari frame sebelumnya di universe yang sama.

    Menjalankan script ini lagi otomatis menghentikan instance sebelumnya.
    Berhenti manual: _G.ResetSpesificScripts = true
]]

local HttpService = game:GetService("HttpService")
local RunService = game:GetService("RunService")
local request = http_request or request or (syn and syn.request)

if not request then
    error("[DMX] Executor tidak mendukung HTTP request")
    return
end

-- Hentikan instance lama supaya tidak ada pengiriman ganda
if type(_G.DMXBridgeStop) == "function" then
    pcall(_G.DMXBridgeStop)
end

-- ============================================================
-- Setting (default sudah optimal, tidak perlu diubah)
-- ============================================================
local BASE_URL = "http://127.0.0.1:5311/polling"
local BATCH_MODE = false          -- false = realtime per frame, true = batch + dt
local POLL_INTERVAL = 1 / 60      -- mode biasa
local BATCH_POLL_INTERVAL = 0.05  -- mode batch
local MAX_BACKLOG = 6             -- batas antrean per universe (~130 ms), cegah delay menumpuk
local MAX_UNIVERSES = 8
-- ============================================================

local running = true
local connections = {}
local vehicles = {}     -- [username huruf kecil] = {remote = RemoteEvent, name = "Username"}
local frameQueues = {}  -- [username huruf kecil] = { [universe] = { buffer, ... } }
local lastFrameTs = {}  -- [username huruf kecil] = { [universe] = timestamp }   (mode batch)
local fireErrors = 0
local lastMissingWarn = 0

local function stop()
    if not running then return end
    running = false
    for _, c in ipairs(connections) do
        pcall(function() c:Disconnect() end)
    end
    if _G.DMXBridgeStop == stop then
        _G.DMXBridgeStop = nil
    end
    print("[DMX] Dihentikan.")
end
_G.DMXBridgeStop = stop
_G.ResetSpesificScripts = false

-- ------------------------------------------------------------
-- Kendaraan
-- ------------------------------------------------------------
local VehiclesFolder = workspace:WaitForChild("Vehicles", 15)
if not VehiclesFolder then
    stop()
    error("[DMX] workspace.Vehicles tidak ditemukan. Pastikan kamu sudah berada di dalam game.")
    return
end

local function usernameFromModel(model)
    return (model.Name:gsub("'s Car$", ""))
end

local function registerVehicle(model)
    if not model:IsA("Model") then return end
    local name = usernameFromModel(model)
    task.spawn(function()
        local remote = model:WaitForChild("UDP_DMXDATA", 10)
        if not running then return end
        if remote and remote:IsA("RemoteEvent") then
            vehicles[name:lower()] = {remote = remote, name = name}
            print("[DMX] Mobil terdeteksi: " .. name)
        else
            warn("[DMX] RemoteEvent 'UDP_DMXDATA' tidak ada di: " .. model.Name)
        end
    end)
end

table.insert(connections, VehiclesFolder.ChildRemoved:Connect(function(model)
    local key = usernameFromModel(model):lower()
    local vehicle = vehicles[key]
    -- hanya hapus kalau yang dihapus memang mobil yang terdaftar
    if vehicle and (not vehicle.remote.Parent or vehicle.remote:IsDescendantOf(model)) then
        vehicles[key] = nil
        frameQueues[key] = nil
        lastFrameTs[key] = nil
    end
end))

for _, child in ipairs(VehiclesFolder:GetChildren()) do
    registerVehicle(child)
end
table.insert(connections, VehiclesFolder.ChildAdded:Connect(registerVehicle))

-- ------------------------------------------------------------
-- Data
-- ------------------------------------------------------------
-- Buffer mulai dari 0, jadi channel yang tidak dikirim server otomatis bernilai 0.
local function createDmxBuffer(channelData)
    local dmxBuf = buffer.create(512)
    for ch, val in pairs(channelData) do
        local chNum = tonumber(ch)
        local value = tonumber(val)
        if chNum and value and chNum >= 1 and chNum <= 512 then
            buffer.writeu8(dmxBuf, chNum - 1, math.clamp(math.floor(value), 0, 255))
        end
    end
    return dmxBuf
end

-- Key "t1".."tN" yang valid, urut numerik.
local function sortedFrameKeys(frames)
    local keys = {}
    for k in pairs(frames) do
        if type(k) == "string" and tonumber(k:sub(2)) then
            table.insert(keys, k)
        end
    end
    table.sort(keys, function(a, b)
        return tonumber(a:sub(2)) < tonumber(b:sub(2))
    end)
    return keys
end

local function validUniverse(raw)
    local universe = tonumber(raw)
    if universe and universe >= 1 and universe <= MAX_UNIVERSES and universe == math.floor(universe) then
        return universe
    end
    return nil
end

-- Mode biasa: simpan frame terbaru saja (antrean pendek = delay terbatas).
local function enqueueFrames(key, universes)
    local userQueues = frameQueues[key]
    if not userQueues then
        userQueues = {}
        frameQueues[key] = userQueues
    end
    for rawUniverse, frames in pairs(universes) do
        local universe = validUniverse(rawUniverse)
        if universe and type(frames) == "table" then
            local q = userQueues[universe]
            if not q then
                q = {}
                userQueues[universe] = q
            end
            for _, frameKey in ipairs(sortedFrameKeys(frames)) do
                local frame = frames[frameKey]
                if type(frame) == "table" and type(frame.channels) == "table" then
                    table.insert(q, createDmxBuffer(frame.channels))
                    while #q > MAX_BACKLOG do
                        table.remove(q, 1)
                    end
                end
            end
        end
    end
end

-- Mode batch: {[universe] = { {buffer=, dt=}, ... }}
local function buildBatch(key, universes)
    local userLast = lastFrameTs[key]
    if not userLast then
        userLast = {}
        lastFrameTs[key] = userLast
    end

    local batch, any = {}, false
    for rawUniverse, frames in pairs(universes) do
        local universe = validUniverse(rawUniverse)
        if universe and type(frames) == "table" then
            local list = {}
            for _, frameKey in ipairs(sortedFrameKeys(frames)) do
                local frame = frames[frameKey]
                if type(frame) == "table" and type(frame.channels) == "table" then
                    local ts = tonumber(frame.timestamp) or 0
                    local prev = userLast[universe]
                    local dt = 0
                    if prev then
                        dt = math.clamp(math.floor((ts - prev) * 1000 + 0.5), 0, 4095)
                    end
                    userLast[universe] = ts
                    table.insert(list, {buffer = createDmxBuffer(frame.channels), dt = dt})
                end
            end
            if #list > 0 then
                batch[universe] = list
                any = true
            end
        end
    end
    return any and batch or nil
end

-- ------------------------------------------------------------
-- Pengiriman
-- ------------------------------------------------------------
local function fire(key, vehicle, payload)
    local remote = vehicle.remote
    if not remote.Parent then
        vehicles[key] = nil
        return false
    end
    local ok, err = pcall(remote.FireServer, remote, payload)
    if not ok then
        fireErrors += 1
        if fireErrors == 1 or fireErrors % 300 == 0 then
            warn("[DMX] FireServer gagal (" .. fireErrors .. "x): " .. tostring(err))
        end
    end
    return ok
end

local function warnMissingVehicle(username)
    local now = os.clock()
    if now - lastMissingWarn < 10 then return end
    lastMissingWarn = now
    local names = {}
    for _, v in pairs(vehicles) do
        table.insert(names, "'" .. v.name .. "'")
    end
    warn(("[DMX] Tidak ada mobil untuk username '%s'. Mobil terdeteksi: %s. "
        .. "Username di artnet2WSS.py harus sama dengan nama akun Roblox."):format(
        username, #names > 0 and table.concat(names, ", ") or "(belum ada)"))
end

local function processBody(body)
    for username, universes in pairs(body.data) do
        if type(username) == "string" and type(universes) == "table" then
            local key = username:lower()
            local vehicle = vehicles[key]
            if not vehicle then
                warnMissingVehicle(username)
            elseif BATCH_MODE then
                local batch = buildBatch(key, universes)
                if batch then
                    fire(key, vehicle, batch)
                end
            else
                enqueueFrames(key, universes)
            end
        end
    end
end

-- Mode biasa: tiap Heartbeat kirim 1 frame per universe (digabung dalam satu tabel per user).
table.insert(connections, RunService.Heartbeat:Connect(function()
    if not running or BATCH_MODE then return end
    for key, userQueues in pairs(frameQueues) do
        local vehicle = vehicles[key]
        if not vehicle then
            frameQueues[key] = nil
        else
            local payload, any = {}, false
            for universe, q in pairs(userQueues) do
                if #q > 0 then
                    payload[universe] = table.remove(q, 1)
                    any = true
                end
            end
            if any then
                fire(key, vehicle, payload)
            end
        end
    end
end))

-- ------------------------------------------------------------
-- Polling
-- ------------------------------------------------------------
task.spawn(function()
    local interval = BATCH_MODE and BATCH_POLL_INTERVAL or POLL_INTERVAL
    local failures = 0
    local everConnected = false
    local warned = false

    while running do
        if _G.ResetSpesificScripts == true then
            _G.ResetSpesificScripts = false
            stop()
            return
        end

        local startTime = os.clock()
        local good = false

        local ok, response = pcall(request, {Url = BASE_URL, Method = "GET"})
        if ok and type(response) == "table" and response.StatusCode == 200 then
            local decodeOk, body = pcall(HttpService.JSONDecode, HttpService, response.Body)
            if decodeOk and type(body) == "table" and type(body.data) == "table" then
                good = true
                if not everConnected then
                    everConnected = true
                    print("[DMX] Terhubung ke server.")
                elseif warned then
                    print("[DMX] Terhubung kembali ke server.")
                end
                failures = 0
                warned = false
                local processOk, processErr = pcall(processBody, body)
                if not processOk then
                    warn("[DMX] Error memproses data: " .. tostring(processErr))
                end
            end
        end

        if not good then
            failures += 1
            if failures >= 30 and not warned then
                warned = true
                warn("[DMX] Server tidak terjangkau di " .. BASE_URL
                    .. ". Pastikan Server_multi_universe_polling.py sedang berjalan.")
            end
        end

        -- Server mati: jangan banjiri dengan request, cek tiap 1 detik saja.
        local wait = (failures >= 30) and 1 or interval
        task.wait(math.max(0, wait - (os.clock() - startTime)))
    end
end)

print("[DMX] Siap. Mode: " .. (BATCH_MODE and "batch" or "realtime") .. ". Menunggu data dari server...")
