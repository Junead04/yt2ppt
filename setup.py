# -*- coding: utf-8 -*-
"""Auto-installs node_modules on Streamlit Cloud at startup."""
import os
import subprocess
import sys


def ensure_node_modules():
    """Run npm install if node_modules/pptxgenjs is missing."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    pptxgenjs_path = os.path.join(app_dir, "node_modules", "pptxgenjs")

    if not os.path.exists(pptxgenjs_path):
        print("Installing node_modules...", flush=True)
        result = subprocess.run(
            ["npm", "install", "--prefer-offline"],
            cwd=app_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"npm install failed:\n{result.stderr}", flush=True)
            sys.exit(1)
        print("node_modules installed successfully.", flush=True)
    else:
        print("node_modules already present.", flush=True)
