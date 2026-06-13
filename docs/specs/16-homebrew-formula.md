# Homebrew Formula

Homebrew で配布するための Formula。

## 要件
- 別リポジトリ `konyu/homebrew-kikitori` で管理
- `brew install konyu/homebrew-kikitori/kikitori` でインストール可能
- `swift build -c release` でビルドしたバイナリを配布
- bottle 対応（GitHub Actions で自動ビルド）
