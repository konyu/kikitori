# Silence RMS Filter

録音データの RMS（二乗平均平方根）値が閾値未満の場合、無音と判定し認識結果を破棄する。

## 要件
- `silenceRmsThreshold` 設定値（デフォルト 0.0001）
- 全フレームの RMS を計算
- RMS < 閾値なら空文字を返す
