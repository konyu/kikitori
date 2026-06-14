# Kikitori Swift リリース — 作業項目一覧

## 完了済み ✅

### コア実装
- [x] SFSpeechRecognizer によるローカル音声認識
- [x] ホットキー (右 Option) 押下中録音 → 解放時認識 → 自動ペースト
- [x] メニューバー常駐 UI (NSStatusBar)
- [x] 設定ウィンドウ (言語、ホットキー、無音判定、デバッグログ)
- [x] 校正機能 (YAML 置換ルール)
- [x] フロントアプリ追跡・復帰 (FrontmostAppTracker)
- [x] オーバーレイ波形アニメーション
- [x] 多言語対応 (ja/en)

### 配布基盤
- [x] Sparkle 2.9.x 統合 (SPM) — アプリ内自動更新
- [x] `scripts/build-dmg.sh` — .app バンドル → DMG → ad-hoc コード署名
- [x] `scripts/generate-appcast.sh` — EdDSA 署名付き appcast.xml 生成
- [x] `scripts/generate-sparkle-keys.sh` — Sparkle キーペア生成
- [x] `.github/workflows/release.yml` — v* タグで DMG + appcast.xml 自動アップロード

---

## 未完了 — 優先度順 🔴🔶🟡

### 🔴 リリース前必須

#### 1. GitHub Secrets 設定
GitHub リポジトリ `konyu/kikitori` に以下を登録:
1. `Settings → Secrets and variables → Actions → New repository secret`
2. 名前: `SPARKLE_PRIVATE_KEY_BASE64`
3. 値: `bash scripts/generate-sparkle-keys.sh` で出力された値

#### 2. SUPublicEDKey 設定
Info.plist に Sparkle 公開鍵を埋め込む必要がある。
`scripts/build-dmg.sh` 内の Info.plist 生成部分に現在 `${SU_PUBLIC_ED_KEY:-}` で空フォールバックあり。
CI ビルド時に環境変数 `SU_PUBLIC_ED_KEY` を設定するか、build-dmg.sh にハードコードする。

**対応方法 A**: `.github/workflows/release.yml` に追加:
```yaml
env:
  SU_PUBLIC_ED_KEY: ${{ secrets.SU_PUBLIC_ED_KEY }}
```

**対応方法 B**: `scripts/build-dmg.sh` の SUPublicEDKey 値を直接記述 (公開鍵はコミット可).

#### 3. Info.plist の CFBundleVersion と CFBundleShortVersionString を分離
現在どちらも `$VERSION`。Sparkle は `CFBundleVersion` (整数推奨) と `CFBundleShortVersionString` (セマンティックバージョン) を区別する。
`build-dmg.sh` で `BUILD` と `VERSION` を分けて受け取るよう修正。

#### 4. 初回リリース前の動作確認
- [ ] 実機で DMG をインストールし起動確認
- [ ] 初回「右クリック → 開く」で起動できること
- [ ] マイク権限・アクセシビリティ権限の要求が表示されること
- [ ] 音声認識が動作すること

---

### 🔶 リリース後優先

#### 5. SUFeedURL のホスト場所確定
現在 Info.plist の `SUFeedURL` は:
```
https://github.com/konyu/kikitori/releases/latest/download/appcast.xml
```
初回リリース後、実際にこの URL でアクセスできるか確認。
GitHub Releases の latest リダイレクトが `/releases/latest/download/` で機能するか検証。

#### 6. バージョニング方針
Sparkle が期待する `sparkle:version` と Info.plist の `CFBundleVersion` の関係を整理:
- 推奨: `CFBundleVersion` = 単調増加整数 (ビルド番号)
- `CFBundleShortVersionString` = セマンティックバージョン (1.0.0)
- タグは `v1.0.0` 形式

#### 7. テスト追加
- [ ] `KikitoriCore` の単体テスト
- [ ] `AudioCapture` のモックテスト
- [ ] `HotkeyManager` のテスト
- [ ] `SpeechRecognizer` の Fake を使ったテスト

#### 8. エラーハンドリング強化
- [ ] 音声認識未許可時のユーザー誘導
- [ ] アクセシビリティ権限未許可時の警告
- [ ] マイク未接続時のエラー表示
- [ ] 録音デバイスが見つからない場合のフォールバック

---

### 🟡 将来対応

#### 9. Apple Developer ID 署名 + 公証
現状 ad-hoc 署名のためユーザーは初回「右クリック→開く」が必要。
Apple Developer Program ($99/年) に加入すれば:
1. Developer ID Application 証明書で署名
2. `xcrun notarytool submit` で公証
3. `xcrun stapler staple` でチケット埋め込み
4. Gatekeeper 完全スルー → インストール体験向上

`build-dmg.sh` には `CODE_SIGN_IDENTITY` 環境変数対応を追加予定:
```bash
if [ -n "${CODE_SIGN_IDENTITY:-}" ]; then
  codesign --sign "$CODE_SIGN_IDENTITY" --deep --force --options runtime "$APP_BUNDLE"
else
  codesign --sign - --deep --force "$APP_BUNDLE"
fi
```

#### 10. `create-dmg` 対応
現在 `create-dmg` 未インストール環境では `hdiutil` フォールバック。
CI では `brew install create-dmg` を入れているが、以下を追加したい:
- 背景画像 (`assets/dmg-background.png`)
- Applications フォルダへのシンボリックリンク
- アイコン配置のカスタマイズ

#### 11. デルタアップデート
Sparkle のデルタアップデート対応:
- `generate_appcast` の `--maximum-deltas` オプション
- 差分バイナリ (小さなアップデート) の自動生成
- 要: `generate_appcast` がコード署名検証をパスする必要あり → Developer ID 署名前提

#### 12. クラッシュレポート
クラッシュレポート収集基盤 (Sparkle の `SUEnableInstallerLauncherService` は設定済み).
追加候補: PLCrashReporter または Sparkle の built-in 収集機能.

#### 13. CI 改善
- [ ] `macos-14` (M1) と `macos-15` (M4) のマトリックスビルド
- [ ] Intel Mac 向けユニバーサルバイナリビルド (`swift build --arch arm64 --arch x86_64`)
- [ ] DMG の SHA256 チェックサム自動生成・Release 添付

#### 14. リリースノート自動生成
Sparkle は DMG と同じディレクトリの `.html` / `.md` ファイルをリリースノートとして読み込む.
`generate_appcast` 非使用のため手動で `appcast.xml` に `<sparkle:releaseNotesLink>` を追加するか、
GitHub Release の本文を appcast に埋め込むスクリプトを追加.

---

## コマンドリファレンス

### キーペア生成 (初回のみ)
```bash
bash scripts/generate-sparkle-keys.sh
```

### ローカルビルド
```bash
# 署名なし (開発用)
VERSION=1.0.0 bash scripts/build-dmg.sh

# 署名付き (リリース用)
export SU_PUBLIC_ED_KEY='<公開鍵>'
export SPARKLE_PRIVATE_KEY_BASE64='<秘密鍵base64>'
VERSION=1.0.0 bash scripts/build-dmg.sh
```

### リリース手順
```bash
git tag v1.0.0
git push origin v1.0.0
# → GitHub Actions が DMG + appcast.xml を自動生成・アップロード
```

### テスト
```bash
swift test
```

---

## ファイル構成 (配布関連)

```
.
├── Package.swift                         # Sparkle 依存追加済み
├── Package.resolved                      # ロックファイル (コミット済み)
├── Sources/Kikitori/AppDelegate.swift    # Sparkle updater 統合済み
├── Sources/KikitoriCore/I18n.swift       # 更新メニュー項目追加済み
├── scripts/
│   ├── build-dmg.sh                      # ビルド + DMG + 署名 + appcast
│   ├── generate-appcast.sh               # Sparkle appcast.xml 手動生成
│   └── generate-sparkle-keys.sh          # Ed25519 キーペア生成
├── .github/workflows/release.yml         # CI: v* タグでリリース自動化
├── .config/sparkle/public.pem            # 公開鍵 (コミットOK)
├── .config/sparkle/private.pem           # 秘密鍵 (gitignore / 絶対非公開)
└── .gitignore                            # private.pem, Kikitori.app, dist/ 除外
```
