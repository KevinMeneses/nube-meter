// Lista las ventanas de REAPER (id, pid, nombre, tamaño) para capturar la del FX con screencapture -l <id>
import CoreGraphics
let l = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as! [[String: Any]]
for w in l {
  if let o = w["kCGWindowOwnerName"] as? String, o == "REAPER" {
    let n = w["kCGWindowName"] as? String ?? ""
    let b = w["kCGWindowBounds"] as? [String: Any] ?? [:]
    print(w["kCGWindowNumber"]!, w["kCGWindowOwnerPID"]!, n, b["Width"] ?? 0, b["Height"] ?? 0)
  }
}
