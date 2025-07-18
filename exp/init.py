#!/usr/bin/env python3
"""
Author: Li Yuanming
Email: yuanmingleee@gmail.com
Date: Jul 11, 2025

grab_mle_experiments.py
-----------------------
Download openai/mle-bench's `experiments/` directory (with Git-LFS files) and
copy it into the installed `mlebench` package’s folder inside site-packages.

Run:  python grab_mle_experiments.py
"""

import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path

from git import Repo
from typing import TYPE_CHECKING

from exp.utils import get_logger

if TYPE_CHECKING:
    from typing import Optional, List

logger = get_logger(__name__)
REPO_URL = "https://github.com/openai/mle-bench.git"
_LFS_SIGNATURE = "https://git-lfs.github.com/spec/v1"
BRANCH = "main"
EXP_DIR = "experiments"
LFS_SEARCH_DIR = "mlebench/competitions"


def is_init() -> bool:
    """
    Check if the mlebench package is installed and has the expected structure.
    """
    try:
        spec = importlib.util.find_spec("mlebench")
        if spec is None or not spec.origin:
            return False

        pkg_root = Path(spec.origin).parents[1]
        # Check if the experiments directory created by `init`
        mlebench_exp_dir = pkg_root / EXP_DIR
        if not (mlebench_exp_dir.exists() and mlebench_exp_dir.is_dir()):
            return False
        # Check if all git-lfs files are present
        for file_path in (pkg_root / LFS_SEARCH_DIR).rglob("*"):
            if file_path.is_file():
                try:
                    # Open and read the beginning of the file
                    with file_path.open('r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(512)  # Read first 512 bytes
                        if _LFS_SIGNATURE in content:
                            return False
                except Exception:
                    continue  # Skip unreadable files
        return True
    except ImportError:
        return False


def find_git_lfs() -> "Optional[List[str]]":
    """
    Return True if a working `git-lfs` is on PATH and responds to `git lfs version`.
    """
    git_lfs = shutil.which("git-lfs") or shutil.which("git")  # some distros ship as `git lfs …`
    if not git_lfs:
        return None

    use_git = git_lfs.lower().endswith("git") or git_lfs.lower().endswith("git.exe")
    cmd = [git_lfs, "lfs"] if use_git else [git_lfs]

    try:
        # Most installations expose `git-lfs` directly; fall back to `git lfs version`
        subprocess.run(
            cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        # Example output: `git-lfs/3.5.2 (GitHub; linux amd64; go 1.22.0)`
        return cmd
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error(
            "Git LFS is not installed or not found in PATH. "
            "Please install Git LFS and ensure it is available in your PATH.\n"
            "You can install it from https://git-lfs.github.com/ or via your package manager."
        )
    return None


def init(force=False) -> int:
    git_lfs_cmd = find_git_lfs()
    # Check if git-lfs is available
    if git_lfs_cmd is None:
        return 1

    # Check if experiments directory already exists and if it symlinks to the right place
    if is_init():
        if force:
            logger.info("Upgrading existing experiments/ directory …")
        else:
            logger.info("experiments/ directory already exists; skipping setup.")
            return 1

    # Find the mlebench package directory
    spec = importlib.util.find_spec("mlebench")
    pkg_root = Path(spec.origin).parents[1]
    dest_exp_dir = pkg_root / EXP_DIR
    dest_lfs_dir = pkg_root / LFS_SEARCH_DIR

    # Wipe any existing experiments/ copy
    if dest_exp_dir.exists():
        logger.info("Removing old experiments/ folder …")
        shutil.rmtree(dest_exp_dir)

    # Clone repo sparsely into a temp dir
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        repo_dir = tmp / "mle-bench"
        logger.info(f"Cloning {REPO_URL} → {repo_dir}")

        repo = Repo.clone_from(
            REPO_URL,
            repo_dir,
            branch=BRANCH,
            depth=1,
            no_checkout=True,
            multi_options=["--filter=blob:limit=256k"]
        )

        # Sparse-checkout just the experiments folder
        repo.git.sparse_checkout("init", "--cone")
        repo.git.sparse_checkout("set", EXP_DIR, LFS_SEARCH_DIR)
        repo.git.checkout(BRANCH)

        # Pull the large-file objects
        logger.info(f"Pulling Git LFS objects for {EXP_DIR}/, {LFS_SEARCH_DIR}/ …")
        subprocess.run(
            git_lfs_cmd + ["pull", "--include", EXP_DIR, "--include", LFS_SEARCH_DIR],
            cwd=repo_dir,
            check=True
        )

        src_exp_dir = repo_dir / EXP_DIR
        if not src_exp_dir.is_dir():
            logger.error(f"{EXP_DIR}/ folder was not found in the clone.")
            return 1

        src_lfs_dir = repo_dir / LFS_SEARCH_DIR
        if not src_lfs_dir.is_dir():
            logger.error(f"{LFS_SEARCH_DIR}/ folder was not found in the clone.")
            return 1

        # Copy into site-packages
        logger.info(f"Copying {src_exp_dir} → {dest_exp_dir}")
        shutil.copytree(src_exp_dir, dest_exp_dir)
        logger.info(f"Copying {src_lfs_dir} → {dest_lfs_dir}")
        shutil.copytree(src_lfs_dir, dest_lfs_dir, dirs_exist_ok=True)

    # Quick sanity check: make sure at least one non-pointer file exists
    some_file = next(dest_exp_dir.rglob("*"), None)
    if some_file and some_file.stat().st_size > 150:  # LFS pointers are ~130 B
        logger.info(f"Done! Sample file copied: {some_file.relative_to(dest_exp_dir.parent)}")
        return 0
    else:
        logger.warning("files might still be Git-LFS pointers; check your git-lfs setup.")
        return 1
