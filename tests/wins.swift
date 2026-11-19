// Lista las ventanas de REAPER: id, pid, x, y, ancho, alto, nombre (puntos de pantalla)
import CoreGraphics
let l = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as! [[String: Any]]
for w in l {
  if let o = w["kCGWindowOwnerName"] as? String, o == "REAPER" {
    let n = w["kCGWindowName"] as? String ?? ""
    let b = w["kCGWindowBounds"] as? [String: Any] ?? [:]
    print(w["kCGWindowNumber"]!, w["kCGWindowOwnerPID"]!, b["X"] ?? 0, b["Y"] ?? 0, b["Width"] ?? 0, b["Height"] ?? 0, n)
  }
}
