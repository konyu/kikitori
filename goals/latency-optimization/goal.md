# Goal: Kikitori レイテンシ最適化

音声認識の録音終了から画面へのテキストペーストまでのエンドツーエンド遅延を50ms以下に短縮する。
apple_speech 音声認識エンジンを対象に、録音開始応答速度、認識処理速度、ペースト処理の全段階を最適化する。

## 要件

[facts.md](facts.md) 参照。全8件のFactが承認済み。

## 実行計画

[plan.md](plan.md) 参照。

## 完了条件

- [ ] 計測インフラ（BENCHMARK_MODE）が実装され、各段階の遅延がログ出力される
- [ ] injector の全 sleep が除去され、直接キー入力方式が追加されている
- [ ] hotkey_manager の activate_app_by_pid 後の sleep が除去または最小化されている
- [ ] recorder の PortAudio 再初期化待機が最適化されている
- [ ] 既存テスト + 新規テストが全てパスする
- [ ] 実機でエンドツーエンド遅延が50ms以下であることが確認できる
