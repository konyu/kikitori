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
    @ObservedObject var i18n: I18n
    @State private var selection: Set<UUID> = []
    @State private var isShowingEditor = false
    @State private var editingItem: CorrectionItem?
    
    @State private var editWrong: String = ""
    @State private var editRight: String = ""

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("~/.kikitori/corrections.yaml")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
                Button(action: { vm.openFile() }) { Label(i18n.t(.correctionsOpenFile), systemImage: "arrow.up.right.square") }
                Button(action: { vm.reload() }) { Label(i18n.t(.correctionsReload), systemImage: "arrow.clockwise") }
            }
            .padding()

            Table(vm.pairs, selection: $selection) {
                TableColumn(i18n.t(.correctionsWrongCol), value: \.wrong)
                TableColumn(i18n.t(.correctionsRightCol), value: \.right)
            }
            .frame(minHeight: 200)

            HStack {
                Button(action: openAdd) { Label(i18n.t(.btnAdd), systemImage: "plus") }
                Button(action: openEdit) { Label(i18n.t(.btnEdit), systemImage: "pencil") }
                    .disabled(selection.count != 1)
                Button(action: deleteSelected) { Label(i18n.t(.btnDelete), systemImage: "minus") }
                    .disabled(selection.isEmpty)
                Spacer()
                Button(i18n.t(.btnClose)) {
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
            Text(editingItem == nil ? i18n.t(.correctionsAddTitle) : i18n.t(.correctionsEditTitle))
                .font(.headline)
            Form {
                TextField(i18n.t(.correctionsWrongLabel), text: $editWrong)
                TextField(i18n.t(.correctionsRightLabel), text: $editRight)
            }
            .frame(width: 320)
            HStack {
                Button(i18n.t(.settingsCancelBtn)) { isShowingEditor = false }
                Button(i18n.t(.settingsSaveBtn)) {
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

    init(corrections: Corrections, i18n: I18n) {
        self.vm = CorrectionsViewModel(corrections: corrections)
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 480, height: 360),
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: true
        )
        window.title = i18n.t(.correctionsTitle)
        window.center()
        window.isReleasedWhenClosed = false
        super.init(window: window)

        let view = CorrectionsView(vm: vm, i18n: i18n)
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
