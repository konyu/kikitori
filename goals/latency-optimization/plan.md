# Plan: Kikitori レイテンシ最適化

## Context

録音終了からペースト完了までのエンドツーエンド遅延を50ms以下に短縮する。apple_speech エンジンを優先し、逐次処理のまま各段階の無駄を削る。パイプライン化はスコープ外。

## 特定した遅延源

| 箇所 | ファイル | 遅延 |
|------|----------|------|
| PortAudio 再初期化待機 | `recorder.py:_reinit_portaudio` | `sleep(0.1)` |
| アプリ切替後の待機 | `hotkey_manager.py:_transcribe_and_inject` | `sleep(0.2)` |
| クリップボード反映待機 | `injector.py:inject` | `sleep(0.1)` |
| Cmd+V キー間待機 | `injector.py:inject` | `sleep(0.05)` × 3 = 0.15s |
| **合計** | | **最大 0.55s** |

## Approach

1. 計測インフラを入れて現状の実測値を把握
2. `sleep` を段階的に削減・除去し、各ステップで実機確認
3. `injector` を改善（直接キー入力 + クリップボード待機最適化）
4. 録音開始の応答速度を改善（PortAudio 初期化の最適化）

## Files to Modify

| File | Change |
|------|--------|
| `kikitori/hotkey_manager.py` | `activate_app_by_pid` 後の `sleep(0.2)` 削減、計測ログ追加 |
| `kikitori/injector.py` | 全 sleep 削減、pynput.type() 直接入力追加、計測ログ追加 |
| `kikitori/recorder.py` | `_reinit_portaudio` の `sleep(0.1)` 削減検討 |
| `kikitori/apple_speech.py` | 認識処理の計測ログ追加 |
| `kikitori/config.py` | 計測用設定値（ベンチマークモードフラグ等）追加 |
| `tests/test_injector.py` | sleep 削減後のテスト修正・追加 |
| `tests/test_hotkey_manager.py` | 計測・最適化後のテスト追加 |

## Steps

- [ ] 1. **計測インフラ**: `kikitori/config.py` に `BENCHMARK_MODE` フラグ追加。`hotkey_manager.py` の `_transcribe_and_inject` に各段階の `time.perf_counter()` ログを仕込む。`injector.py` の `inject` にも同様に計測ログ追加。`recorder.py` の `start`/`stop` にも計測ログ追加。`apple_speech.py` の `transcribe` にも計測ログ追加。
- [ ] 2. **ペースト遅延最適化**: `injector.py` の全 `time.sleep` を除去。pynput.Controller.type() による直接キー入力を短いテキスト用に追加。`hotkey_manager.py` の `sleep(0.2)` を除去または最小化。
- [ ] 3. **録音開始応答速度**: `recorder.py` の `_reinit_portaudio` の `sleep(0.1)` を除去できるか検証。
- [ ] 4. **テスト修正**: 既存テストが sleep なしで通るよう修正。新しい injector のテスト追加。ホットキーマネージャの計測テスト追加。
- [ ] 5. **実機検証**: 手動で計測ログを確認し、50ms 目標に対する達成度を評価。

## Verification

```bash
# 全テスト実行
python -m pytest tests/ -v

# 静的チェック
python -c "from kikitori.app import App; print('import OK')"

# 計測ログ確認（BENCHMARK_MODE=True で起動しログ出力を確認）
BENCHMARK_MODE=true python main.py
```

## Risks

- sleep 全除去でクリップボード反映が間に合わない → 最小 sleep (0.01〜0.02s) を試験的に追加
- pynput.type() が IME ON 時に文字化け → 当面は閾値で制御、問題あれば Cmd+V フォールバック
- apple_speech 認識速度はフレームワーク側の制約で改善の余地が少ない → 計測で確認し、問題なければ受容
