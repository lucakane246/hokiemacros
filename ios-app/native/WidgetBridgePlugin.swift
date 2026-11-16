import Foundation
import Capacitor
import WidgetKit

/// Lets the web app hand today's totals to the home screen widget.
/// The JSON goes into the shared App Group, then the widget is told to redraw.
@objc(WidgetBridgePlugin)
public class WidgetBridgePlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "WidgetBridgePlugin"
    public let jsName = "WidgetBridge"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "update", returnType: CAPPluginReturnPromise)
    ]

    @objc func update(_ call: CAPPluginCall) {
        let json = call.getString("json") ?? "{}"
        UserDefaults(suiteName: "group.io.github.lucakane246.hokiemacros")?.set(json, forKey: "summary")
        WidgetCenter.shared.reloadAllTimelines()
        call.resolve()
    }
}
