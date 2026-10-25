#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out/fire-tv-tests
"${JAVA_HOME:+$JAVA_HOME/bin/}javac" -encoding UTF-8 -d out/fire-tv-tests \
  app/src/io/freemytv/FireTvHomePolicy.java tests/FireTvHomePolicyTest.java
"${JAVA_HOME:+$JAVA_HOME/bin/}java" -cp out/fire-tv-tests io.freemytv.FireTvHomePolicyTest
