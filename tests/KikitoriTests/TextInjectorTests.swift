import Testing
import KikitoriCore

@Test func textInjectorInit() {
    let i = TextInjector()
    // No crash on empty text
    i.inject("")
}
