# Kikitori 仕様書一覧

## 実装予定

| # | 仕様 | 説明 |
|---|------|------|
| 02 | Frontmost App Tracker | 録音前に最前面アプリを記憶し、ペースト後に復元 |
| 04 | Min Duration Filter | 最低録音時間未満の認識結果を破棄 |
| 05 | Max Duration AutoStop | 最大録音時間を超えたら自動停止 |
| 06 | Silence RMS Filter | RMS 値による無音判定フィルタ |
| 07 | Custom Hotkey | ホットキーのカスタマイズ（Option 以外） |
| 08 | Settings File | YAML 設定ファイルの読み書き |
| 09 | Settings GUI | 設定画面 UI |
| 10 | Glossary | 用語集によるテキスト置換 |
| 11 | Corrections | 認識結果の後処理・校正 |
| 12 | i18n | 日本語/英語 UI 切り替え |
| 13 | Waveform Overlay | 録音中の波形オーバーレイ表示 |
| 15 | Debug Mode | デバッグログ出力 |
| 16 | Homebrew Formula | Homebrew 配布用 Formula |

> #01, #03, #14 は欠番（未定義または却下）

## コアパイプライン（実装済み）

- Option キー押下で録音開始
- Speech Framework で音声認識
- Option 解放で認識結果を貼り付け
