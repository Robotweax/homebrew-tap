# Robotweax Homebrew Tap

Install Robotweax SRT on Apple Silicon macOS:

```sh
brew install robotweax/tap/robotweax-srt
```

Homebrew may ask you to trust this specific external formula. The library uses
`robotweax-srt` names and does not replace Haivision's `srt` formula. Existing
FFmpeg, GStreamer, VLC and OBS installations are not changed by installing it.
Applications must link explicitly against `RobotweaxSRT::srt` or use
`robotweax-srt.pc`; loading both providers into one process is not qualified.

This formula targets the immutable 0.2.6 source commit
[`7ecb60e`](https://github.com/Robotweax/srt/commit/7ecb60ea8b4faca01ed86237b0cc9dc906350f6e).
Its canonical source and qualification evidence live in
[Robotweax/srt/packaging](https://github.com/Robotweax/srt/tree/main/packaging).
Future formula changes are reviewed there first and then copied here. The tap
holds distribution metadata and bottles; it does not fork the protocol source.

The pull-request workflow builds and tests a macOS arm64 bottle. A maintainer
reviews the formula, bottle checksums and successful tests before manually
running `brew pr-pull` with the exact PR head SHA. Intel macOS and Linux Homebrew
bottles are not currently qualified.
