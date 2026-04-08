#!/bin/bash
set -e
BIN_DIR="$HOME/bin"
SRC_DIR="$HOME/immudb_src"

sudo dnf -y install git make gcc gcc-c++ cmake clang golang
if [ ! -d "$SRC_DIR" ]; then
  git clone --depth=1 --branch v1.10.0 https://github.com/codenotary/immudb.git "$SRC_DIR"
fi
cd "$SRC_DIR"
make immudb immuclient immuadmin
cp immudb immuclient immuadmin "$BIN_DIR/"
echo "[*] immudb binaries deployed to $BIN_DIR"
