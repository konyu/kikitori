# Min Duration Filter

録音時間が最低録音時間（デフォルト 500ms）未満の場合、認識結果を破棄する。

## 要件
- `minDurationMs` 設定値（デフォルト 500）
- `totalFrameCount < minFrames` なら空文字を返す
- 設定ファイルで変更可能
