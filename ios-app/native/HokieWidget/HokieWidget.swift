import WidgetKit
import SwiftUI

// Today's totals, written by the app (WidgetBridgePlugin) into the shared App Group.
struct Summary: Codable {
    var date: String
    var goal: Double
    var food: Double
    var exercise: Double
    var c: Double
    var f: Double
    var p: Double
    var cg: Double
    var fg: Double
    var pg: Double

    var left: Double { goal - food + exercise }
    func emptied() -> Summary { var s = self; s.food = 0; s.exercise = 0; s.c = 0; s.f = 0; s.p = 0; return s }
}

private let group = "group.io.github.lucakane246.hokiemacros"

private func todayString(_ d: Date = Date()) -> String {
    let f = DateFormatter()
    f.calendar = Calendar(identifier: .gregorian)
    f.locale = Locale(identifier: "en_US_POSIX")
    f.dateFormat = "yyyy-MM-dd"
    return f.string(from: d)
}

private func loadSummary() -> Summary? {
    guard let str = UserDefaults(suiteName: group)?.string(forKey: "summary"),
          let data = str.data(using: .utf8),
          let s = try? JSONDecoder().decode(Summary.self, from: data) else { return nil }
    return s.date == todayString() ? s : s.emptied()   // a new day starts at zero
}

struct Entry: TimelineEntry {
    let date: Date
    let s: Summary?
}

struct Provider: TimelineProvider {
    static let sample = Summary(date: "", goal: 2200, food: 1350, exercise: 0, c: 150, f: 45, p: 80, cg: 275, fg: 73, pg: 110)

    func placeholder(in context: Context) -> Entry { Entry(date: Date(), s: Provider.sample) }

    func getSnapshot(in context: Context, completion: @escaping (Entry) -> Void) {
        completion(Entry(date: Date(), s: loadSummary() ?? Provider.sample))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<Entry>) -> Void) {
        let now = Date()
        let midnight = Calendar.current.startOfDay(for: now.addingTimeInterval(86_400))
        let s = loadSummary()
        let entries = [Entry(date: now, s: s), Entry(date: midnight, s: s?.emptied())]
        completion(Timeline(entries: entries, policy: .after(midnight.addingTimeInterval(60))))
    }
}

extension Color {
    init(hex: UInt32) {
        self.init(red: Double((hex >> 16) & 255) / 255, green: Double((hex >> 8) & 255) / 255, blue: Double(hex & 255) / 255)
    }
    static let hmBg = Color(hex: 0x110B0E)
    static let hmMaroon = Color(hex: 0x8A2447)
    static let hmOrange = Color(hex: 0xEE8A3C)
    static let hmCarb = Color(hex: 0x69C3B2)
    static let hmFat = Color(hex: 0xE26D8F)
    static let hmProtein = Color(hex: 0xF2A95B)
}

private func fmt(_ v: Double) -> String {
    let n = NumberFormatter(); n.numberStyle = .decimal; n.maximumFractionDigits = 0
    return n.string(from: NSNumber(value: v.rounded())) ?? "\(Int(v))"
}

struct Ring: View {
    let progress: Double
    let width: CGFloat
    var body: some View {
        ZStack {
            Circle().stroke(Color.white.opacity(0.10), lineWidth: width)
            Circle()
                .trim(from: 0, to: min(1, max(0.002, progress)))
                .stroke(LinearGradient(colors: [Color(hex: 0xF5A25D), Color(hex: 0xD2611C)], startPoint: .top, endPoint: .bottom),
                        style: StrokeStyle(lineWidth: width, lineCap: .round))
                .rotationEffect(.degrees(-90))
        }
    }
}

struct MacroRow: View {
    let name: String, value: Double, goal: Double, color: Color
    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 4) {
                Circle().fill(color).frame(width: 6, height: 6)
                Text(name).font(.system(size: 11, weight: .semibold)).foregroundColor(.white.opacity(0.75))
                Spacer(minLength: 2)
                Text("\(fmt(value))").font(.system(size: 12, weight: .bold)).foregroundColor(.white)
                + Text(" / \(fmt(goal))g").font(.system(size: 10.5, weight: .medium)).foregroundColor(.white.opacity(0.5))
            }
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Capsule().fill(color.opacity(0.22))
                    Capsule().fill(color).frame(width: max(4, g.size.width * min(1, goal > 0 ? value / goal : 0)))
                }
            }.frame(height: 5)
        }
    }
}

struct CaloriesBlock: View {
    let s: Summary
    let size: CGFloat
    var body: some View {
        let over = s.left < 0
        ZStack {
            Ring(progress: s.goal > 0 ? s.food / s.goal : 0, width: size * 0.09)
            VStack(spacing: 0) {
                Text(fmt(abs(s.left))).font(.system(size: size * 0.22, weight: .heavy)).foregroundColor(.white).minimumScaleFactor(0.6).lineLimit(1)
                Text(over ? "over" : "left").font(.system(size: size * 0.11, weight: .semibold)).foregroundColor(over ? .hmOrange : .white.opacity(0.6))
            }.padding(.horizontal, size * 0.14)
        }.frame(width: size, height: size)
    }
}

struct WidgetView: View {
    @Environment(\.widgetFamily) var family
    let entry: Entry

    var body: some View {
        content.widgetBackground()
    }

    @ViewBuilder var content: some View {
        if let s = entry.s {
            if family == .systemSmall {
                VStack(alignment: .leading, spacing: 6) {
                    Text("CALORIES").font(.system(size: 10, weight: .heavy)).tracking(0.8).foregroundColor(.hmOrange)
                    HStack { Spacer(); CaloriesBlock(s: s, size: 96); Spacer() }
                    Text("\(fmt(s.food)) of \(fmt(s.goal)) eaten").font(.system(size: 10.5, weight: .medium)).foregroundColor(.white.opacity(0.6))
                        .frame(maxWidth: .infinity, alignment: .center)
                }
            } else {
                HStack(spacing: 14) {
                    VStack(spacing: 4) {
                        CaloriesBlock(s: s, size: 104)
                        Text("of \(fmt(s.goal)) cal").font(.system(size: 10.5, weight: .medium)).foregroundColor(.white.opacity(0.6))
                    }
                    VStack(alignment: .leading, spacing: 9) {
                        Text("TODAY").font(.system(size: 10, weight: .heavy)).tracking(0.8).foregroundColor(.hmOrange)
                        MacroRow(name: "Carbs", value: s.c, goal: s.cg, color: .hmCarb)
                        MacroRow(name: "Fat", value: s.f, goal: s.fg, color: .hmFat)
                        MacroRow(name: "Protein", value: s.p, goal: s.pg, color: .hmProtein)
                    }
                }
            }
        } else {
            VStack(alignment: .leading, spacing: 6) {
                Text("Gobble").font(.system(size: 13, weight: .heavy)).foregroundColor(.hmOrange)
                Text("Open the app and log a meal to see today's calories here.").font(.system(size: 12, weight: .medium)).foregroundColor(.white.opacity(0.8))
            }.frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
    }
}

private extension View {
    @ViewBuilder func widgetBackground() -> some View {
        let bg = LinearGradient(colors: [Color.hmMaroon.opacity(0.55), Color.hmBg], startPoint: .topLeading, endPoint: .bottomTrailing)
        if #available(iOS 17.0, *) {
            self.containerBackground(for: .widget) { ZStack { Color.hmBg; bg } }
        } else {
            self.padding().background(ZStack { Color.hmBg; bg })
        }
    }
}

@main
struct HokieWidget: Widget {
    let kind = "HokieMacrosToday"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            WidgetView(entry: entry)
        }
        .configurationDisplayName("Today")
        .description("Calories left and macros for today.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
