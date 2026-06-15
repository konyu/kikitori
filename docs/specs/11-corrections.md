# 11 — Corrections（校正辞書）

## 目的
音声認識結果に対し、ユーザー定義の「間違い→訂正」ペアを適用し、テキスト品質を向上させる。

## Python 版参照
`kikitori/corrections.py`:
```python
CORRECTIONS_PATH = Path.home() / ".kikitori" / "corrections.yaml"

class Corrections:
    def load(self):    # YAML から corrections 辞書を読み込み
    def correct(self, text: str) -> str:  # 置換適用
    def save_items(self, items: dict[str, str]):  # 保存
```

### 校正アルゴリズム（最重要）
```python
def correct(self, text: str) -> str:
    sorted_items = sorted(self._items.items(), key=lambda x: len(x[0]), reverse=True)
    result = []
    i = 0
    while i < len(text):
        matched = False
        for wrong, right in sorted_items:
            end = i + len(wrong)
            if end <= len(text) and text[i:end].lower() == wrong.lower():
                result.append(right)
                i = end
                matched = True
                break
        if not matched:
            result.append(text[i])
            i += 1
    return "".join(result)
```

### アルゴリズムの特徴
1. **長いキー優先**: ソートで `use effect` が `use` より先にマッチ
2. **ケースインセンシティブ**: `Use Effect` も `use effect` もマッチ
3. **非再帰置換**: 一度置換した部分は再検査しない（連鎖置換防止）
4. **文字単位走査**: マッチしなければ1文字進む

### YAML フォーマット
```yaml
corrections:
  use effect: useEffect
  use state: useState
  use callback: useCallback
```

### GUI（`corrections_dialog.py`）
- QTableWidget（間違い | 訂正）2列
- 追加: 間違い/訂正を入力するサブダイアログ
- 編集/削除
- 上書き確認ダイアログ
- ファイル保存

## Swift 実装仕様

### ファイル
```
~/.kikitori/corrections.yaml
```

### Corrections クラス
```swift
public final class Corrections: Sendable {
    public private(set) var pairs: [(wrong: String, right: String)] = []
    
    public init(path: URL? = nil)
    public func load()
    public func apply(to text: String) -> String  // 校正適用
    public func save()
}
```

### apply(to:) 実装（Python 版と同様）
```swift
public func apply(to text: String) -> String {
    guard !pairs.isEmpty, !text.isEmpty else { return text }
    
    // 長い wrong から順にソート
    let sorted = pairs.sorted { $0.wrong.count > $1.wrong.count }
    
    var result = ""
    var i = text.startIndex
    while i < text.endIndex {
        var matched = false
        for (wrong, right) in sorted {
            let end = text.index(i, offsetBy: wrong.count, limitedBy: text.endIndex)
            if let end, text[i..<end].lowercased() == wrong.lowercased() {
                result += right
                i = end
                matched = true
                break
            }
        }
        if !matched {
            result.append(text[i])
            i = text.index(after: i)
        }
    }
    return result
}
```

### YAML パース
- 自前の単純なキー・値パーサー（外部依存不要）
- フォーマット: `"wrong": "right"` （1行1ペア）
- `corrections:` キーがあればその中身を、なければルートを辞書として解釈

### 呼び出しタイミング
`stopRecording()` 内、`inject()` の直前:
```swift
var finalText = text
if !finalText.isEmpty {
    finalText = corrections.apply(to: finalText)
    textInjector.inject(finalText)
}
```

### 単体テスト
- 空文字でそのまま
- 単純置換
- 長いキー優先
- ケースインセンシティブ
- 非再帰置換（置換後の文字列が再マッチしない）
