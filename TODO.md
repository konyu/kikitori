# Kikitori 残タスクリスト

## 進行中: Dockアイコン設定

- [x] `kikitori/ui_pyside.py` に Dock アイコン設定コードを追加
  - `NSApp.setApplicationIconImage_()` を使用（macOS ネイティブ API）
  - `assets/dock-icon.png` を読み込む
  - `AppKit` のインポートが必要

- [x] `pyside_main.py` または `ui_pyside.py` でアイコンリソースパスを解決
  - Homebrew インストール時: `/opt/homebrew/Cellar/kikitori/1.0.x/libexec/assets/dock-icon.png`
  - 開発時: `./assets/dock-icon.png`

## リリース作業

- [x] `assets/dock-icon.png` を含めてコミット
- [x] `v1.0.2` タグを作成・push
- [x] GitHub アーカイブ SHA256 を計算
- [x] `homebrew-kikitori` Formula を更新（URL・SHA256）
- [x] Homebrew インストールテスト（v1.0.2 インストール成功）
- [x] `homebrew-kikitori` tap への push（SSH 経由で成功）

## オプション / 今後の改善

- [ ] メニューバーアイコンも `dock-icon.png` と統一（現在は `icon-idle.png` / `icon-recording.png`）
- [ ] アプリケーションメニュー（Dock アイコン右クリック）に「設定」「終了」を追加
- [ ] 初回起動時のチュートリアル / 権限ガイド
- [ ] オーバーレイUIのデザイン調整（色・サイズ・位置）
- [ ] 自動アップデート機能（Homebrew `brew upgrade` で十分か検討）
