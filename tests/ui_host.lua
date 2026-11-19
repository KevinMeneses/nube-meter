-- Anfitrión de las pruebas de mouse: se lanza con un REAPER PROPIO (REAPER -new -nosplash tests/ui_host.lua) y
-- no necesita -nonewinst (que mandaría scripts al REAPER del usuario).
--  * espera a que REAPER termine de arrancar, arma la demo (premaster -> Antes -> Nube Limit +12 -> Medidor),
--    abre la ventana del Medidor y reproduce en loop;
--  * cada 0.25 s escribe los parámetros del Medidor en tests/out/dump.txt ("n|valor|formateado");
--  * lee órdenes de tests/out/cmd.txt: play, stop.
local ROOT = debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")
local OUT = ROOT .. "/out"
local t0 = reaper.time_precise()
local proj, tr, med

local function build()
  reaper.Main_OnCommand(40859, 0)
  proj = reaper.EnumProjects(-1)
  reaper.InsertTrackAtIndex(0, false); tr = reaper.GetTrack(proj, 0)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "Nube Meter demo", true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", 0)
  local item = reaper.AddMediaItemToTrack(tr); local take = reaper.AddTakeToMediaItem(item)
  local src = reaper.PCM_Source_CreateFromFile(ROOT .. "/signals/pre.wav"); reaper.SetMediaItemTake_Source(take, src)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", reaper.GetMediaSourceLength(src))
  local a = reaper.TrackFX_AddByName(tr, "JS:Nube Meter/nube_meter.jsfx", false, -1); reaper.TrackFX_SetParam(tr, a, 4, 1)
  local l = reaper.TrackFX_AddByName(tr, "JS:Nube Limit/nube_limit.jsfx", false, -1); reaper.TrackFX_SetParam(tr, l, 0, 12)
  med = reaper.TrackFX_AddByName(tr, "JS:Nube Meter/nube_meter.jsfx", false, -1)
  reaper.TrackFX_Show(tr, med, 3)
  reaper.GetSet_LoopTimeRange2(proj, true, true, 0, reaper.GetMediaSourceLength(src), false)
  reaper.GetSetRepeatEx(proj, 1)
  reaper.SetEditCurPos2(proj, 0, false, false)
  reaper.OnPlayButtonEx(proj)
end

local last = 0
local function loop()
  local now = reaper.time_precise()
  if not proj then
    if now - t0 > 5 then build() end
  elseif now - last > 0.25 then
    last = now
    local c = io.open(OUT .. "/cmd.txt")
    if c then
      local cmd = c:read("l") or ""; c:close(); os.remove(OUT .. "/cmd.txt")
      if cmd == "play" then reaper.OnPlayButtonEx(proj) elseif cmd == "stop" then reaper.OnStopButtonEx(proj) end
    end
    local f = io.open(OUT .. "/dump.tmp", "w")
    for p = 0, reaper.TrackFX_GetNumParams(tr, med) - 1 do
      local _, s = reaper.TrackFX_GetFormattedParamValue(tr, med, p, "")
      f:write(string.format("%d|%.6f|%s\n", p + 1, reaper.TrackFX_GetParam(tr, med, p), s))
    end
    f:write(string.format("play|%d\n", reaper.GetPlayStateEx(proj)))
    f:write("done\n"); f:close(); os.rename(OUT .. "/dump.tmp", OUT .. "/dump.txt")
  end
  reaper.defer(loop)
end
reaper.defer(loop)
