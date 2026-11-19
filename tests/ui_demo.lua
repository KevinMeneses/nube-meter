-- Demo de la interfaz: pestaña nueva con 45 s del premaster de Nube baja -> Nube Meter (Antes) -> Nube Limit +12 ->
-- Nube Meter (Medidor), fader en -inf (no suena), ventana del Medidor flotante y reproducción en loop.
-- Opciones (REAPER no ve las variables de la terminal): tests/out/demo_opts.txt = "ganancia_del_limitador"
-- Cerrar con tests/ui_close.lua.
local ROOT = debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")
local o = io.open(ROOT .. "/out/demo_opts.txt"); local gain = 12
if o then gain = tonumber(o:read("l")) or 12; o:close() end
local AUDIO = ROOT .. "/signals/pre.wav"
reaper.Main_OnCommand(40859, 0)
local proj = reaper.EnumProjects(-1)
reaper.InsertTrackAtIndex(0, false); local tr = reaper.GetTrack(proj, 0)
reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "Nube Meter demo", true)
reaper.SetMediaTrackInfo_Value(tr, "D_VOL", 0)
local item = reaper.AddMediaItemToTrack(tr); local take = reaper.AddTakeToMediaItem(item)
local src = reaper.PCM_Source_CreateFromFile(AUDIO); reaper.SetMediaItemTake_Source(take, src)
reaper.SetMediaItemInfo_Value(item, "D_LENGTH", reaper.GetMediaSourceLength(src))
reaper.UpdateArrange()
local a = reaper.TrackFX_AddByName(tr, "JS:Nube Meter/nube_meter.jsfx", false, -1); reaper.TrackFX_SetParam(tr, a, 4, 1)
local l = reaper.TrackFX_AddByName(tr, "JS:Nube Limit/nube_limit.jsfx", false, -1); reaper.TrackFX_SetParam(tr, l, 0, gain)
local m = reaper.TrackFX_AddByName(tr, "JS:Nube Meter/nube_meter.jsfx", false, -1)
reaper.TrackFX_Show(tr, m, 3)
reaper.GetSet_LoopTimeRange2(proj, true, true, 0, reaper.GetMediaSourceLength(src), false)
reaper.SetEditCurPos2(proj, 0, false, false)
reaper.GetSetRepeatEx(proj, 1)
reaper.OnPlayButtonEx(proj)
local f = io.open(ROOT .. "/out/ui.txt", "w"); f:write("done\n"); f:close()
