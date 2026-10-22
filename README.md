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

This formula targets the immutable 0.3.0 product source commit
[`607d003`](https://github.com/Robotweax/srt/commit/607d0034b7977f1e5003c98c42cc934bbdf9d431).
Its canonical source and qualification evidence live in
[Robotweax/srt/packaging](https://github.com/Robotweax/srt/blob/0b4aa7f3daa1591f59a17432c7041102960bcf7b/packaging/qualification-0.3.0.md).
Future formula changes are reviewed there first and then copied here. The tap
holds distribution metadata and bottles; it does not fork the protocol source.

Version 0.3.0 uses shared-library ABI line 0.3; rebuild applications and
dependencies linked against ABI line 0.2. The compatible SRT API version remains
1.5.7. Existing C export names do not establish binary compatibility with 0.2.

The SRT release was published on October 14, 2026. The 0.3.0 Homebrew bottle
for Apple Silicon macOS 15 (`arm64_sequoia`) was published on October 22, 2026.
[Native qualification](https://github.com/Robotweax/homebrew-tap/actions/runs/39789532751)
passed bottle installation, audit/linkage, the 0.2.8 upgrade with consumer rebuild,
ABI 0.3 and 84 exports, C/C++ consumers, default-prefix relocation, coexistence
and removal. The downloaded public bottle is byte-identical to the accepted
native artifact; its SHA-256 is
`701662d3fb99e361f437ff27abd7380427b499dbb0e262cfe05f06906aa87bbb`.
[Publication and provenance](https://github.com/Robotweax/homebrew-tap/actions/runs/39792270813)
used the exact reviewed PR head. Older bottle checksums must not be reused.

The pull-request workflow builds and tests a macOS arm64 bottle. A maintainer
reviews the formula, bottle checksums and successful tests before manually
running `brew pr-pull` with the exact PR head SHA. Intel macOS and Linux Homebrew
bottles, additional macOS tags and arbitrary installation prefixes are not
currently qualified. PR #8 for 0.2.9 was closed as superseded by #10; its evidence
remains historical. Future bottle updates require their own exact-head native
qualification and downloaded artifact/hash review.
