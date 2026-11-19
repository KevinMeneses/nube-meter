// Clic con CGEvent: swift tests/click.swift x y [clics]  (clics = 2 -> doble clic con clickState 1 y 2)
// Con cliclick, REAPER 7.86 a veces no ve el "soltar" y la gráfica cree que el botón sigue apretado.
import CoreGraphics
import Foundation
let a = CommandLine.arguments.dropFirst().compactMap { Double($0) }
let (x, y) = (a[0], a[1]); let n = a.count > 2 ? Int(a[2]) : 1
func post(_ t: CGEventType, _ state: Int64) {
    let e = CGEvent(mouseEventSource: nil, mouseType: t, mouseCursorPosition: CGPoint(x: x, y: y), mouseButton: .left)!
    e.setIntegerValueField(.mouseEventClickState, value: state); e.post(tap: .cghidEventTap)
}
post(.mouseMoved, 0); usleep(120000)
for k in 1...n {
    post(.leftMouseDown, Int64(k)); usleep(70000)
    post(.leftMouseUp, Int64(k)); usleep(k < n ? 90000 : 150000)
}
post(.mouseMoved, 0); usleep(100000)
