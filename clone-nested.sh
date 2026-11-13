#!/usr/bin/env bash
# Clone the standalone repos that live inside Local-WIA (it ignores them). Run once after cloning Local-WIA.
set -e
cd "$(dirname "$0")"
clone() { if [ -d "$2/.git" ]; then echo "skip $2 (already cloned)"; else git clone -c core.longpaths=true "$@"; fi; }
clone https://github.com/kenil-e2m/WIA-Command-Center.git frontend
clone https://github.com/kenil-e2m/wia-knowledge-base.git knowledge_base/wia-knowledge-base -b mvp
