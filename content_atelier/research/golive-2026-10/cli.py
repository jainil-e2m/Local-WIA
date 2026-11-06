"""storage_cli as a script, so remote.py can run it against production over a TCP proxy (N4; not product code).

Usage (from backend/, with production's variables loaded): python -I ../research/packs-2026-10/np5/remote.py ../research/golive-2026-10/cli.py <storage_cli arguments>
"""
import sys

from backend_pipeline.storage_cli import main

sys.exit(main(sys.argv[1:]))
