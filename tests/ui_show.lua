-- Abre la ventana del Medidor (FX 3 de la pista 1) de la pestaña de demo y arranca la reproducción en loop
local proj = reaper.EnumProjects(-1)
local tr = reaper.GetTrack(proj, 0)
if tr and select(2, reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "", false)) == "Nube Meter demo" then
  reaper.TrackFX_Show(tr, 2, 3)
  if reaper.GetPlayStateEx(proj) & 1 == 0 then reaper.OnPlayButtonEx(proj) end
end
