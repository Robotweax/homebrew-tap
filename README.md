# Robotweax Homebrew Tap

This repository is the distribution channel for Robotweax Homebrew formulae.
The canonical `robotweax-srt.rb` recipe and its installed-consumer tests are
maintained in [Robotweax/srt](https://github.com/Robotweax/srt/tree/main/packaging).
A formula change is reviewed there first, then copied here with its source
commit, checksum and qualification result preserved.

The initial Robotweax SRT 0.2.5 formula is being prepared. No installation
command is advertised until its bottle and source-install checks pass in this
tap and the formula is published.

This tap uses Homebrew's generated pull-request workflow to build and test a
macOS arm64 bottle. The separate `brew pr-pull` workflow publishes bottles only
when explicitly dispatched with a reviewed PR number and exact head SHA.
Bottles are never published by a pull-request build alone.
