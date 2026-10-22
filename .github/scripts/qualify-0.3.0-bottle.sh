#!/bin/bash
set -euo pipefail

# Release-specific native acceptance for the bottle created by test-bot.
export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 HOMEBREW_NO_AUTOREMOVE=1
test "$(uname -m)" = arm64
workdir="$(mktemp -d "$RUNNER_TEMP/srt-bottle-qualification.XXXXXX")"
bottle="$PWD/robotweax-srt--0.3.0.arm64_sequoia.bottle.tar.gz"
recipe="$(brew --repository robotweax/tap)/Formula/robotweax-srt.rb"
cp "$recipe" "$workdir/new-formula.rb"
trap 'cp "$workdir/new-formula.rb" "$recipe"' EXIT
test -f "$bottle"

curl --fail --location --retry 3 \
  https://github.com/Robotweax/srt/archive/607d0034b7977f1e5003c98c42cc934bbdf9d431.tar.gz \
  -o "$workdir/source.tar.gz"
printf '%s  %s\n' 6c6d19458838248a6c95153e8907334e6c16826c041d4e204f57b73a1750cb5c "$workdir/source.tar.gz" | shasum -a 256 --check
mkdir "$workdir/source"
tar -xzf "$workdir/source.tar.gz" -C "$workdir/source" --strip-components=1
brew install cmake pkgconf

if brew list --formula robotweax-srt >/dev/null 2>&1; then
  brew uninstall --force --ignore-dependencies robotweax-srt
fi
if brew list --formula srt >/dev/null 2>&1; then
  brew uninstall --force --ignore-dependencies srt
fi

# Install the real published 0.2.8 bottle under its historical formula.
curl --fail --location --retry 3 \
  https://raw.githubusercontent.com/Robotweax/homebrew-tap/60d220b9737e65ab73674427d2b2af6fa79284f8/Formula/robotweax-srt.rb \
  -o "$recipe"
curl --fail --location --retry 3 \
  https://github.com/Robotweax/homebrew-tap/releases/download/robotweax-srt-0.2.8/robotweax-srt-0.2.8.arm64_sequoia.bottle.tar.gz \
  -o "$workdir/robotweax-srt--0.2.8.arm64_sequoia.bottle.tar.gz"
printf '%s  %s\n' 1058b2cf39d26f19afff857dc5b1886f29ad7909459231c27af568274a875396 "$workdir/robotweax-srt--0.2.8.arm64_sequoia.bottle.tar.gz" | shasum -a 256 --check
(cd "$workdir" && HOMEBREW_DEVELOPER=1 brew install ./robotweax-srt--0.2.8.arm64_sequoia.bottle.tar.gz)

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
test "$(pkg-config --modversion robotweax-srt)" = 0.2.8
# pkg-config emits compiler argument words, intentionally split here.
# shellcheck disable=SC2046
cc "$workdir/consumer.c" -o "$workdir/consumer-0.2" $(pkg-config --cflags --libs robotweax-srt)
"$workdir/consumer-0.2"
otool -L "$workdir/consumer-0.2" | tee "$workdir/old-linkage.txt"
grep -F 'librobotweax-srt.0.2.dylib' "$workdir/old-linkage.txt"

# Install the new local bottle through Homebrew's outdated-package upgrade path.
cp "$workdir/new-formula.rb" "$recipe"
# Homebrew 7 permits local bottle paths in developer/test mode.
HOMEBREW_DEVELOPER=1 brew install ./robotweax-srt--0.3.0.arm64_sequoia.bottle.tar.gz
export PKG_CONFIG_PATH="$(brew --prefix robotweax-srt)/lib/pkgconfig:$(brew --prefix openssl@3)/lib/pkgconfig"
test "$(pkg-config --modversion robotweax-srt)" = 0.3.0
# shellcheck disable=SC2046
cc "$workdir/consumer.c" -o "$workdir/consumer-0.3" $(pkg-config --cflags --libs robotweax-srt)
"$workdir/consumer-0.3"
otool -L "$workdir/consumer-0.3" | tee "$workdir/new-linkage.txt"
grep -F 'librobotweax-srt.0.3.dylib' "$workdir/new-linkage.txt"
! grep -F 'librobotweax-srt.0.2.dylib' "$workdir/new-linkage.txt"
brew test robotweax/tap/robotweax-srt
brew audit --strict robotweax/tap/robotweax-srt
brew linkage --test --strict robotweax/tap/robotweax-srt

prefix="$(brew --prefix robotweax-srt)"
library="$prefix/lib/librobotweax-srt.0.3.0.dylib"
otool -D "$library" | tee "$workdir/install-name.txt"
otool -L "$library" | tee "$workdir/dependencies.txt"
grep -F "$(brew --prefix)/opt/robotweax-srt/lib/librobotweax-srt.0.3.dylib" "$workdir/install-name.txt"
grep -F 'libcrypto.3.dylib' "$workdir/dependencies.txt"
! grep -E '@@HOMEBREW_|/Users/runner/work/' "$workdir/dependencies.txt"
test ! -e "$prefix/include/srt/srt.h"
test ! -e "$prefix/lib/pkgconfig/srt.pc"
python3 "$workdir/source/tests/verify_shared_library_exports.py" \
  --library "$library" --manifest "$workdir/source/cmake/abi/robotweax-srt-0.3.0.txt" \
  --header "$prefix/include/robotweax-srt/robotweax_srt.h" \
  --header "$prefix/include/robotweax-srt/srt/srt.h" --tool /usr/bin/nm

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
echo "PASS: native bottle consumers, 0.2.8 upgrade/rebuild, ABI 0.3, default-prefix relocation, coexistence and removal"
