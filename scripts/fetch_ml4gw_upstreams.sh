#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <empty-destination-directory>" >&2
  exit 2
fi

destination=$1
if [[ -e "$destination" ]] && [[ -n "$(find "$destination" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
  echo "destination must be absent or empty: $destination" >&2
  exit 2
fi

mkdir -p "$destination"

bbnet_commit=9bd5147095f25fd8c6ac7cad30d78c71bcd3ece7
sagenet_commit=ab7face439b5ad47a8551d61e1a3fbdfd2d0ac55
stiffgw_commit=d6903d3f2552fc81f7de8f8765e9567766c4361e

git clone --filter=blob:none --no-checkout https://github.com/ML4GW/BBNet.git "$destination/BBNet"
git -C "$destination/BBNet" checkout --detach "$bbnet_commit"

git clone --filter=blob:none --no-checkout https://github.com/ML4GW/SageNet.git "$destination/SageNet"
git -C "$destination/SageNet" checkout --detach "$sagenet_commit"
git -C "$destination/SageNet" submodule update --init --recursive

[[ "$(git -C "$destination/BBNet" rev-parse HEAD)" == "$bbnet_commit" ]]
[[ "$(git -C "$destination/SageNet" rev-parse HEAD)" == "$sagenet_commit" ]]
[[ "$(git -C "$destination/SageNet/sagenetgw/stiffGWpy" rev-parse HEAD)" == "$stiffgw_commit" ]]

check_sha256() {
  local expected=$1
  local file=$2
  local observed
  observed=$(sha256sum "$file" | awk '{print $1}')
  if [[ "$observed" != "$expected" ]]; then
    echo "SHA-256 mismatch for $file" >&2
    echo "expected: $expected" >&2
    echo "observed: $observed" >&2
    exit 1
  fi
}

check_sha256 294d4e41e831f57c862cfaa2e4ced3f4bb467f3712b268aeed50b06ef0cc4553 \
  "$destination/BBNet/train_bbn_parthenope.py"
check_sha256 05522585f7b845b4cd8cb09afc9086f6ed29dea1476d45ac3e9f72b824d3869b \
  "$destination/BBNet/train_bbn_alterbbn.py"
check_sha256 d3f3ca4320229a6e4dcb2ebd0a84f1ef6920e21357c6a93200d1b2e4adfd016c \
  "$destination/SageNet/sagenetgw/models/best_gw_model_CosmicNet2.pth"
check_sha256 6c1066ba4b74d283f6d451346aa40a23062ad81feeec0bcbbbace1548a3ab343 \
  "$destination/SageNet/sagenetgw/models/best_gw_model_LSTM.pth"
check_sha256 19f4812cec55f60eca32df73b4a98a4b7477a0b401aadd86bf37e84ad38e6a3b \
  "$destination/SageNet/sagenetgw/models/best_gw_model_RNN.pth"
check_sha256 95d87b483472fd4a73f6de5ba85213358ed138bf75a2d26d8bd1ce4181a6d485 \
  "$destination/SageNet/sagenetgw/models/best_gw_model_Transformer.pth"
check_sha256 67a5414abe577b49a8614740cedd9106d96adfeefd95724235d40559b495c879 \
  "$destination/SageNet/src/solve_plus.data_test_5400.json"

echo "Verified ML4GW/BBNet $bbnet_commit"
echo "Verified ML4GW/SageNet $sagenet_commit"
echo "Verified YifangLuo/stiffGWpy $stiffgw_commit"
echo "Checkpoint files contain pickle metadata; validate them in an isolated environment."
