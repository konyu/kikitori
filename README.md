# 🎤 Kikitori

macOS 向け音声認識入力ツール。ホットキー押下中にマイク入力を録音し、解放時に Apple Speech Framework（オンデバイス）を利用して音声をテキストに変換、クリップボード経由で自動ペーストする、軽量・高速なネイティブ macOS アプリです。

## 特徴

- **Swift / SwiftUI によるネイティブ実装**: 従来の Python 版から移行し、より軽量で高速な動作を実現。
- **オンデバイス音声認識**: macOS 14 搭載の Apple Speech Framework (`SFSpeechRecognizer`) を利用し、ネットワーク不要で完全にローカルで音声認識。
- **直感的な UI**:
  - メニューバー常駐でいつでもアクセス可能。
  - 録音中は画面中央下にリアルタイムに波形が動くオーバーレイ UI を表示。
- **柔軟なカスタマイズ (GUI 設定)**: アプリ上の設定画面から、言語、録音長、無音しきい値、ホットキーなどを簡単に変更可能。
- **誤変換の自動修正**: カスタム辞書（Corrections）機能で、特定の言い回しや専門用語の誤変換を自動で置換。
- **自動アップデート**: Sparkle フレームワークによる自動アップデート機能に対応。

## 動作環境

- Apple Silicon Mac（M1/M2/M3/M4）
- macOS 14.0（Sonoma）以上 必須

## 必要な権限

Kikitori を正しく動作させるためには、以下の3つの権限が必要です。初回起動時に許可を求められます。

| 権限 | 設定場所 | 用途 |
|------|---------|------|
| **マイク** | プライバシーとセキュリティ → マイク | マイクからの音声入力 |
| **音声認識** | プライバシーとセキュリティ → 音声認識 | Apple Speech Framework による音声からテキストへの変換 |
| **アクセシビリティ** | プライバシーとセキュリティ → アクセシビリティ | ホットキー（キーボード）の監視と、自動ペースト (Cmd+V のエミュレーション) |

## インストール

[Releases ページ](https://github.com/konyu/kikitori/releases/latest) から最新の `Kikitori-x.x.x.dmg` をダウンロードしてください。

1. DMG ファイルを開きます。
2. 中にある `Kikitori.app` を `Applications` フォルダへドラッグ＆ドロップします。
3. アプリケーションフォルダから `Kikitori` を起動してください。

> [!WARNING]
> **初回起動時の「開発元が未確認」という警告について**
> 
> 起動時に「開発元が未確認」「マルウェアがないか検証できません」という警告が出る場合は、以下のいずれかの方法で許可してください：
> 
> **A. システム設定から許可する**
> 1. 警告ダイアログを「完了」で閉じます。
> 2. **「システム設定」** > **「プライバシーとセキュリティ」** を開きます。
> 3. 「"Kikitori" は開発元を確認できないため...」の横にある **「このまま開く」** をクリックします。
> 
> **B. ターミナルで検疫を解除する**
> ```bash
> xattr -rd com.apple.quarantine /Applications/Kikitori.app
> ```

## 使い方

アプリを起動すると、メニューバーに 🎤 アイコンが表示されます。

- **ホットキー押下中（デフォルト: 右 Option キー）**: 録音開始（画面下部に波形オーバーレイが表示されます）
- **ホットキー解放**: 録音停止 → 音声認識 → 自動的に現在のカーソル位置にテキストがペーストされます。

### メニューバーの機能

メニューバーの 🎤 アイコンをクリックすると、以下の操作が可能です。

- **設定**: 言語（日本語・英語など）、UIの言語、ホットキー、各種しきい値（ミリ秒・音量）を GUI から設定します。
- **置換辞書**: よく間違えられる単語の変換ルール（間違い → 正解）を登録できます。
- **アップデートの確認**: 新しいバージョンがあるか確認し、自動でダウンロード・インストールします。
- **終了**: アプリを終了します。

## トラブルシューティング

### ホットキーが効かない・テキストがペーストされない
「システム設定 → プライバシーとセキュリティ → アクセシビリティ」で **Kikitori** のスイッチがオンになっているか確認してください。すでにオンの場合は、一度オフにしてから再度オンにしてみてください。

### 録音されない・音声認識が失敗する
「システム設定 → プライバシーとセキュリティ」の **マイク** および **音声認識** の項目で、Kikitori に許可が与えられているか確認してください。

## 開発（Swift版）

本プロジェクトは Swift 5.10 / Swift Package Manager (SPM) ベースで構築されています。

### ビルド手順

```bash
# クローン
git clone https://github.com/konyu/kikitori.git
cd kikitori

# 開発用ビルド
swift build

# DMG / リリースビルドの作成（Sparkleの鍵設定が必要）
bash scripts/build-dmg.sh
```

### プロジェクト構成

```
.
├── Package.swift            # SPM パッケージ定義
├── Sources/
│   ├── Kikitori/            # AppDelegate, SwiftUI (設定画面, オーバーレイUI) など
│   └── KikitoriCore/        # 録音制御, Apple Speech API 連携, ホットキー監視, 設定管理
├── scripts/                 # DMG作成やSparkle用鍵生成スクリプト
└── (以下、Python版のレガシーコード群)
```

---

## 🐍 Python版（Legacy）について

以前の Python / PySide6 / `mlx-whisper` ベースのバージョンもリポジトリ内に残されています。
Apple Speech Framework ではなく、Hugging Face の Whisper モデルを使用したい場合などにご利用いただけますが、**現在は Swift 版がメインストリーム**となります。

<details>
<summary>Python版のインストールと使い方</summary>

### Homebrew でのインストール

```bash
brew tap konyu/kikitori
brew install kikitori
kikitori
```

### 手動インストール
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg
```

### 実行方法

メニューバーアプリ（推奨）:
```bash
./run.sh
```

PySide6 版オーバーレイUI:
```bash
python pyside_main.py
```

</details>

## ライセンス

MIT License
