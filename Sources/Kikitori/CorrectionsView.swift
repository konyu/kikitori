import SwiftUI
import KikitoriCore

@MainActor
final class CorrectionsViewModel: ObservableObject {
    @Published var pairs: [CorrectionItem] = []
    private let corrections: Corrections

    init(corrections: Corrections) {
        self.corrections = corrections
    }

    func load() {
        corrections.load()
        pairs = corrections.items.map { CorrectionItem(wrong: $0.wrong, right: $0.right) }
    }

    func save() {
        corrections.setPairs(pairs.map { ($0.wrong, $0.right) })
        corrections.save()
        // AppDelegate で持っている Corrections に即時反映される
        // （Corrections クラスが共有インスタンスとして動作しているため）
    }

    func add(wrong: String, right: String) {
        pairs.append(CorrectionItem(wrong: wrong, right: right))
        save()
    }

    func openFile() {
        NSWorkspace.shared.open(Corrections.defaultPath)
    }

    func reload() {
        load()
    }

    func update(id: UUID, wrong: String, right: String) {
        if let idx = pairs.firstIndex(where: { $0.id == id }) {
            pairs[idx].wrong = wrong
            pairs[idx].right = right
            save()
        }
    }

    func delete(ids: Set<UUID>) {
        pairs.removeAll { ids.contains($0.id) }
        save()
    }
}

struct CorrectionItem: Identifiable {
    let id = UUID()
    var wrong: String
    var right: String
}

struct CorrectionsView: View {
    @ObservedObject var vm: CorrectionsViewModel
    @State private var selection: Set<UUID> = []
    @State private var isShowingEditor = false
    @State private var editingItem: CorrectionItem?
    
    @State private var editWrong: String = ""
    @State private var editRight: String = ""

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("ファイル: ~/.kikitori/corrections.yaml")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
                Button(action: { vm.openFile() }) { Label("ファイルを開く", systemImage: "arrow.up.right.square") }
                Button(action: { vm.reload() }) { Label("再読み込み", systemImage: "arrow.clockwise") }
            }
            .padding()

            Table(vm.pairs, selection: $selection) {
                TableColumn("間違い (変換前)", value: \.wrong)
                TableColumn("訂正 (変換後)", value: \.right)
            }
            .frame(minHeight: 200)

            HStack {
                Button(action: openAdd) { Label("追加", systemImage: "plus") }
                Button(action: openEdit) { Label("編集", systemImage: "pencil") }
                    .disabled(selection.count != 1)
                Button(action: deleteSelected) { Label("削除", systemImage: "minus") }
                    .disabled(selection.isEmpty)
                Spacer()
                Button("閉じる") {
                    NSApp.sendAction(#selector(NSWindow.performClose(_:)), to: nil, from: nil)
                }
            }
            .padding()
        }
        .frame(minWidth: 480, minHeight: 360)
        .onAppear { vm.load() }
        .sheet(isPresented: $isShowingEditor) {
            editorSheet
        }
    }

    private func openAdd() {
        editingItem = nil
        editWrong = ""
        editRight = ""
        isShowingEditor = true
    }

    private func openEdit() {
        guard let id = selection.first, let item = vm.pairs.first(where: { $0.id == id }) else { return }
        editingItem = item
        editWrong = item.wrong
        editRight = item.right
        isShowingEditor = true
    }

    private func deleteSelected() {
        vm.delete(ids: selection)
        selection.removeAll()
    }

    private var editorSheet: some View {
        VStack(spacing: 20) {
            Text(editingItem == nil ? "ペアを追加" : "ペアを編集")
                .font(.headline)
            Form {
                TextField("間違い (例: use effect):", text: $editWrong)
                TextField("訂正 (例: useEffect):", text: $editRight)
            }
            .frame(width: 320)
            HStack {
                Button("キャンセル") { isShowingEditor = false }
                Button("保存") {
                    let w = editWrong.trimmingCharacters(in: .whitespaces)
                    let r = editRight.trimmingCharacters(in: .whitespaces)
                    if !w.isEmpty, !r.isEmpty {
                        if let item = editingItem {
                            vm.update(id: item.id, wrong: w, right: r)
                        } else {
                            vm.add(wrong: w, right: r)
                        }
                    }
                    isShowingEditor = false
                }
                .keyboardShortcut(.defaultAction)
                .disabled(editWrong.trimmingCharacters(in: .whitespaces).isEmpty || editRight.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(24)
    }
}

// MARK: - Window Controller

final class CorrectionsWindowController: NSWindowController {
    private let vm: CorrectionsViewModel

    init(corrections: Corrections) {
        self.vm = CorrectionsViewModel(corrections: corrections)
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 480, height: 360),
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: true
        )
        window.title = "Kikitori 校正設定"
        window.center()
        window.isReleasedWhenClosed = false
        super.init(window: window)

        let view = CorrectionsView(vm: vm)
        window.contentViewController = NSHostingController(rootView: view)
    }

    required init?(coder: NSCoder) { fatalError() }

    func show() {
        vm.load()
        window?.center()
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}
