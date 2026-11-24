#!/bin/bash
set -euo pipefail

# Release-specific native acceptance for the bottle created by test-bot.
export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 HOMEBREW_NO_AUTOREMOVE=1
test "$(uname -m)" = arm64
workdir="$(mktemp -d "$RUNNER_TEMP/srt-bottle-qualification.XXXXXX")"
bottle="$PWD/robotweax-srt--0.3.5.arm64_sequoia.bottle.tar.gz"
recipe="$(brew --repository robotweax/tap)/Formula/robotweax-srt.rb"
cp "$recipe" "$workdir/new-formula.rb"
trap 'cp "$workdir/new-formula.rb" "$recipe"' EXIT
test -f "$bottle"

curl --fail --location --retry 3 \
  https://github.com/Robotweax/srt/archive/3415d7c155d393755c8e49f88db4e68789fdf1b6.tar.gz \
  -o "$workdir/source.tar.gz"
printf '%s  %s\n' d0874116bd14f27eaf5f9a3fba523e3f32d6f579896009b540de1c08e95a9336 "$workdir/source.tar.gz" | shasum -a 256 --check
mkdir "$workdir/source"
tar -xzf "$workdir/source.tar.gz" -C "$workdir/source" --strip-components=1
# The frozen product's package consumer still requests 0.3.4; the release
# commit changes only that version line. Use the released file, by checksum.
curl --fail --location --retry 3 \
  https://raw.githubusercontent.com/Robotweax/srt/fd9dac31675b12022579d28a748abb0839004cde/packaging/tests/CMakeLists.txt \
  -o "$workdir/source/packaging/tests/CMakeLists.txt"
printf '%s  %s\n' 38cbc4ea0f28b4c1dfda23d7f2d2367bf2a6351fb7b6b63a19cec7f5af2add0b "$workdir/source/packaging/tests/CMakeLists.txt" | shasum -a 256 --check
brew install cmake pkgconf

if brew list --formula robotweax-srt >/dev/null 2>&1; then
  brew uninstall --force --ignore-dependencies robotweax-srt
fi
if brew list --formula srt >/dev/null 2>&1; then
  brew uninstall --force --ignore-dependencies srt
fi

# Install the real published 0.3.4 bottle under its historical formula.
curl --fail --location --retry 3 \
  https://raw.githubusercontent.com/Robotweax/homebrew-tap/d4e49112ebcfc8bd1dd6ed06bf2d65be66a7203d/Formula/robotweax-srt.rb \
  -o "$recipe"
printf '%s  %s\n' 1a2ce02bb11d288b7beb7a6e1702e1d5bfa4555123d0b9870df93f4e9e502928 "$recipe" | shasum -a 256 --check
curl --fail --location --retry 3 \
  https://github.com/Robotweax/homebrew-tap/releases/download/robotweax-srt-0.3.4/robotweax-srt-0.3.4.arm64_sequoia.bottle.tar.gz \
  -o "$workdir/robotweax-srt--0.3.4.arm64_sequoia.bottle.tar.gz"
printf '%s  %s\n' 585b1aaa343416eaff3aec2bb7d1aac06d0280e811eaa6be00936ce76b743ce4 "$workdir/robotweax-srt--0.3.4.arm64_sequoia.bottle.tar.gz" | shasum -a 256 --check
(cd "$workdir" && HOMEBREW_DEVELOPER=1 brew install ./robotweax-srt--0.3.4.arm64_sequoia.bottle.tar.gz)

cat > "$workdir/consumer.c" <<'C'
#include <robotweax_srt.h>
#include <srt/srt.h>
int main(void) {
  robotweax_srt_options *options = 0;
  if (srt_getversion() != 0x010507) return 1;
  if (robotweax_srt_options_create(&options) != ROBOTWEAX_SRT_OK || !options) return 2;
  robotweax_srt_options_destroy(options);
  return 0;
}
C
export PKG_CONFIG_PATH="$(brew --prefix robotweax-srt)/lib/pkgconfig:$(brew --prefix openssl@3)/lib/pkgconfig"
test "$(pkg-config --modversion robotweax-srt)" = 0.3.4
# pkg-config emits compiler argument words, intentionally split here.
# shellcheck disable=SC2046
cc "$workdir/consumer.c" -o "$workdir/consumer-0.3.4" $(pkg-config --cflags --libs robotweax-srt)
"$workdir/consumer-0.3.4"
otool -L "$workdir/consumer-0.3.4" | tee "$workdir/old-linkage.txt"
grep -F "$(brew --prefix)/opt/robotweax-srt/lib/librobotweax-srt.0.3.dylib" "$workdir/old-linkage.txt"
shasum -a 256 "$workdir/consumer-0.3.4" > "$workdir/old-consumer.sha256"

# Install the new local bottle through Homebrew's outdated-package upgrade path.
cp "$workdir/new-formula.rb" "$recipe"
# Homebrew 7 permits local bottle paths in developer/test mode.
HOMEBREW_DEVELOPER=1 brew install "$bottle"
export PKG_CONFIG_PATH="$(brew --prefix robotweax-srt)/lib/pkgconfig:$(brew --prefix openssl@3)/lib/pkgconfig"
test "$(pkg-config --modversion robotweax-srt)" = 0.3.5
python3 - "$(brew --prefix)/opt/robotweax-srt" "$(brew --cellar robotweax-srt)/0.3.5" <<'PYKEG'
from pathlib import Path
import sys
opt, keg = map(Path, sys.argv[1:])
assert opt.resolve() == keg.resolve(strict=True), (opt, keg)
PYKEG
# ABI line 0.3 preserves the already-linked C consumer without rebuilding it.
shasum -a 256 --check "$workdir/old-consumer.sha256"
"$workdir/consumer-0.3.4"
# shellcheck disable=SC2046
cc "$workdir/consumer.c" -o "$workdir/consumer-0.3.5" $(pkg-config --cflags --libs robotweax-srt)
"$workdir/consumer-0.3.5"
otool -L "$workdir/consumer-0.3.5" | tee "$workdir/new-linkage.txt"
grep -F 'librobotweax-srt.0.3.dylib' "$workdir/new-linkage.txt"
! grep -F 'librobotweax-srt.0.2.dylib' "$workdir/new-linkage.txt"
brew test robotweax/tap/robotweax-srt
brew audit --strict robotweax/tap/robotweax-srt
brew linkage --test --strict robotweax/tap/robotweax-srt

prefix="$(brew --prefix robotweax-srt)"
library="$prefix/lib/librobotweax-srt.0.3.5.dylib"
otool -D "$library" | tee "$workdir/install-name.txt"
otool -L "$library" | tee "$workdir/dependencies.txt"
grep -F "$(brew --prefix)/opt/robotweax-srt/lib/librobotweax-srt.0.3.dylib" "$workdir/install-name.txt"
grep -F 'libcrypto.3.dylib' "$workdir/dependencies.txt"
! grep -E '@@HOMEBREW_|/Users/runner/work/' "$workdir/dependencies.txt"
test ! -e "$prefix/include/srt/srt.h"
test ! -e "$prefix/lib/pkgconfig/srt.pc"
python3 "$workdir/source/tests/verify_shared_library_exports.py" \
  --library "$library" --manifest "$workdir/source/cmake/abi/robotweax-srt-0.3.5.txt" \
  --header "$prefix/include/robotweax-srt/robotweax_srt.h" \
  --header "$prefix/include/robotweax-srt/srt/srt.h" --tool /usr/bin/nm

# Validate the finished documentation carried by the actual bottle.
docroot="$prefix/share/doc/robotweax_srt"
python3 "$workdir/source/tests/package_consumer/check_documentation.py" "$docroot" 0.3.5
python3 - "$workdir/source" "$docroot" <<'PYDOC'
from pathlib import Path
import sys
source, installed = map(Path, sys.argv[1:])
files = list(source.glob("*.md")) + list((source / "docs").rglob("*.md")) + list((source / "examples").rglob("*.md"))
assert len(files) == 109, f"Unexpected public documentation count: {len(files)}"
for path in files:
    relative = path.relative_to(source)
    assert (installed / relative).read_bytes() == path.read_bytes(), str(relative)
print("Verified all 109 installed Markdown files against the frozen product")
PYDOC

cmake -S "$workdir/source/packaging/tests" -B "$workdir/standalone" \
  -DCMAKE_BUILD_TYPE=Release -DTEST_HAIVISION=OFF \
  "-DCMAKE_PREFIX_PATH=$prefix;$(brew --prefix openssl@3)"
cmake --build "$workdir/standalone"
ctest --test-dir "$workdir/standalone" --output-on-failure

brew install srt
cmake -S "$workdir/source/packaging/tests" -B "$workdir/coexistence" \
  -DCMAKE_BUILD_TYPE=Release "-DHAIVISION_PREFIX=$(brew --prefix srt)" \
  "-DCMAKE_PREFIX_PATH=$prefix;$(brew --prefix openssl@3)"
cmake --build "$workdir/coexistence"
ctest --test-dir "$workdir/coexistence" --output-on-failure
brew uninstall --force robotweax-srt
"$workdir/coexistence/haivision"
test -n "$(pkg-config --modversion srt)"
echo "PASS: native bottle consumers, 0.3.4 upgrade without rebuilding the existing C consumer, ABI 0.3, default-prefix relocation, coexistence and removal"
