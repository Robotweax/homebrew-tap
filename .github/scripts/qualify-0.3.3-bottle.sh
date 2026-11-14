#!/bin/bash
set -euo pipefail

# Release-specific native acceptance for the bottle created by test-bot.
export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 HOMEBREW_NO_AUTOREMOVE=1
test "$(uname -m)" = arm64
workdir="$(mktemp -d "$RUNNER_TEMP/srt-bottle-qualification.XXXXXX")"
bottle="$PWD/robotweax-srt--0.3.3.arm64_sequoia.bottle.tar.gz"
recipe="$(brew --repository robotweax/tap)/Formula/robotweax-srt.rb"
cp "$recipe" "$workdir/new-formula.rb"
trap 'cp "$workdir/new-formula.rb" "$recipe"' EXIT
test -f "$bottle"

curl --fail --location --retry 3 \
  https://github.com/Robotweax/srt/archive/f5948a4b059aa1c8e7aa5e932053f92ff37eb6ff.tar.gz \
  -o "$workdir/source.tar.gz"
printf '%s  %s\n' ccc2c409790f0d72bedbc7f87ebeb429fe723716af3b30bdd87f52fbc3d79ec7 "$workdir/source.tar.gz" | shasum -a 256 --check
mkdir "$workdir/source"
tar -xzf "$workdir/source.tar.gz" -C "$workdir/source" --strip-components=1
brew install cmake pkgconf

if brew list --formula robotweax-srt >/dev/null 2>&1; then
  brew uninstall --force --ignore-dependencies robotweax-srt
fi
if brew list --formula srt >/dev/null 2>&1; then
  brew uninstall --force --ignore-dependencies srt
fi

# Install the real published 0.3.1 bottle under its historical formula.
curl --fail --location --retry 3 \
  https://raw.githubusercontent.com/Robotweax/homebrew-tap/85da09814cbede71546db240866aee1bef871c41/Formula/robotweax-srt.rb \
  -o "$recipe"
curl --fail --location --retry 3 \
  https://github.com/Robotweax/homebrew-tap/releases/download/robotweax-srt-0.3.1/robotweax-srt-0.3.1.arm64_sequoia.bottle.tar.gz \
  -o "$workdir/robotweax-srt--0.3.1.arm64_sequoia.bottle.tar.gz"
printf '%s  %s\n' cda530ad9bf5b936b310f5917ee181d855825bed3981468234910d37c0d5b527 "$workdir/robotweax-srt--0.3.1.arm64_sequoia.bottle.tar.gz" | shasum -a 256 --check
(cd "$workdir" && HOMEBREW_DEVELOPER=1 brew install ./robotweax-srt--0.3.1.arm64_sequoia.bottle.tar.gz)

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
test "$(pkg-config --modversion robotweax-srt)" = 0.3.1
# pkg-config emits compiler argument words, intentionally split here.
# shellcheck disable=SC2046
cc "$workdir/consumer.c" -o "$workdir/consumer-0.3.1" $(pkg-config --cflags --libs robotweax-srt)
"$workdir/consumer-0.3.1"
otool -L "$workdir/consumer-0.3.1" | tee "$workdir/old-linkage.txt"
grep -F "$(brew --prefix)/opt/robotweax-srt/lib/librobotweax-srt.0.3.dylib" "$workdir/old-linkage.txt"
shasum -a 256 "$workdir/consumer-0.3.1" > "$workdir/old-consumer.sha256"

# Install the new local bottle through Homebrew's outdated-package upgrade path.
cp "$workdir/new-formula.rb" "$recipe"
# Homebrew 7 permits local bottle paths in developer/test mode.
HOMEBREW_DEVELOPER=1 brew install ./robotweax-srt--0.3.3.arm64_sequoia.bottle.tar.gz
export PKG_CONFIG_PATH="$(brew --prefix robotweax-srt)/lib/pkgconfig:$(brew --prefix openssl@3)/lib/pkgconfig"
test "$(pkg-config --modversion robotweax-srt)" = 0.3.3
# ABI line 0.3 preserves the already-linked C consumer without rebuilding it.
shasum -a 256 --check "$workdir/old-consumer.sha256"
"$workdir/consumer-0.3.1"
# shellcheck disable=SC2046
cc "$workdir/consumer.c" -o "$workdir/consumer-0.3.3" $(pkg-config --cflags --libs robotweax-srt)
"$workdir/consumer-0.3.3"
otool -L "$workdir/consumer-0.3.3" | tee "$workdir/new-linkage.txt"
grep -F 'librobotweax-srt.0.3.dylib' "$workdir/new-linkage.txt"
! grep -F 'librobotweax-srt.0.2.dylib' "$workdir/new-linkage.txt"
brew test robotweax/tap/robotweax-srt
brew audit --strict robotweax/tap/robotweax-srt
brew linkage --test --strict robotweax/tap/robotweax-srt

prefix="$(brew --prefix robotweax-srt)"
library="$prefix/lib/librobotweax-srt.0.3.3.dylib"
otool -D "$library" | tee "$workdir/install-name.txt"
otool -L "$library" | tee "$workdir/dependencies.txt"
grep -F "$(brew --prefix)/opt/robotweax-srt/lib/librobotweax-srt.0.3.dylib" "$workdir/install-name.txt"
grep -F 'libcrypto.3.dylib' "$workdir/dependencies.txt"
! grep -E '@@HOMEBREW_|/Users/runner/work/' "$workdir/dependencies.txt"
test ! -e "$prefix/include/srt/srt.h"
test ! -e "$prefix/lib/pkgconfig/srt.pc"
python3 "$workdir/source/tests/verify_shared_library_exports.py" \
  --library "$library" --manifest "$workdir/source/cmake/abi/robotweax-srt-0.3.3.txt" \
  --header "$prefix/include/robotweax-srt/robotweax_srt.h" \
  --header "$prefix/include/robotweax-srt/srt/srt.h" --tool /usr/bin/nm

# Validate the finished documentation carried by the actual bottle.
docroot="$prefix/share/doc/robotweax_srt"
python3 "$workdir/source/tests/package_consumer/check_documentation.py" "$docroot" 0.3.3
python3 - "$workdir/source" "$docroot" <<'PYDOC'
from pathlib import Path
import sys
source, installed = map(Path, sys.argv[1:])
files = list(source.glob("*.md")) + list((source / "docs").rglob("*.md")) + list((source / "examples").rglob("*.md"))
assert len(files) == 100, f"Unexpected public documentation count: {len(files)}"
for path in files:
    relative = path.relative_to(source)
    assert (installed / relative).read_bytes() == path.read_bytes(), str(relative)
print("Verified all 100 installed Markdown files against the frozen product")
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
echo "PASS: native bottle consumers, 0.3.1 upgrade without rebuilding the existing C consumer, ABI 0.3, default-prefix relocation, coexistence and removal"
