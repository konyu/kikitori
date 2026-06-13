# Debug Mode

デバッグログ出力機能。

## 要件
- 設定ファイルの `debug: true` で有効化
- 録音開始/停止、認識結果、フィルタ判定、エラーをログ出力
- `NSLog` で出力（Console.app で確認可能）
- 全コンポーネントに注入可能な DebugLogger クラス
