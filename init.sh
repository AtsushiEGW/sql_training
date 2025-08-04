#~/bin/bash
#set -e

echo "=== STARTING ==="

echo ">>> uv 仮想環境の作成"
uv lock --upgrade
uv sync
source .venv/bin/activate
uv add -r requirements.txt

echo ">>> データの準備"
uv run python setup.py

echo "=== 初期化完了 ==="
