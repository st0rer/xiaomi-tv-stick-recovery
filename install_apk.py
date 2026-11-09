#!/usr/bin/env python3
"""
Xiaomi TV Stick 4K / Android TV Smart APK & APKM Installer
Author: Open Source Community
License: MIT

Smart installer supporting:
- Standard single .apk files
- APKMirror bundles (.apkm) and XAPK bundles (.xapk)
- Automatic device ABI detection (e.g. armeabi-v7a) with split filtering
- Batch installation of directories
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import List, Optional, Tuple

class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.HEADER = ""
        cls.BLUE = ""
        cls.CYAN = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.RED = ""
        cls.BOLD = ""
        cls.RESET = ""

if not sys.stdout.isatty():
    Colors.disable()

def log_info(msg: str) -> None:
    print(f"{Colors.GREEN}[INFO]{Colors.RESET} {msg}")

def log_warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")

def log_error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


class AppInstaller:
    def __init__(self, adb_bin: str, device_serial: Optional[str] = None, dry_run: bool = False, verbose: bool = False):
        self.adb_bin = adb_bin
        self.device_serial = device_serial
        self.dry_run = dry_run
        self.verbose = verbose
        self._device_abi: Optional[str] = None

    def run_adb(self, args: List[str]) -> Tuple[int, str, str]:
        cmd = [self.adb_bin]
        if self.device_serial:
            cmd += ["-s", self.device_serial]
        cmd += args

        if self.verbose:
            print(f"{Colors.BLUE}[ADB]{Colors.RESET} {' '.join(cmd)}")
        if self.dry_run:
            return 0, "[DRY-RUN] Success", ""

        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out = p.stdout.strip()
        err = p.stderr.strip()
        combined = (out + "\n" + err).strip()
        if self.verbose and combined:
            for line in combined.splitlines():
                print(f"  {line}")
        return p.returncode, out, err

    def get_device_abi(self) -> str:
        if self._device_abi:
            return self._device_abi
        code, out, err = self.run_adb(["shell", "getprop", "ro.product.cpu.abi"])
        abi = out.strip() or "armeabi-v7a"
        self._device_abi = abi
        log_info(f"Target device architecture: {Colors.BOLD}{abi}{Colors.RESET}")
        return abi

    def install_single_apk(self, apk_path: str, grant_permissions: bool = False) -> bool:
        log_info(f"Installing APK: {os.path.basename(apk_path)}...")
        args = ["install", "-r", "-d"]
        if grant_permissions:
            args.append("-g")
        args.append(apk_path)

        code, out, err = self.run_adb(args)
        combined = out + "\n" + err
        if "Success" in combined:
            log_info(f"{Colors.GREEN}Successfully installed {os.path.basename(apk_path)}{Colors.RESET}")
            return True
        else:
            log_error(f"Failed to install {os.path.basename(apk_path)}:\n{combined}")
            return False

    def install_bundle(self, bundle_path: str, grant_permissions: bool = False) -> bool:
        log_info(f"Unpacking and processing bundle: {os.path.basename(bundle_path)}...")
        target_abi = self.get_device_abi()

        with tempfile.TemporaryDirectory(prefix="stick_bundle_") as tmp_dir:
            try:
                with zipfile.ZipFile(bundle_path, "r") as z:
                    z.extractall(tmp_dir)
            except zipfile.BadZipFile:
                log_error(f"File {bundle_path} is not a valid zip/bundle archive.")
                return False

            apk_files = [f for f in os.listdir(tmp_dir) if f.endswith(".apk")]
            if not apk_files:
                log_error("No APK files found inside bundle.")
                return False

            base_apk = None
            split_apks = []

            # Filter appropriate splits
            for f in sorted(apk_files):
                full_path = os.path.join(tmp_dir, f)
                if f == "base.apk":
                    base_apk = full_path
                    continue

                # Architecture filter
                if "arm64" in f and "arm64" not in target_abi:
                    if self.verbose:
                        print(f"  Filtering out incompatible split: {f}")
                    continue
                if "armeabi" in f and "v7a" in f and "v7a" not in target_abi and "arm64" not in target_abi:
                    if self.verbose:
                        print(f"  Filtering out incompatible split: {f}")
                    continue
                if "x86" in f and "x86" not in target_abi:
                    continue

                split_apks.append(full_path)

            if not base_apk and apk_files:
                # Some bundles name base differently, find the largest APK
                largest = max(apk_files, key=lambda x: os.path.getsize(os.path.join(tmp_dir, x)))
                base_apk = os.path.join(tmp_dir, largest)
                split_apks = [os.path.join(tmp_dir, x) for x in apk_files if x != largest]

            to_install = [base_apk] + split_apks
            log_info(f"Installing split bundle ({len(to_install)} split packages selected)...")

            args = ["install-multiple", "-r", "-d"]
            if grant_permissions:
                args.append("-g")
            args.extend(to_install)

            code, out, err = self.run_adb(args)
            combined = out + "\n" + err
            if "Success" in combined:
                log_info(f"{Colors.GREEN}Successfully installed bundle {os.path.basename(bundle_path)}{Colors.RESET}")
                return True
            else:
                log_error(f"Failed to install bundle:\n{combined}")
                return False


def locate_adb() -> str:
    found = shutil.which("adb")
    if found:
        return found
    candidates = [
        "/usr/local/bin/adb",
        "/opt/homebrew/bin/adb",
        os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
        os.path.expanduser("~/platform-tools/adb"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    win_path = shutil.which("adb.exe")
    if win_path:
        return win_path
    raise FileNotFoundError("Could not find 'adb' in PATH.")


def main():
    parser = argparse.ArgumentParser(
        description="Xiaomi TV Stick 4K / Android TV Smart APK & Bundle Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 install_apk.py app.apk
  python3 install_apk.py ru.kinopoisk.tv.apkm
  python3 install_apk.py ~/Downloads/*.apk
        """,
    )
    parser.add_argument("files", nargs="+", help="Path to .apk, .apkm, or .xapk files to install")
    parser.add_argument("-g", "--grant-permissions", action="store_true", help="Grant all runtime permissions upon installation")
    parser.add_argument("-s", "--serial", default=None, help="Device serial if multiple ADB devices are connected")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without installing")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose command output")

    args = parser.parse_args()

    try:
        adb_path = locate_adb()
        installer = AppInstaller(
            adb_bin=adb_path,
            device_serial=args.serial,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        success = 0
        total = 0

        for pattern in args.files:
            file_path = os.path.abspath(pattern)
            if not os.path.isfile(file_path):
                log_warn(f"File not found: {file_path}")
                continue

            total += 1
            ext = file_path.lower()
            if ext.endswith(".apk"):
                if installer.install_single_apk(file_path, grant_permissions=args.grant_permissions):
                    success += 1
            elif ext.endswith(".apkm") or ext.endswith(".xapk") or ext.endswith(".zip"):
                if installer.install_bundle(file_path, grant_permissions=args.grant_permissions):
                    success += 1
            else:
                log_warn(f"Unsupported file format: {file_path}")

        print(f"\n{Colors.BOLD}{Colors.GREEN}Finished: {success}/{total} applications installed.{Colors.RESET}")

    except Exception as e:
        log_error(f"Installation aborted: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
