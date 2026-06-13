# Custom Hotkey

Option 以外のホットキーを設定可能にする。

## 要件
- 設定ファイルでホットキーを指定（例: `ctrl+shift`, `cmd+space`）
- 修飾キーの組み合わせ、または修飾キー＋文字キー
- `NSEvent.addGlobalMonitorForEvents` で監視
- 設定画面から変更可能
