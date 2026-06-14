// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Kikitori",
    platforms: [.macOS("26.0")],
    products: [
        .executable(name: "Kikitori", targets: ["Kikitori"])
    ],
    dependencies: [
        .package(url: "https://github.com/sparkle-project/Sparkle", from: "2.9.0"),
    ],
    targets: [
        .target(name: "KikitoriCore"),
        .executableTarget(
            name: "Kikitori",
            dependencies: ["KikitoriCore", .product(name: "Sparkle", package: "Sparkle")],
            resources: [.process("Resources")]
        ),
        .testTarget(
            name: "KikitoriTests",
            dependencies: ["KikitoriCore"]
        ),
    ]
)
