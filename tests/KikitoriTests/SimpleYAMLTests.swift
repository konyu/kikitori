import Testing
@testable import KikitoriCore

struct SimpleYAMLTests {

    @Test("キーと値のパース")
    func testParseBasic() {
        let text = """
        key1: value1
        key2: value 2
        """
        let dict = SimpleYAML.parse(text)
        #expect(dict["key1"] == "value1")
        #expect(dict["key2"] == "value 2")
    }

    @Test("クォートの除去")
    func testParseQuotes() {
        let text = """
        key1: "value1"
        key2: 'value2'
        key3: "value with space"
        """
        let dict = SimpleYAML.parse(text)
        #expect(dict["key1"] == "value1")
        #expect(dict["key2"] == "value2")
        #expect(dict["key3"] == "value with space")
    }

    @Test("コメントと空行の無視")
    func testParseCommentsAndBlankLines() {
        let text = """
        # This is a comment
        key1: value1

        # key2: value2
        key3: value3
        """
        let dict = SimpleYAML.parse(text)
        #expect(dict["key1"] == "value1")
        #expect(dict["key2"] == nil)
        #expect(dict["key3"] == "value3")
    }

    @Test("シリアライズのテスト")
    func testSerialize() {
        let dict = [
            "key1": "value1",
            "key2": "value with space",
            "key3": "value3"
        ]
        let yaml = SimpleYAML.serialize(dict)
        // serialize() sorts keys alphabetically
        let expected = """
        key1: value1
        key2: "value with space"
        key3: value3

        """
        #expect(yaml == expected)
    }

    @Test("リスト行（- ）のスキップ")
    func testSkipListLines() {
        let text = """
        key1: value1
        - item1
        - item2
        key2: value2
        """
        let dict = SimpleYAML.parse(text)
        #expect(dict["key1"] == "value1")
        #expect(dict["key2"] == "value2")
        #expect(dict.count == 2)
    }
}
