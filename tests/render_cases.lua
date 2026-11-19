-- Renderiza cada caso en una pestaña nueva (Antes -> efecto -> Medidor, o solo el Medidor) y escribe las lecturas.
-- Uso: REAPER -nonewinst tests/render_cases.lua   (escribe tests/out/*.wav y tests/out/log.txt)
local ROOT = debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")
local OUT = ROOT .. "/out"
local METER = "JS:Nube Meter/nube_meter.jsfx"
local LIMIT, CLIP, PROBE = "JS:Nube Limit/nube_limit.jsfx", "JS:Nube Clip/nube_clip.jsfx", "JS:Claude/claude_probe.jsfx"
os.execute('mkdir -p "' .. OUT .. '"')
local logf = io.open(OUT .. "/log.txt", "w")
local function log(...) local t = {} for _, v in ipairs({...}) do t[#t+1] = tostring(v) end logf:write(table.concat(t, " "), "\n") logf:flush() end
local ANTES = {METER, {[5] = 1}}
local MED = {METER, {}}
-- {nombre, señal, cadena = {{fx, {slider = valor}}, ...}}  (el Medidor es el último Nube Meter en modo 0)
local CASES = {
  {"master",     "x20.wav",     {MED}},
  {"probe",      "x20.wav",     {{PROBE, {}}, MED}},
  {"sine",       "s1k_m20.wav", {MED}},
  {"noise",      "noise.wav",   {MED}},
  {"noantes",    "pre.wav",     {{LIMIT, {[1] = 12}}, MED}},
  {"antes_only", "pre.wav",     {ANTES}},
  {"lim_ref",    "pre.wav",     {{LIMIT, {[1] = 12}}}},
  {"lim12",      "pre.wav",     {ANTES, {LIMIT, {[1] = 12}}, MED}},
  {"lim17",      "pre.wav",     {ANTES, {LIMIT, {[1] = 17, [5] = 3}}, MED}},
  {"lim_la5",    "pre.wav",     {ANTES, {LIMIT, {[1] = 12, [4] = 5}}, MED}},
  {"clip_lim",   "pre.wav",     {ANTES, {CLIP, {[1] = 8, [2] = -1, [3] = 3}}, {LIMIT, {[1] = 4}}, MED}},
  {"enlace2",    "pre.wav",     {{METER, {[5] = 1, [6] = 2}}, {LIMIT, {[1] = 12}}, {METER, {[6] = 2}}}},
  {"enlace_mal", "pre.wav",     {{METER, {[5] = 1, [6] = 2}}, {LIMIT, {[1] = 12}}, MED}},
}
local of = io.open(OUT .. "/only.txt"); local only = of and of:read("l") or nil; if of then of:close() end

reaper.Main_OnCommand(40859, 0) -- nueva pestaña
local proj = reaper.EnumProjects(-1)
reaper.GetSetProjectInfo(proj, "PROJECT_SRATE", 48000, true)
reaper.GetSetProjectInfo(proj, "PROJECT_SRATE_USE", 1, true)
reaper.InsertTrackAtIndex(0, false); local tr = reaper.GetTrack(proj, 0)
local item = reaper.AddMediaItemToTrack(tr)
local take = reaper.AddTakeToMediaItem(item)
reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0)

for _, c in ipairs(CASES) do
  local name, src, chain = c[1], c[2], c[3]
  local sel = not only
  if only then for pat in only:gmatch("[^,]+") do if name:find(pat) then sel = true end end end
  if sel then
    local s = reaper.PCM_Source_CreateFromFile(ROOT .. "/signals/" .. src)
    reaper.SetMediaItemTake_Source(take, s)
    reaper.SetMediaItemInfo_Value(item, "D_LENGTH", reaper.GetMediaSourceLength(s))
    reaper.SetMediaItemInfo_Value(item, "D_FADEINLEN", 0); reaper.SetMediaItemInfo_Value(item, "D_FADEOUTLEN", 0)
    reaper.UpdateItemInProject(item)
    while reaper.TrackFX_GetCount(tr) > 0 do reaper.TrackFX_Delete(tr, 0) end
    local med = -1
    for _, f in ipairs(chain) do
      local k = reaper.TrackFX_AddByName(tr, f[1], false, -1)
      if k < 0 then log("ERROR no cargó", f[1]) break end
      for sl, v in pairs(f[2]) do reaper.TrackFX_SetParam(tr, k, sl - 1, v) end
      if f[1] == METER and (f[2][5] or 0) == 0 then med = k end
    end
    local file = OUT .. "/" .. name .. ".wav"
    os.remove(file)
    reaper.GetSetProjectInfo(proj, "RENDER_SETTINGS", 0, true)
    reaper.GetSetProjectInfo(proj, "RENDER_BOUNDSFLAG", 1, true)
    reaper.GetSetProjectInfo(proj, "RENDER_SRATE", 48000, true)
    reaper.GetSetProjectInfo(proj, "RENDER_CHANNELS", 2, true)
    reaper.GetSetProjectInfo(proj, "RENDER_TAILFLAG", 0, true)
    reaper.GetSetProjectInfo_String(proj, "RENDER_FORMAT", "ZXZhdyAAAQ==", true)   -- wav float 32
    reaper.GetSetProjectInfo_String(proj, "RENDER_FILE", OUT, true)
    reaper.GetSetProjectInfo_String(proj, "RENDER_PATTERN", name, true)
    local t0 = reaper.time_precise()
    reaper.Main_OnCommand(42230, 0)
    local info = string.format("t=%.1f", reaper.time_precise() - t0)
    if med >= 0 then
      local vals = {}
      for p = 0, reaper.TrackFX_GetNumParams(tr, med) - 1 do vals[#vals + 1] = string.format("%.6f", reaper.TrackFX_GetParam(tr, med, p)) end
      info = info .. " P=" .. table.concat(vals, ",")
    end
    for k = 0, reaper.TrackFX_GetCount(tr) - 1 do
      local _, fn = reaper.TrackFX_GetFXName(tr, k, "")
      if fn:find("Probe") then info = info .. string.format(" PROBE=%.4f,%.4f,%.0f", reaper.TrackFX_GetParam(tr, k, 0), reaper.TrackFX_GetParam(tr, k, 1), reaper.TrackFX_GetParam(tr, k, 2)) end
    end
    log("caso", name, info)
  end
end
-- presets: cargar cada uno y leer curva / techo / PLR / exigencia / Cargar preset (debe volver a 0)
while reaper.TrackFX_GetCount(tr) > 0 do reaper.TrackFX_Delete(tr, 0) end
local k = reaper.TrackFX_AddByName(tr, METER, false, -1)
for p = 1, 16 do
  reaper.TrackFX_SetParam(tr, k, 10, p)
  log("preset", p, string.format("%g %g %g %g %g", reaper.TrackFX_GetParam(tr, k, 6), reaper.TrackFX_GetParam(tr, k, 7),
    reaper.TrackFX_GetParam(tr, k, 8), reaper.TrackFX_GetParam(tr, k, 9), reaper.TrackFX_GetParam(tr, k, 10)))
end
reaper.Main_SaveProjectEx(proj, OUT .. "/_tmp_test.rpp", 0)
reaper.Main_openProject("noprompt:" .. OUT .. "/_tmp_test.rpp")
reaper.Main_OnCommand(40860, 0) -- cerrar pestaña
log("done")
logf:close()