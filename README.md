# Xiaomi TV Stick 4K (MDZ-27-AA / soul) Universal Recovery & Optimization Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)]()
[![Tested Device](https://img.shields.io/badge/device-Xiaomi%20TV%20Stick%204K-orange.svg)]()

> Complete, production-grade open-source toolkit to recover bricked **Xiaomi TV Stick 4K (MDZ-27-AA / soul)** devices stuck in bootloops (e.g. after broken Android 11 $\rightarrow$ 14 OTA upgrades), safely flash dual-slot partitions, eliminate bloatware, and tune performance.

📖 **[Читать на русском языке (README_RU.md)](README_RU.md)**

---

## 🚀 Key Features

* **⚡ Automated Fastboot Stage Transition:**
  Seamlessly detects **Stage 1** (`amlogic` / `0.1` bootloader) and transitions the stick into **Stage 2** (`soul` full fastboot) without manual intervention.
* **🛡️ Dual-Slot (A/B) Integrity:**
  Flashes all critical partitions (`bootloader`, `dtbo`, `oem`, `odm_ext`, `vbmeta`, `vendor_boot`, `boot`) to both Slot A and Slot B to prevent boot failure during fallback slot switching.
* **📦 Super Partition Flashing:**
  Robust handling of the dynamic 1.8 GB `super.img` container with elevated timeouts.
* **🧹 Proper Filesystem Formatting:**
  Executes `fastboot -w` to format `userdata` and `metadata` into ext4 structures, preventing post-flash logo bootloops.
* **📶 Empty Wi-Fi Network Fix:**
  Automatically corrects system clock desync via ADB, restoring functional Wi-Fi scanning.
* **🎯 Remote OK-Click Bug Fix:**
  Disables `mitv.service` and optimizes keypress timings so apps open instantly without triggering the annoying *"Open / Move / Remove"* context menu.
* **🚀 24-Package Safe Debloat:**
  Disables Xiaomi analytics, tracking, PatchWall, and system ballast while keeping Google Play, Widevine DRM (4K Netflix/Kinopoisk), and Cast fully functional.
* **📦 Smart APK & Bundle (.apkm / .xapk) Installer:**
  Automatically detects device ABI (`armeabi-v7a`), extracts APKMirror split bundles, filters incompatible architectures, and installs via `adb install-multiple`.

---

## 📋 Table of Contents

* [Device Compatibility](#-device-compatibility)
* [Prerequisites](#-prerequisites)
* [Quick Start: Unbricking (Fastboot)](#-quick-start-unbricking-fastboot)
* [Post-Install Optimization (ADB)](#-post-install-optimization-adb)
* [Installing Apps & APKM Bundles](#-installing-apps--apkm-bundles)
* [Documentation Links](#-documentation-links)
* [License](#-license)

---

## 📱 Device Compatibility

| Model | Marketing Name | Codename | SoC | Fastboot Recovery Script | ADB Optimizer Script |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MDZ-27-AA** | **Xiaomi TV Stick 4K** | `soul` | S905Y4 | **100% Tested & Supported** | **100% Supported** |
| **MDZ-28-AA** | Xiaomi TV Box S (2nd Gen) | `daisy` | S905X4 | **Compatible** *(with daisy images)* | **100% Supported** |
| **MDZ-24-AA** | Mi TV Stick 1080p | `aquaman` | S805Y | Incompatible *(Legacy partition layout)* | **Supported** |

*For deep dive analysis on hardware differences, check [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).*

---

## 🛠️ Prerequisites

1. **Python 3.8+** installed on your host system.
2. **Android Platform Tools (`adb` and `fastboot`)**:
   * **macOS:** `brew install android-platform-tools`
   * **Linux (Debian/Ubuntu):** `sudo apt install adb fastboot`
   * **Windows:** Download [SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) and add to PATH.
3. **Power Requirement:**
   > [!WARNING]
   > Do **NOT** connect the TV Stick through a passive/unpowered USB hub. Voltage drops will trip host overcurrent protection (`0xe00002bc`). Connect directly to a native USB port on your PC or use a powered hub. See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

---

## ⚡ Quick Start: Unbricking (Fastboot)

### 1. Obtain and Unpack Factory Firmware
Download the official Android 14 factory firmware archive (`mi-tv-stick-4k_14_26.6.10_91_MDZ-27-AA.7z`) and extract it into a `firmware/` directory:
```bash
mkdir -p firmware
7z x mi-tv-stick-4k_14_26.6.10_91_MDZ-27-AA.7z -o./firmware
```
*(See [docs/FIRMWARE_GUIDE.md](docs/FIRMWARE_GUIDE.md) for partition verification).*

### 2. Connect the Stick
1. Connect the TV Stick via Micro-USB to your computer.
2. If the stick is stuck in a bootloop, power cycle it while connected.
3. Run the recovery tool:
```bash
python3 flash_recovery.py --firmware-dir ./firmware --lock
```

### Options for `flash_recovery.py`:
* `--firmware-dir PATH`: Directory containing extracted `.img` files (default: `./firmware`).
* `--lock`: Lock the bootloader back after flashing (returns stick to stock status).
* `--skip-super`: Skip flashing the 1.8 GB `super.img` (useful for quick kernel/bootloader repair).
* `--dry-run`: Test run without modifying hardware.

When completed, reboot the device:
```bash
fastboot reboot
```

---

## 🚀 Post-Install Optimization (ADB)

Once the TV Stick boots to the setup screen or desktop, enable **USB Debugging** (in *Settings $\rightarrow$ Device Preferences $\rightarrow$ Developer options*).

Run the all-in-one optimizer:
```bash
python3 optimize_stick.py --all
```

### What this does:
1. **Synchronizes Clock & Wi-Fi:** Solves the bug where empty Wi-Fi scan results occur due to stale RTC timestamps.
2. **Fixes OK Button Delay:** Disables `mitv.service` and increases `long_press_timeout 800` so apps open immediately without opening the context menu.
3. **Debloats 24 Junk Packages:** Removes Xiaomi tracking, PatchWall, ads, and telemetry.
4. **Boosts Responsiveness:** Sets UI animation scales to `0.5x` and disables background Wi-Fi/BLE polling.

To re-enable debloated packages at any time:
```bash
python3 optimize_stick.py --restore-debloat
```

---

## 📦 Installing Apps & APKM Bundles

Android TV hides phone-specific apps that lack `LEANBACK_LAUNCHER`. To install apps or complex APKMirror split bundles (`.apkm` / `.xapk`):

```bash
# Install standard APK
python3 install_apk.py my_app.apk

# Install APKMirror bundle (automatically filters for armeabi-v7a)
python3 install_apk.py ru.kinopoisk.tv_2.256.1.apkm

# Batch install multiple files
python3 install_apk.py ~/Downloads/*.apk
```

---

## 📚 Documentation Links

* 📖 **[Compatibility Matrix (docs/COMPATIBILITY.md)](docs/COMPATIBILITY.md)**: Hardware architectures, SoCs (S905Y4 vs S905X4 vs S805Y), and the "Two Bricks" dilemma.
* 🔧 **[Troubleshooting Guide (docs/TROUBLESHOOTING.md)](docs/TROUBLESHOOTING.md)**: USB overcurrent errors, Fastboot Stage 1 vs 2, Wi-Fi date sync, and remote button fixes.
* 📦 **[Firmware & Partition Guide (docs/FIRMWARE_GUIDE.md)](docs/FIRMWARE_GUIDE.md)**: Partition layouts, extraction, and verification.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
Contributions, issues, and pull requests are welcome!
