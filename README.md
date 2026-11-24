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

This formula targets the immutable 0.3.5 product source commit
[`3415d7c`](https://github.com/Robotweax/srt/commit/3415d7c155d393755c8e49f88db4e68789fdf1b6),
the same product used by [published SRT 0.3.5](https://github.com/Robotweax/srt/releases/tag/v0.3.5).
See the [canonical formula](https://github.com/Robotweax/srt/blob/v0.3.5/packaging/homebrew/robotweax-srt.rb)
and [source manifest](https://github.com/Robotweax/srt/blob/v0.3.5/packaging/source-0.3.5.json).

Version 0.3.5 keeps shared-library ABI line 0.3, all 86 public C exports
and the compatible SRT API version 1.5.7. Applications moving from ABI line
0.2 must rebuild.

## 0.3.5 bottle publication

The [Apple Silicon macOS 15 bottle](https://github.com/Robotweax/homebrew-tap/releases/tag/robotweax-srt-0.3.5)
(`arm64_sequoia`) was published on 24 November 2026.
[Native qualification](https://github.com/Robotweax/homebrew-tap/actions/runs/45340361072)
passed on its first attempt at head
[`d7a8127`](https://github.com/Robotweax/homebrew-tap/commit/d7a81277139736aeca2c2bbb85da3d795912b656).
It upgraded from the checksum-verified published 0.3.4 bottle and ran the
same C executable against 0.3.5 without rebuilding it. All 86 exports and
109 installed Markdown files matched. Installed C/C++ consumers, default-prefix
relocation, coexistence with Haivision SRT and removal also passed.

The public download matches the [qualified bottle artifact](https://github.com/Robotweax/homebrew-tap/actions/runs/45340361072/artifacts/14895972609)
with SHA-256 `33824f8702ec667745a5c4322f99dc71447ccc4da2ebfe15bce6a3e27a194c7f`.
Its signed provenance verified against the tap's
[`brew pr-pull` publication run](https://github.com/Robotweax/homebrew-tap/actions/runs/45341293566/attempts/1).
The formula with the workflow-generated bottle URL and checksum landed in
[PR 16](https://github.com/Robotweax/homebrew-tap/pull/16) at merge commit
[`0060f84`](https://github.com/Robotweax/homebrew-tap/commit/0060f8445ba2e0ee3ff4a613bc06cef74a16d84f).

## Previous 0.3.4 bottle publication

The 0.3.4 bottle for Apple Silicon macOS 15 (`arm64_sequoia`) was published on
November 20, 2026.
[Native qualification](https://github.com/Robotweax/homebrew-tap/actions/runs/44768944062)
passed on the exact reviewed PR head
[`c8ee2e3`](https://github.com/Robotweax/homebrew-tap/commit/c8ee2e3205e796056ed90cbab1b0d307d553dfc9).
[Publication and provenance](https://github.com/Robotweax/homebrew-tap/actions/runs/44772229425)
used that head. The independently downloaded public bottle is byte-identical
to the accepted native artifact; its SHA-256 is
`585b1aaa343416eaff3aec2bb7d1aac06d0280e811eaa6be00936ce76b743ce4`.
Its signed provenance was verified against this tap's publication workflow and
run. The published formula contains that same bottle checksum and preserves
the reviewed canonical source recipe.

## Previous 0.3.3 bottle publication

The SRT 0.3.3 release and its Homebrew bottle for Apple Silicon macOS 15
(`arm64_sequoia`) were published on November 14, 2026.
[Native qualification](https://github.com/Robotweax/homebrew-tap/actions/runs/43596588263)
passed the published 0.3.1 upgrade, an existing C consumer without rebuilding,
85 exports, C/C++ consumers, default-prefix relocation, coexistence and removal.
All 100 finished public Markdown documents matched the frozen product byte for
byte after installation.

[Publication and provenance](https://github.com/Robotweax/homebrew-tap/actions/runs/43597906992)
used the exact reviewed PR head
[`fef71f5`](https://github.com/Robotweax/homebrew-tap/commit/fef71f53dc28edcfe9d0204ea1a27986c0eee8e5).
The independently downloaded public bottle is byte-identical to the accepted
native artifact; its SHA-256 is
`e4be4925909c71ae98f9f4cd0d226e3d7fc999c3d80f7bacabcfeedfb4ff60bc`.
Its signed provenance was verified against this tap's publication workflow and
run. The published formula contains that same bottle checksum and preserves
the reviewed canonical source recipe.

## Previous 0.3.1 bottle publication

The SRT 0.3.1 release and its Homebrew bottle for Apple Silicon macOS 15
(`arm64_sequoia`) were published on October 24, 2026.
[Native qualification](https://github.com/Robotweax/homebrew-tap/actions/runs/40092408908)
passed the published 0.3.0 upgrade, an existing C consumer without rebuilding,
85 exports, C/C++ consumers, default-prefix relocation, coexistence and removal.
All 90 finished public Markdown documents matched the frozen product byte for
byte after installation.

[Publication and provenance](https://github.com/Robotweax/homebrew-tap/actions/runs/40092976316)
used the exact reviewed PR head
[`bec3e95`](https://github.com/Robotweax/homebrew-tap/commit/bec3e9505c0fb1d61bdc87d356c2ef00f57d9c8c).
The independently downloaded public bottle is byte-identical to the accepted
native artifact; its SHA-256 is
`cda530ad9bf5b936b310f5917ee181d855825bed3981468234910d37c0d5b527`.
Its signed provenance was verified against this tap's publication workflow and
run. The published formula contains that same bottle checksum and preserves
the reviewed canonical source recipe.

## Previous 0.3.0 bottle publication

The 0.3.0 Homebrew bottle for Apple Silicon macOS 15 (`arm64_sequoia`) was
published on October 22, 2026.
[Native qualification](https://github.com/Robotweax/homebrew-tap/actions/runs/39789532751)
passed bottle installation, audit/linkage, the 0.2.8 upgrade with consumer rebuild,
ABI 0.3 and 84 exports, C/C++ consumers, default-prefix relocation, coexistence
and removal. The downloaded public bottle is byte-identical to the accepted
native artifact; its SHA-256 is
`701662d3fb99e361f437ff27abd7380427b499dbb0e262cfe05f06906aa87bbb`.
[Publication and provenance](https://github.com/Robotweax/homebrew-tap/actions/runs/39792270813)
used the exact reviewed PR head. Older bottle checksums must not be reused.

## Bottle publication

The pull-request workflow builds and tests the Apple Silicon macOS 15
(`arm64_sequoia`) bottle. After reviewing that qualification, dispatch
`Publish Homebrew bottle` on `main` with the release PR number, its full
qualified head SHA, and the successful native qualification run ID.

The workflow verifies the bottle and its embedded formula, creates signed
provenance and publishes the asset. It then opens a separate metadata PR
based on the qualified release PR. Review and merge the metadata PR using
the tap's normal rules. The workflow summary shows the PR and its merge state.
Reuse the same inputs for retries. The existing metadata branch records the
qualification run and digest, and the workflow verifies and reuses the
published asset and attestation when they already exist.

Configure the repository Actions secret `BOTTLE_PUBLICATION_PR_TOKEN` with
a fine-grained token scoped to this tap and **Pull requests: write**. It is
used only to open the metadata PR. GitHub's workflow token handles release
assets, attestations and the metadata branch.

Other bottle platforms require their own native qualification.
