-- Detiene y cierra la pestaña de demo sin preguntar, SOLO si la pestaña activa es la demo (pista 1 "Nube Meter demo").
-- Si no, no toca nada y lo anota en tests/out/ui_close.txt.
local OUT = debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$") .. "/out"
local f = io.open(OUT .. "/ui_close.txt", "w")
local proj = reaper.EnumProjects(-1)
local tr = reaper.GetTrack(proj, 0)
local name = tr and select(2, reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "", false)) or ""
if name == "Nube Meter demo" and reaper.CountTracks(proj) == 1 then
  reaper.OnStopButtonEx(proj)
  reaper.Main_SaveProjectEx(proj, OUT .. "/_tmp_ui.rpp", 0)
  reaper.Main_openProject("noprompt:" .. OUT .. "/_tmp_ui.rpp")
  reaper.Main_OnCommand(40860, 0)
  f:write("cerrada\n")
else
  f:write("NO cerrada: la pestaña activa no es la demo (" .. name .. ")\n")
end
f:close()
