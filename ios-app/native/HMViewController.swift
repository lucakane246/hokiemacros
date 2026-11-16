import UIKit
import Capacitor

/// The app's main screen. Same as Capacitor's, plus our own WidgetBridge plugin.
class HMViewController: CAPBridgeViewController {
    override func capacitorDidLoad() {
        bridge?.registerPluginInstance(WidgetBridgePlugin())
    }
}
