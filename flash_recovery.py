#!/usr/bin/env python3
"""
Xiaomi TV Stick 4K (MDZ-27-AA / soul) Universal Fastboot Recovery Tool
Author: Open Source Community
License: MIT

Automates recovery of bricked Xiaomi TV Stick 4K devices stuck in bootloops,
with automatic Stage 1 (amlogic) -> Stage 2 (soul) detection, dual-slot (A/B)
partition flashing, ext4 userdata formatting, and post-flash lock options.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

# Terminal color styling
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

# Standard partition image list for Amlogic A/B Android 14 architecture
CRITICAL_PARTITIONS = [
    "bootloader",
    "dtbo",
    "oem",
    "odm_ext",
    "vbmeta",
    "vbmeta_system",
    "vendor_boot",
    "boot",
]

def log_info(msg: str) -> None:
    print(f"{Colors.GREEN}[INFO]{Colors.RESET} {msg}")

def log_warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")

def log_error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")

def log_step(step: int, total: int, msg: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.CYAN}[STEP {step}/{total}] {msg}{Colors.RESET}")


class FastbootRecovery:
    def __init__(self, fastboot_bin: str, firmware_dir: str, dry_run: bool = False, verbose: bool = False):
        self.fastboot_bin = fastboot_bin
        self.firmware_dir = os.path.abspath(firmware_dir)
        self.dry_run = dry_run
        self.verbose = verbose

    def run_cmd(self, args: List[str], check: bool = True, timeout: Optional[int] = None) -> Tuple[int, str, str]:
        cmd = [self.fastboot_bin] + args
        if self.verbose:
            print(f"{Colors.BLUE}[EXEC]{Colors.RESET} {' '.join(cmd)}")
        if self.dry_run:
            return 0, "[DRY-RUN] Success", ""

        try:
            p = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            out = p.stdout.strip()
            err = p.stderr.strip()
            combined = (out + "\n" + err).strip()
            if self.verbose and combined:
                for line in combined.splitlines():
                    print(f"  {line}")
            if check and p.returncode != 0:
                raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}\n{combined}")
            return p.returncode, out, err
        except subprocess.TimeoutExpired:
            log_error(f"Command timed out ({timeout}s): {' '.join(cmd)}")
            raise

    def getvar(self, var_name: str) -> str:
        if self.dry_run:
            mock_vars = {"product": "soul", "version-bootloader": "01.01.260610.084506", "unlocked": "yes", "current-slot": "a"}
            return mock_vars.get(var_name, "mock_val")
        code, out, err = self.run_cmd(["getvar", var_name], check=False)
        combined = (out + "\n" + err).strip()
        for line in combined.splitlines():
            line_str = line.strip()
            if line_str.startswith(f"{var_name}:"):
                val = line_str.split(":", 1)[1].strip()
                return val
        return ""

    def find_devices(self) -> List[str]:
        if self.dry_run:
            return ["DRYRUN_FASTBOOT_001"]
        code, out, err = self.run_cmd(["devices"], check=False)
        devices = []
        for line in (out + "\n" + err).splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "fastboot":
                devices.append(parts[0])
        return devices

    def detect_and_prepare_stage(self, max_wait: int = 60) -> bool:
        """
        Detects device and seamlessly handles Stage 1 (amlogic) -> Stage 2 (soul) transition.
        Stage 1: VID_1B8E, product: amlogic (limited commands, cannot flash super or unlock)
        Stage 2: VID_18D1, product: soul (full fastboot)
        """
        log_info("Waiting for device in Fastboot mode...")
        start_time = time.time()
        while time.time() - start_time < max_wait:
            devices = self.find_devices()
            if devices:
                serial = devices[0]
                product = self.getvar("product")
                bl_version = self.getvar("version-bootloader")
                log_info(f"Connected: Serial={serial}, Product={product or 'unknown'}, Bootloader={bl_version or 'unknown'}")

                if product == "amlogic" or bl_version == "0.1":
                    log_warn("Device detected in Fastboot STAGE 1 (Amlogic primary bootloader)!")
                    log_info("Transitioning to STAGE 2 (product: soul)...")
                    try:
                        self.run_cmd(["reboot", "bootloader"], check=False)
                    except Exception:
                        pass
                    log_info("Waiting for Stage 2 re-enumeration...")
                    time.sleep(3)
                    continue

                if product == "soul" or "soul" in (product or ""):
                    log_info(f"{Colors.GREEN}Successfully reached Fastboot STAGE 2 (soul)!{Colors.RESET}")
                    return True

                # If product name is empty or another string but device responds to fastboot
                if product:
                    log_info(f"Target device recognized as: {product}")
                    return True
            time.sleep(1)

        raise TimeoutError(f"No device reached Fastboot Stage 2 within {max_wait} seconds.")

    def verify_firmware_files(self) -> Dict[str, str]:
        """Checks for required firmware partition images in firmware_dir."""
        found_files = {}
        missing_critical = []

        log_info(f"Checking firmware directory: {self.firmware_dir}")
        if not os.path.isdir(self.firmware_dir):
            if self.dry_run:
                log_warn(f"[DRY-RUN] Directory {self.firmware_dir} does not exist. Simulating mock partition files...")
                mock_images = {part: f"/mock/path/{part}.img" for part in CRITICAL_PARTITIONS}
                mock_images["super"] = "/mock/path/super.img"
                return mock_images
            raise FileNotFoundError(f"Firmware directory does not exist: {self.firmware_dir}")

        for part in CRITICAL_PARTITIONS:
            expected_name = f"{part}.img"
            path = os.path.join(self.firmware_dir, expected_name)
            if os.path.isfile(path):
                found_files[part] = path
            else:
                missing_critical.append(expected_name)

        super_path = os.path.join(self.firmware_dir, "super.img")
        if os.path.isfile(super_path):
            found_files["super"] = super_path
        else:
            # Check for super chunks (super.img_sparsechunk.0, etc.)
            chunks = [f for f in os.listdir(self.firmware_dir) if f.startswith("super.img") or "super" in f]
            if chunks:
                found_files["super"] = os.path.join(self.firmware_dir, sorted(chunks)[0])
            else:
                log_warn("super.img not found in directory. OS image will be skipped if not provided.")

        if self.dry_run and missing_critical:
            log_warn(f"[DRY-RUN] Simulating mock partition files for missing images...")
            mock_images = {part: f"/mock/path/{part}.img" for part in CRITICAL_PARTITIONS}
            mock_images["super"] = "/mock/path/super.img"
            return mock_images

        if missing_critical:
            raise FileNotFoundError(
                f"Missing critical partition images in {self.firmware_dir}:\n - "
                + "\n - ".join(missing_critical)
            )

        log_info(f"Verified {len(found_files)} partition images ready to flash.")
        return found_files

    def unlock_if_needed(self) -> None:
        unlocked = self.getvar("unlocked")
        if unlocked.lower() == "yes":
            log_info("Bootloader is already UNLOCKED.")
            return

        log_warn("Bootloader is LOCKED. Attempting unlock...")
        self.run_cmd(["flashing", "unlock"], check=True)
        time.sleep(2)
        unlocked_after = self.getvar("unlocked")
        if unlocked_after.lower() == "yes":
            log_info(f"{Colors.GREEN}Bootloader successfully unlocked!{Colors.RESET}")
        else:
            log_warn("Could not verify unlock status. Proceeding...")

    def flash_all(self, images: Dict[str, str], skip_super: bool = False) -> None:
        total_steps = len(CRITICAL_PARTITIONS) * 2 + (0 if skip_super else 1)
        step = 1

        # Flash critical partitions to both slots A and B
        for part in CRITICAL_PARTITIONS:
            img_path = images[part]
            file_size_mb = (os.path.getsize(img_path) / (1024 * 1024)) if os.path.isfile(img_path) else 16.0

            for slot in ["a", "b"]:
                target_part = f"{part}_{slot}"
                log_step(step, total_steps, f"Flashing {target_part} ({file_size_mb:.2f} MB)...")
                self.run_cmd(["flash", target_part, img_path], check=True)
                step += 1

        # Flash super partition
        if not skip_super and "super" in images:
            super_path = images["super"]
            file_size_mb = (os.path.getsize(super_path) / (1024 * 1024)) if os.path.isfile(super_path) else 1840.0
            log_step(step, total_steps, f"Flashing dynamic container super.img ({file_size_mb:.2f} MB)...")
            # Set high timeout for large super.img (can take up to 3-5 minutes)
            self.run_cmd(["flash", "super", super_path], check=True, timeout=600)
            step += 1

    def wipe_and_format(self) -> None:
        log_info("Performing factory format of userdata & metadata (fastboot -w)...")
        # fastboot -w recreates ext4 / f2fs filesystems properly
        self.run_cmd(["-w"], check=True, timeout=180)
        log_info(f"{Colors.GREEN}Wipe & format completed successfully.{Colors.RESET}")

    def finalize(self, active_slot: str = "a", lock_bootloader: bool = False) -> None:
        log_info(f"Setting active boot slot to '{active_slot}'...")
        self.run_cmd(["set_active", active_slot], check=False)

        if lock_bootloader:
            log_info("Locking bootloader back to factory locked state...")
            self.run_cmd(["flashing", "lock"], check=False)

        log_info(f"{Colors.BOLD}{Colors.GREEN}Recovery flashing completed successfully!{Colors.RESET}")


def locate_fastboot() -> str:
    # 1. Check system PATH
    found = shutil.which("fastboot")
    if found:
        return found

    # 2. Common install paths on macOS / Linux
    candidates = [
        "/usr/local/bin/fastboot",
        "/opt/homebrew/bin/fastboot",
        os.path.expanduser("~/Library/Android/sdk/platform-tools/fastboot"),
        os.path.expanduser("~/platform-tools/fastboot"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c

    # Windows fallback
    win_path = shutil.which("fastboot.exe")
    if win_path:
        return win_path

    raise FileNotFoundError("Could not find 'fastboot' binary in PATH or default locations. Install Android Platform Tools.")


def main():
    parser = argparse.ArgumentParser(
        description="Xiaomi TV Stick 4K (MDZ-27-AA / soul) Universal Fastboot Recovery Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 flash_recovery.py --firmware-dir ./firmware
  python3 flash_recovery.py --firmware-dir /path/to/extracted_images --lock
  python3 flash_recovery.py --firmware-dir ./firmware --dry-run --verbose
        """,
    )
    parser.add_argument(
        "-f", "--firmware-dir",
        default="./firmware",
        help="Directory containing unpacked firmware partition images (*.img). Default: ./firmware",
    )
    parser.add_argument(
        "--fastboot-bin",
        default=None,
        help="Explicit path to fastboot binary. Default: auto-detect from PATH.",
    )
    parser.add_argument(
        "--slot",
        default="a",
        choices=["a", "b"],
        help="Slot to set active after flashing. Default: a",
    )
    parser.add_argument(
        "--skip-super",
        action="store_true",
        help="Skip flashing super.img container (useful for quick bootloader/kernel repair).",
    )
    parser.add_argument(
        "--skip-wipe",
        action="store_true",
        help="Skip userdata format (fastboot -w). WARNING: May cause bootloop if OS upgraded.",
    )
    parser.add_argument(
        "--lock",
        action="store_true",
        help="Lock bootloader back after flashing (recommended for factory stock state).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the entire recovery workflow without executing fastboot commands.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose fastboot output.",
    )

    args = parser.parse_args()

    print(f"{Colors.BOLD}{Colors.HEADER}====================================================={Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}  Xiaomi TV Stick 4K (MDZ-27-AA / soul) Recovery Tool{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}====================================================={Colors.RESET}\n")

    try:
        fastboot_path = args.fastboot_bin or locate_fastboot()
        log_info(f"Using fastboot binary: {fastboot_path}")
    except FileNotFoundError as e:
        log_error(str(e))
        sys.exit(1)

    recovery = FastbootRecovery(
        fastboot_bin=fastboot_path,
        firmware_dir=args.firmware_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    try:
        # Step 1: Verify firmware images exist before touching hardware
        images = recovery.verify_firmware_files()

        # Step 2: Detect device & handle Stage 1 -> Stage 2
        recovery.detect_and_prepare_stage()

        # Step 3: Unlock bootloader if locked
        recovery.unlock_if_needed()

        # Step 4: Flash critical partitions to both slots & super
        recovery.flash_all(images, skip_super=args.skip_super)

        # Step 5: Wipe userdata & metadata
        if not args.skip_wipe:
            recovery.wipe_and_format()
        else:
            log_warn("Skipping wipe per --skip-wipe flag.")

        # Step 6: Finalize (set active slot & optional lock)
        recovery.finalize(active_slot=args.slot, lock_bootloader=args.lock)

        print(f"\n{Colors.BOLD}{Colors.GREEN}====================================================={Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}  DONE! You can now reboot the TV Stick:{Colors.RESET}")
        print(f"{Colors.CYAN}    fastboot reboot{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}====================================================={Colors.RESET}\n")

    except Exception as e:
        log_error(f"Recovery failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
