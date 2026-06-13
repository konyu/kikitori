# Max Duration AutoStop

録音時間が最大録音時間（デフォルト 60秒）を超えた場合、自動的に録音を停止する。

## 要件
- `maxDurationSec` 設定値（デフォルト 60）
- フレーム数が上限を超えたら自動的に `stopRecording()` を呼ぶ
- 設定ファイルで変更可能
