// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Kikitori",
    platforms: [.macOS("26.0")],
    products: [
        .executable(name: "Kikitori", targets: ["Kikitori"])
    ],
    targets: [
        .target(name: "KikitoriCore"),
        .executableTarget(
            name: "Kikitori",
            dependencies: ["KikitoriCore"]
        ),
        .testTarget(
            name: "KikitoriTests",
            dependencies: ["KikitoriCore"]
        ),
    ]
)
