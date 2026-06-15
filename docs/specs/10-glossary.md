# 10 — Glossary（用語集）

## 目的
Whisper 音声認識の認識精度を向上させるため、専門用語を指定しプロンプトに追記する。Apple Speech Framework の `contextualStrings` に渡す。

## Python 版参照
`kikitori/glossary.py`:
```python
GLOSSARY_PATH = Path.home() / ".kikitori" / "glossary.yaml"

class Glossary:
    def load(self):  # YAML から terms リストを読み込み
    def get_terms(self) -> list[str]:  # 用語リスト返却
    def build_prompt(self, base_prompt: str) -> str:  # プロンプト追記
```

テンプレート:
```yaml
# Kikitori 用語集
# 行頭に "- " を付けて1行1用語で記述
terms:
  - MLX
  - Transformer
  - Apple Silicon
```

`kikitori/glossary_dialog.py`: PySide6 QDialog — 用語の追加/編集/削除/保存

`kikitori/app.py`:
```python
def load(self):
    from kikitori.apple_speech import SpeechAnalyzer
    terms = self._glossary_ref.get_terms()
    self._speech_analyzer = SpeechAnalyzer(
        contextual_strings=terms,  # Apple Speech に渡す
    )
```

## Swift 実装仕様

### ファイル
```
~/.kikitori/glossary.yaml
```

### Glossary クラス
```swift
public final class Glossary: Sendable {
    public private(set) var terms: [String] = []
    
    public init(path: URL? = nil)  // デフォルトパス = ~/.kikitori/glossary.yaml
    public func load()              // YAML 読み込み
    public func save()              // YAML 書き込み
}
```

### SpeechRecognizer 連携
```swift
// SpeechRecognizer.start() で glossary の内容を contextualStrings に渡す
public func start(glossaryTerms: [String] = []) async throws {
    // ...
    // SpeechTranscriber や SpeechAnalyzer の contextualStrings オプションに渡す
    // （macOS 26.0 API の対応プロパティを確認必要）
}
```

### TODO: macOS 26.0 Speech API の確認
- `SpeechTranscriber` に `contextualStrings` 相当のパラメータがあるか？
- なければ用語集は無効（将来の API 追加を待つ）
- 代替案: 認識結果に対して用語辞書による後処理置換（Corrections と統合）

### 用語集 GUI（後日）
- 一覧表示
- 用語の追加/編集/削除
- ファイル保存

### 単体テスト
- ファイル不在で空リスト
- 用語読み込み
- 保存→再読み込みで一致
