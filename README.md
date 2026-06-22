[English](README.md) | [日本語](README_jp.md)

# 🐦 Kikitori

🌐 **Website**: [https://kikitori.arpa-llc.com/](https://kikitori.arpa-llc.com/)

A speech recognition input tool for macOS. Kikitori records your voice while you hold down a hotkey, and upon release, it uses the new **Speech Framework (SpeechAnalyzer / SpeechTranscriber)** to convert the audio into text and automatically pastes it via the clipboard. It's a lightweight, fast, native macOS application.

## Features

- **Native Swift / SwiftUI Implementation**: Achieves lightweight and fast performance.
- **On-Device Speech Recognition**: Executes speech recognition entirely locally without the need for a network connection (uses the new `SpeechAnalyzer` instead of the legacy `SFSpeechRecognizer`).
- **Intuitive UI**:
  - Always accessible via the macOS menu bar.
  - Displays an "Apple Liquid Glass" style real-time waveform overlay UI (a bird icon and 12 waveform bars) near the bottom of the screen while recording.
- **Flexible Customization (GUI Settings)**: Easily change the language, recording duration limits, silence thresholds, and hotkeys from the settings window.
- **Auto-Correction**: Use the Corrections feature to automatically replace specific phrases or misrecognized technical terms.
- **Automatic Updates**: Supports automatic updates via the Sparkle framework.

## System Requirements

- **Apple Silicon Mac Required** (M1 / M2 / M3 / M4, etc.)
- **macOS 26.0** or later required

## Required Permissions

To function correctly, Kikitori requires the following three permissions. You will be prompted to grant them upon first launch.

| Permission | Settings Location | Purpose |
|------|---------|------|
| **Microphone** | Privacy & Security → Microphone | To capture audio input from the microphone. |
| **Speech Recognition** | Privacy & Security → Speech Recognition | To convert speech to text using the Speech Framework. |
| **Accessibility** | Privacy & Security → Accessibility | To monitor hotkeys (keyboard) and automatically paste text (Cmd+V emulation). |

## Installation

Download the latest `Kikitori-x.x.x.dmg` from the [Releases page](https://github.com/konyu/kikitori/releases/latest).

1. Open the downloaded DMG file.
2. Drag and drop the `Kikitori.app` into your `Applications` folder.
3. Launch `Kikitori` from the Applications folder.

> [!WARNING]
> **Regarding the "unidentified developer" warning on first launch**
> 
> If you encounter a warning stating "cannot be opened because the developer cannot be verified" or "macOS cannot verify that this app is free from malware," please grant permission using one of the following methods:
> 
> **A. Allow from System Settings**
> 1. Close the warning dialog by clicking "Done".
> 2. Open **System Settings** > **Privacy & Security**.
> 3. Click **Open Anyway** next to the message ""Kikitori" was blocked from use...".
> 
> **B. Remove the quarantine attribute via Terminal**
> ```bash
> xattr -rd com.apple.quarantine /Applications/Kikitori.app
> ```

## Usage

Kikitori is a simple tool that records audio only while you hold down a hotkey (keyboard modifier key) and automatically inputs the recognized text when you release it. Upon launch, a bird icon (🐦) will appear in the menu bar.

- **Start Recording**: **Press and hold** the configured hotkey (default is the `Fn (🌐)` key alone).
  - A transparent glass UI featuring a bird icon and 12 waveform bars will appear near the bottom of the screen. The waveform will animate in real-time according to your voice volume.
- **Stop Recording & Input Text**: **Release** the hotkey.
  - The recording will stop and speech recognition will be executed.
  - The recognized text will be automatically pasted into the application where your cursor is currently active (e.g., Notepad, Browser, Editor).

### Menu Bar Features

Clicking the bird icon in the menu bar will display the following menu. Each setting can be intuitively configured in a dedicated GUI window.

- **Settings (Cmd + ,)**
  - **General Tab**: 
    - **Recognition language**: Select the language for speech recognition (e.g., Japanese, English, etc. - 6 languages available).
    - **UI language**: Select the application's display language.
    - **Hotkey (Modifiers)**: Set the modifier key used for recording (Fn, Control, Option, Command, Shift, or a combination) using checkboxes.
  - **Filters Tab**: 
    - **Min duration**: Recordings shorter than the specified time (in milliseconds) will be ignored (prevents accidental triggers).
    - **Max duration**: Recording is forcibly stopped when it reaches the specified time (in seconds).
    - **Silence RMS**: If the recording volume falls below this threshold, it is considered "silence" and no speech recognition is performed.
    - **Debug Log**: Enables detailed log output for developers.

- **Corrections... (Cmd + e)**
  - A screen to manage replacement rules (Wrong → Right) for commonly misrecognized words.
  - **Add ( + ) / Edit ( Pencil ) / Delete ( - )**: Opens a dedicated input form to register a pair of "Wrong (e.g. use effect)" and "Right (e.g. useEffect)".
  - *Internally, these are saved in `~/.kikitori/corrections.yaml`. You can also open the file directly or reload it using the buttons in the top right corner.*

- **Check for Updates...**
  - Checks if a new version is available and automatically downloads and installs it if found.

- **Quit (Cmd + q)**
  - Exits the application.

## Troubleshooting

### Hotkey not working / Text not pasted
Check if the toggle for **Kikitori** is turned on in "System Settings → Privacy & Security → Accessibility". If it is already on, try turning it off and on again.

### Not recording / Speech recognition fails
Ensure that Kikitori has been granted permissions in both the **Microphone** and **Speech Recognition** sections under "System Settings → Privacy & Security".

## Development (Swift Version)

This project is built using Swift 6.0 and the Swift Package Manager (SPM).

### Build Instructions

```bash
# Clone the repository
git clone https://github.com/konyu/kikitori.git
cd kikitori

# Development build
swift build

# Create DMG / Release build (Requires Sparkle key configuration)
bash scripts/build-dmg.sh
```

### Project Structure

```
.
├── Package.swift            # SPM package definition
├── Sources/
│   ├── Kikitori/            # AppDelegate, SwiftUI (Settings, Overlay UI), etc.
│   └── KikitoriCore/        # Recording control, Speech API integration, Hotkey monitoring, Settings management
├── scripts/                 # Scripts for DMG creation and Sparkle key generation
```

## License

MIT License
