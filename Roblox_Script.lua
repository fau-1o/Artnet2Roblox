--[[
    DMX Internal Bridge — Executor Version (Smooth Edition)
    
    Cara kerja:
    
        [THREAD POLLING]  setiap ~1/44 detik
            → HTTP GET /polling
            → dapat batch frame t1..tN per user
            → masukkan semua ke frameQueue per user (FIFO)
    
        [THREAD DRAIN]  setiap Heartbeat (~1/60 detik)
            → ambil 1 frame dari depan queue tiap user
            → FireServer ke RemoteEvent
    
        Hasilnya: tidak ada burst, frame keluar 1-per-Heartbeat,
        gerakan terasa smooth seperti video 60fps.
        
    Catatan:
        Queue diberi batas maxQueueSize agar tidak menumpuk
        jika polling lebih cepat dari drain (anti memory leak).
]]

local HttpService  = game:GetService("HttpService")
local RunService   = game:GetService("RunService")
local request      = http_request or request or (syn and syn.request)

_G.ResetSpesificScripts = false

if not request then
    error("Executor tidak mendukung HTTP request")
    return
end

-- ============================================================
-- KONFIGURASI
-- ============================================================
local BASE_URL      = "http://127.0.0.1:5311/polling"
local POLL_INTERVAL = 1 / 44   -- seberapa sering tanya server

-- Batas maksimal frame yang boleh menunggu di queue per user.
-- Jika queue penuh, frame paling lama dibuang (drop head).
-- Rumus: (POLL_INTERVAL * 44fps * buffer_time_detik)
-- 30 frame ≈ buffer ~0.5 detik — cukup besar tanpa bikin lag
local MAX_QUEUE_SIZE = 30

-- ============================================================
-- CACHE KENDARAAN
-- ============================================================
local VehiclesFolder = workspace:WaitForChild("Vehicles")
local vehicleCache   = {}   -- { ["username"] = RemoteEvent }

local function registerVehicle(model)
    local username = model.Name:gsub("'s Car", "")
    task.spawn(function()
        local remoteData = model:WaitForChild("Data", 10)
        if remoteData and remoteData:IsA("RemoteEvent") then
            vehicleCache[username] = remoteData
            print("[DMX] Cached: " .. username)
        else
            warn("[DMX] Tidak ada RemoteEvent 'Data' di: " .. model.Name)
        end
    end)
end

VehiclesFolder.ChildRemoved:Connect(function(model)
    local username = model.Name:gsub("'s Car", "")
    if vehicleCache[username] then
        vehicleCache[username] = nil
        print("[DMX] Cache cleared: " .. username)
    end
end)

for _, child in ipairs(VehiclesFolder:GetChildren()) do
    registerVehicle(child)
end
VehiclesFolder.ChildAdded:Connect(registerVehicle)

-- ============================================================
-- FRAME QUEUE  { ["username"] = { dmxBuffer, dmxBuffer, ... } }
-- ============================================================
local frameQueues = {}   -- antrian buffer per user, index 1 = paling lama

local function enqueueFrame(username, dmxBuf)
    if not frameQueues[username] then
        frameQueues[username] = {}
    end
    local q = frameQueues[username]
    table.insert(q, dmxBuf)

    -- Buang frame paling lama jika queue terlalu penuh
    if #q > MAX_QUEUE_SIZE then
        table.remove(q, 1)
    end
end

-- ============================================================
-- BUAT ROBLOX BUFFER DARI DATA CHANNEL
-- ============================================================
local function createDmxBuffer(channelData)
    local dmxBuf = buffer.create(512)
    for ch, val in pairs(channelData) do
        local chNum = tonumber(ch)
        if chNum and chNum >= 1 and chNum <= 512 then
            buffer.writeu8(dmxBuf, chNum - 1, math.clamp(val, 0, 255))
        end
    end
    return dmxBuf
end

-- ============================================================
-- THREAD 1: POLLING SERVER  (isi queue)
-- ============================================================
task.spawn(function()
    print("[DMX] Polling thread started → " .. BASE_URL)

    while true do
        -- Cek flag reset
        if _G.ResetSpesificScripts == true then
            _G.ResetSpesificScripts = false
            print("[DMX] Dihentikan via ResetSpesificScripts")
            script:Destroy()
            return
        end

        local startTime = tick()

        local ok, response = pcall(function()
            return request({ Url = BASE_URL, Method = "GET" })
        end)

        if ok and response and response.StatusCode == 200 then
            local decodeOk, body = pcall(HttpService.JSONDecode, HttpService, response.Body)

            if decodeOk and type(body) == "table" and type(body.data) == "table" then
                for username, frames in pairs(body.data) do
                    -- Urutkan kunci t1, t2, ... secara numeric
                    local keys = {}
                    for k in pairs(frames) do
                        table.insert(keys, k)
                    end
                    table.sort(keys, function(a, b)
                        return tonumber(a:sub(2)) < tonumber(b:sub(2))
                    end)

                    -- Buat buffer untuk setiap frame lalu masukkan ke queue
                    for _, key in ipairs(keys) do
                        local frame = frames[key]
                        if type(frame) == "table" and type(frame.channels) == "table" then
                            local dmxBuf = createDmxBuffer(frame.channels)
                            enqueueFrame(username, dmxBuf)
                        end
                    end
                end
            end
        end

        -- Jaga interval polling
        local elapsed  = tick() - startTime
        local waitTime = math.max(0, POLL_INTERVAL - elapsed)
        task.wait(waitTime)
    end
end)

-- ============================================================
-- THREAD 2: DRAIN QUEUE  (keluarkan 1 frame per Heartbeat)
-- ============================================================
RunService.Heartbeat:Connect(function()
    for username, q in pairs(frameQueues) do
        if #q > 0 then
            local dmxBuf = table.remove(q, 1)   -- ambil frame paling lama (FIFO)
            local remote = vehicleCache[username]
            if remote then
                remote:FireServer(dmxBuf)
            end
        end
    end
end)

print("[DMX] Bridge ready.")
