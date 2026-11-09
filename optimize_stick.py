#!/usr/bin/env python3
"""
Xiaomi TV Stick 4K / Android TV Optimizer & Debloater
Author: Open Source Community
License: MIT

Automates post-recovery ADB setup:
- Fixes empty Wi-Fi networks bug by synchronizing system clock
- Fixes remote click delay / context menu popup bug caused by mitv.service
- Disables 24 bloatware, telemetry, and tracking packages
- Applies UI animation speedups and disables battery/CPU-wasting background scans
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import time
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

# Safe list of packages that can be disabled on Xiaomi TV Stick 4K (MDZ-27-AA / soul)
# without breaking Google TV Home, Play Store, Widevine DRM, or Cast/Miracast.
BLOATWARE_PACKAGES = [
    # Xiaomi Telemetry & Tracking
    ("com.miui.tv.analytics", "Xiaomi TV Analytics"),
    ("com.xiaomi.statistic", "Xiaomi Statistics Daemon"),
    ("com.xiaomo.tv.milegal", "Xiaomi Legal & Privacy Tracking"),
    ("com.xm.webcontent", "Xiaomi Promo Web Content & Ads"),
    ("com.xiaomi.tvqs.overseas", "Xiaomi TV Quick Survey Overseas"),
    ("com.xiaomi.tvqs.overseas.y24", "Xiaomi Quick Survey 2024 Overseas"),
    ("com.xiaomi.android.tvsetup.partnercustomizer", "Xiaomi Setup Partner Customizer"),
    ("com.xiaomi.mitv.updateservice", "Xiaomi OTA Update Service (Prevents corrupt OTA bricks)"),
    ("com.mitv.cloudcontrol", "Mi TV Cloud Control Telemetry"),

    # Xiaomi PatchWall & Stock Overlays
    ("com.mitv.tvhome.atv", "PatchWall ATV Integration"),
    ("com.mitv.tvhome.oemtab", "PatchWall OEM Partner Promo Tab"),
    ("com.mitv.tvhome.michannel", "Mi Channels Promo Feed"),
    ("com.mitv.tvhome.mitvplus", "Mi TV Plus Free Live TV Feed"),
    ("com.mitv.shoplugin", "Mi TV Shop Plugin"),
    ("com.xiaomi.floatingframe", "Xiaomi Floating Banner Daemon"),
    ("com.xiaomi.mimusic2", "Mi Music Stock Player"),
    ("com.mitv.videoplayer", "Mi Stock Video Player"),
    ("com.mitv.dream", "Mi Screensaver / Dream Service"),
    ("com.xiaomi.mitv.smartshare", "Mi SmartShare Background Service"),
    ("com.xiaomi.screenrecorder", "Xiaomi Screen Recorder Background Service"),
    ("com.xiaomi.gamecenter.sdk.service.mibox", "Xiaomi Game Center SDK"),

    # Partner Auto-Installers (Silent background app downloads)
    ("android.autoinstalls.config.soc.amlogic", "Amlogic Partner Auto-install Configuration"),
    ("android.autoinstalls.config.xioami.mibox3", "Xiaomi Partner Auto-install Daemon (sic)"),
    ("android.autoinstalls.config.xiaomi.amelie", "Xiaomi Partner Auto-install Amelie"),

    # Preinstalled Third-party / Google ballast
    ("com.amazon.amazonvideo.livingroom", "Amazon Prime Video preinstalled stub"),
    ("com.netflix.ninja", "Netflix preinstalled client"),
    ("com.netflix.tokenmanager", "Netflix Token Manager"),
    ("com.google.android.videos", "Google TV / Play Movies legacy video app"),
    ("com.google.android.play.games", "Google Play Games"),
    ("com.google.android.youtube.tvmusic", "YouTube Music TV client"),
    ("com.google.android.youtube.tvkids", "YouTube Kids preinstalled client"),
    ("com.google.android.marvin.talkback", "Android Accessibility TalkBack"),
    ("com.google.android.partnersetup", "Google Partner Setup (RLZ attribution pings)"),

    # Background feedback & printing
    ("com.android.printspooler", "Android Print Spooler (Unnecessary on TV)"),
    ("com.google.android.feedback", "Google Feedback Agent"),
    ("com.android.tv.feedbackconsent", "Android TV Feedback Consent"),
    ("com.google.android.tvrecommendations", "Google TV Recommendations Ad Feed"),
]

def log_info(msg: str) -> None:
    print(f"{Colors.GREEN}[INFO]{Colors.RESET} {msg}")

def log_warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")

def log_error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


class StickOptimizer:
    def __init__(self, adb_bin: str, device_serial: Optional[str] = None, dry_run: bool = False, verbose: bool = False):
        self.adb_bin = adb_bin
        self.device_serial = device_serial
        self.dry_run = dry_run
        self.verbose = verbose

    def run_adb(self, args: List[str], check: bool = False) -> Tuple[int, str, str]:
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
        if check and p.returncode != 0:
            raise RuntimeError(f"ADB command failed ({p.returncode}): {' '.join(cmd)}\n{combined}")
        return p.returncode, out, err

    def run_shell(self, cmd_str: str, check: bool = False) -> str:
        code, out, err = self.run_adb(["shell", cmd_str], check=check)
        return (out + "\n" + err).strip()

    def check_connection(self) -> str:
        code, out, err = self.run_adb(["devices"])
        lines = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith("*")]
        devices = []
        for line in lines[1:]:  # skip 'List of devices attached'
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])

        if not devices:
            if self.dry_run:
                log_warn("[DRY-RUN] No physical ADB device attached. Simulating on mock device (Xiaomi TV Stick 4K)...")
                self.device_serial = "DRYRUN_DEVICE_0001"
                return self.device_serial
            raise ConnectionError("No authorized ADB devices found. Ensure USB debugging is ON.")

        if self.device_serial:
            if self.device_serial not in devices:
                raise ConnectionError(f"Target device {self.device_serial} not found in connected devices: {devices}")
            chosen = self.device_serial
        else:
            chosen = devices[0]
            self.device_serial = chosen

        model = self.run_shell("getprop ro.product.model")
        brand = self.run_shell("getprop ro.product.brand")
        log_info(f"Connected to device: {Colors.BOLD}{brand} {model}{Colors.RESET} (Serial: {chosen})")
        return chosen

    def fix_time_and_wifi(self) -> None:
        """
        Synchronizes system clock from host PC.
        Stale clock (e.g., set to factory date) causes WifiTracker to discard all scanned APs.
        """
        log_info("Synchronizing system clock with host system...")
        now = datetime.datetime.now()
        timestamp_ms = int(now.timestamp() * 1000)
        formatted_date = now.strftime("%m%d%H%M%Y.%S")

        # 1. Try cmd alarm set-time
        res1 = self.run_shell(f"cmd alarm set-time {timestamp_ms}")
        # 2. Also set date formatted
        res2 = self.run_shell(f"date {formatted_date}")

        log_info(f"System time set to: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        log_info("Triggering Wi-Fi scan refresh...")
        self.run_shell("cmd wifi start-scan")
        log_info(f"{Colors.GREEN}Clock & Wi-Fi fix applied successfully.{Colors.RESET}")

    def fix_context_menu_bug(self) -> None:
        """
        Disables mitv.service and adjusts long_press_timeout.
        mitv.service runs AccessibilityKeyService which delays DPAD_CENTER release on third-party
        remotes, causing normal clicks to be misinterpreted as long-presses (triggering 'Open / Move').
        """
        log_info("Fixing context menu popup bug (mitv.service / AccessibilityKeyService)...")
        # 1. Disable mitv.service
        out = self.run_shell("pm disable-user --user 0 mitv.service")
        log_info(f"Disabled mitv.service: {out}")

        # 2. Increase long press threshold to 800ms
        self.run_shell("settings put secure long_press_timeout 800")
        log_info("Set secure setting: long_press_timeout = 800 ms")
        log_info(f"{Colors.GREEN}Context menu bug fixed! Apps will now open instantly on OK click.{Colors.RESET}")

    def debloat(self) -> None:
        log_info(f"Disabling {len(BLOATWARE_PACKAGES)} bloatware & telemetry packages...")
        disabled_count = 0
        skipped_count = 0

        for pkg, desc in BLOATWARE_PACKAGES:
            out = self.run_shell(f"pm disable-user --user 0 {pkg}")
            if "disabled" in out.lower() or "new state" in out.lower():
                log_info(f"  [DISABLED] {pkg} ({desc})")
                disabled_count += 1
            else:
                if self.verbose:
                    print(f"  [SKIP/NOT FOUND] {pkg} ({out})")
                skipped_count += 1

        log_info(f"{Colors.GREEN}Debloat complete: {disabled_count} disabled, {skipped_count} skipped/not present.{Colors.RESET}")

    def restore_debloat(self) -> None:
        log_info(f"Re-enabling {len(BLOATWARE_PACKAGES)} packages...")
        enabled_count = 0
        for pkg, desc in BLOATWARE_PACKAGES:
            out = self.run_shell(f"pm enable {pkg}")
            if "enabled" in out.lower() or "new state" in out.lower():
                log_info(f"  [ENABLED] {pkg} ({desc})")
                enabled_count += 1
        log_info(f"{Colors.GREEN}Restore complete: {enabled_count} packages re-enabled.{Colors.RESET}")

    def apply_speed_tweaks(self) -> None:
        log_info("Applying performance & UI responsiveness tweaks...")

        # 1. Animation speeds: 0.5x makes Android TV UI noticeably snappier
        self.run_shell("settings put global window_animation_scale 0.5")
        self.run_shell("settings put global transition_animation_scale 0.5")
        self.run_shell("settings put global animator_duration_scale 0.5")
        log_info("  - Window/Transition/Animator scales set to 0.5x")

        # 2. Disable always-on Wi-Fi and Bluetooth background scanning
        self.run_shell("settings put global wifi_scan_always_enabled 0")
        self.run_shell("settings put global ble_scan_always_enabled 0")
        log_info("  - Wi-Fi and BLE always-on background scanning disabled")

        # 3. Disable Google Play Protect background hash verification of sideloaded apps
        self.run_shell("settings put global package_verifier_enable 0")
        self.run_shell("settings put global upload_apk_enable 0")
        log_info("  - Play Protect sideload package verification disabled")

        log_info(f"{Colors.GREEN}Performance tweaks applied successfully.{Colors.RESET}")


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
    raise FileNotFoundError("Could not find 'adb' in PATH. Ensure Android Platform Tools are installed.")


def main():
    parser = argparse.ArgumentParser(
        description="Xiaomi TV Stick 4K (MDZ-27-AA / soul) Post-Recovery ADB Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 optimize_stick.py --all
  python3 optimize_stick.py --fix-menu --fix-time
  python3 optimize_stick.py --debloat --speed-tweaks
  python3 optimize_stick.py --restore-debloat
        """,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Apply all optimizations: time fix, menu bug fix, debloat, and speed tweaks.",
    )
    parser.add_argument(
        "--fix-time",
        action="store_true",
        help="Synchronize system clock with host to fix empty Wi-Fi scan results.",
    )
    parser.add_argument(
        "--fix-menu",
        action="store_true",
        help="Disable mitv.service and adjust long_press_timeout to fix context menu popup bug.",
    )
    parser.add_argument(
        "--debloat",
        action="store_true",
        help="Disable 24 bloatware, tracking, and PatchWall packages.",
    )
    parser.add_argument(
        "--restore-debloat",
        action="store_true",
        help="Re-enable all disabled bloatware packages.",
    )
    parser.add_argument(
        "--speed-tweaks",
        action="store_true",
        help="Apply 0.5x UI animations, disable background Wi-Fi/BLE scans and verification.",
    )
    parser.add_argument(
        "-s", "--serial",
        default=None,
        help="Specific device serial number if multiple ADB devices are connected.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without modifying device state.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed command execution output.",
    )

    args = parser.parse_args()

    # Default to --all if no specific action provided
    if not any([args.all, args.fix_time, args.fix_menu, args.debloat, args.restore_debloat, args.speed_tweaks]):
        args.all = True

    print(f"{Colors.BOLD}{Colors.HEADER}====================================================={Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}  Xiaomi TV Stick 4K / Android TV Optimizer (ADB)    {Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}====================================================={Colors.RESET}\n")

    try:
        adb_path = locate_adb()
        optimizer = StickOptimizer(
            adb_bin=adb_path,
            device_serial=args.serial,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        optimizer.check_connection()

        if args.all or args.fix_time:
            optimizer.fix_time_and_wifi()

        if args.all or args.fix_menu:
            optimizer.fix_context_menu_bug()

        if args.all or args.debloat:
            optimizer.debloat()

        if args.restore_debloat:
            optimizer.restore_debloat()

        if args.all or args.speed_tweaks:
            optimizer.apply_speed_tweaks()

        print(f"\n{Colors.BOLD}{Colors.GREEN}Optimization completed successfully!{Colors.RESET}")

    except Exception as e:
        log_error(f"Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
