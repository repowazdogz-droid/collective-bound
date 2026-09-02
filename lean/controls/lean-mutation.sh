#!/bin/sh
# NEGATIVE CONTROL: raise the budget from 40 to 60 so the witness profile [10,10,10,10,10,10]
# (total 60) no longer breaches it. per_agent_cap_insufficient is decided over closed data, so the
# mutated file MUST fail to build. A development that still built would prove nothing.
set -e
HERE=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
cp -r "$HERE/CrossLayer" "$HERE/lakefile.lean" "$HERE/lean-toolchain" "$TMP/"
sed -i.bak 's/^def budget : Nat := 40/def budget : Nat := 60/' "$TMP/CrossLayer/AccumulationWitness.lean"
grep -q 'def budget : Nat := 60' "$TMP/CrossLayer/AccumulationWitness.lean" || { echo "mutation not applied"; exit 1; }
if (cd "$TMP" && lake build >/dev/null 2>&1); then echo "** control NOT caught: mutated development built **"; rm -rf "$TMP"; exit 1; fi
echo "OK  lean mutation (budget 40 -> 60): build fails as required"
rm -rf "$TMP"
