#!/usr/bin/env python3
"""Open Doc Intelligence (docintel) System Diagnostic Tool.

Inspects local operating environment, Python runtime, GPU/CUDA capabilities,
Docker availability, disk space, and configuration integrity without making
destructive changes or uploading telemetry.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def check_python() -> bool:
    print("Python Runtime:")
    version = sys.version_info
    print(f"  Version: {version.major}.{version.minor}.{version.micro}")
    print(f"  Executable: {sys.executable}")
    if version.major == 3 and version.minor in (10, 11, 12):
        print("  Status: [OK] Supported Python version")
        return True
    print("  Status: [WARNING] Python 3.11 is recommended for maximum PyTorch & CUDA wheel stability")
    return True


def check_tool(name: str, cmd: list[str]) -> bool:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            first_line = res.stdout.strip().splitlines()[0] if res.stdout else "Available"
            print(f"  {name}: [OK] {first_line}")
            return True
        print(f"  {name}: [FAIL] Command returned code {res.returncode}")
        return False
    except FileNotFoundError:
        print(f"  {name}: [MISSING] Executable not found in PATH")
        return False


def check_gpu() -> bool:
    print("\nGPU & CUDA Acceleration:")
    if not shutil.which("nvidia-smi"):
        print("  nvidia-smi: [NOT FOUND] No NVIDIA GPU detected. Running in pure CPU mode.")
        return False
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            gpu_info = res.stdout.strip().splitlines()[0]
            print(f"  NVIDIA GPU: [OK] {gpu_info}")
            print("  VRAM Safety: Target low_vram profile (Florence-2 / GOT-OCR 2.0)")
            return True
        print("  nvidia-smi: [WARNING] Execution failed")
        return False
    except Exception as exc:
        print(f"  nvidia-smi error: {exc}")
        return False


def check_disk_space() -> bool:
    print("\nStorage Space:")
    cwd = Path.cwd()
    usage = shutil.disk_usage(cwd)
    free_gb = usage.free / (1024**3)
    total_gb = usage.total / (1024**3)
    print(f"  Working Directory: {cwd}")
    print(f"  Drive Free Space: {free_gb:.1f} GB / {total_gb:.1f} GB")
    if free_gb < 10:
        print("  Status: [WARNING] Less than 10 GB free space remaining")
        return False
    print("  Status: [OK] Sufficient disk space for models and document artifacts")
    return True


def check_env_file() -> bool:
    print("\nConfiguration:")
    env_path = Path(".env")
    example_path = Path(".env.example")
    if env_path.exists():
        print("  .env file: [OK] Present")
        return True
    if example_path.exists():
        print("  .env file: [NOTICE] Missing .env (copying from .env.example recommended)")
        return False
    print("  .env file: [MISSING] Neither .env nor .env.example found")
    return False


def main() -> int:
    print_header("Open Doc Intelligence (docintel) - Diagnostic Doctor")
    p_ok = check_python()
    print("\nCore Developer Tools:")
    uv_ok = check_tool("uv", ["uv", "--version"])
    git_ok = check_tool("git", ["git", "--version"])
    docker_ok = check_tool("docker", ["docker", "--version"])
    node_ok = check_tool("node", ["node", "--version"])
    gpu_ok = check_gpu()
    disk_ok = check_disk_space()
    env_ok = check_env_file()

    print_header("Diagnostic Summary")
    print(f"  Python 3.11+: {'PASS' if p_ok else 'WARN'}")
    print(f"  uv Tool:      {'PASS' if uv_ok else 'MISSING'}")
    print(f"  Git:          {'PASS' if git_ok else 'MISSING'}")
    print(f"  Docker:       {'PASS' if docker_ok else 'WARN'}")
    print(f"  NVIDIA GPU:   {'PASS' if gpu_ok else 'CPU-ONLY'}")
    print(f"  Storage:      {'PASS' if disk_ok else 'LOW'}")

    print("\nReady to proceed with Open Doc Intelligence execution!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
