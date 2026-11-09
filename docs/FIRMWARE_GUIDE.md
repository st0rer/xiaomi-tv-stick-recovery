# Firmware & Partition Guide

This guide details the partition layout, official firmware archives, extraction instructions, and file verification for the **Xiaomi TV Stick 4K (MDZ-27-AA / soul)**.

---

## 1. Official Factory Firmware Details

* **Target Device:** Xiaomi TV Stick 4K (MDZ-27-AA)
* **Codename:** `soul`
* **SoC:** Amlogic S905Y4
* **Android Version:** Android 14 (Google TV)
* **Build ID:** `UKG3.250107.001.V816.0.26.6.10.UZFAATK`
* **Package Name:** `mi-tv-stick-4k_14_26.6.10_91_MDZ-27-AA.7z`
* **Archive Size:** ~989 MB (Compressed 7z) / ~2.2 GB (Extracted)

---

## 2. Partition Architecture Overview

The device uses an Android Virtual A/B partition scheme with dynamic partitions. The partitions are structured as follows:

| Partition Name | Typical Size | Description |
| :--- | :--- | :--- |
| `bootloader.img` | ~4 MB | Amlogic primary bootloader and cryptographic trust zone keys. |
| `dtbo.img` | ~8 MB | Device Tree Blob Overlay containing peripheral hardware configs (Wi-Fi, Bluetooth, HDMI, PMIC). |
| `oem.img` | ~1 MB | OEM configuration flags and default system configurations. |
| `odm_ext.img` | ~16 MB | Original Design Manufacturer kernel modules and hardware abstraction layer (HAL) libraries. |
| `vbmeta.img` | ~64 KB | Verified Boot Metadata: cryptographic signatures validating partition integrity. |
| `vbmeta_system.img` | ~64 KB | AVB signatures dedicated to system and vendor partitions. |
| `vendor_boot.img` | ~64 MB | First-stage vendor ramdisk containing early-mount fstab tables and drivers. |
| `boot.img` | ~64 MB | Linux Kernel (v5.4.x) and core Android ramdisk. |
| `super.img` | ~1.8 GB | Dynamic Partition Container encapsulating `system`, `system_ext`, `vendor`, and `product`. |

---

## 3. How to Extract the Firmware

### On macOS:
```bash
# Install 7zip via Homebrew if needed:
brew install p7zip

# Extract into a firmware/ folder:
mkdir -p ./firmware
7z x mi-tv-stick-4k_14_26.6.10_91_MDZ-27-AA.7z -o./firmware
```

### On Linux (Ubuntu / Debian / Arch):
```bash
sudo apt install p7zip-full   # Ubuntu/Debian
# or: sudo pacman -S p7zip    # Arch Linux

mkdir -p ./firmware
7z x mi-tv-stick-4k_14_26.6.10_91_MDZ-27-AA.7z -o./firmware
```

### On Windows:
1. Download and install [7-Zip](https://www.7-zip.org/).
2. Right-click `mi-tv-stick-4k_14_26.6.10_91_MDZ-27-AA.7z` $\rightarrow$ **7-Zip** $\rightarrow$ **Extract to "firmware"**.

---

## 4. Verification Checklist Before Flashing

Ensure your target directory contains the following `.img` files:
```text
firmware/
├── bootloader.img
├── dtbo.img
├── oem.img
├── odm_ext.img
├── vbmeta.img
├── vbmeta_system.img
├── vendor_boot.img
├── boot.img
└── super.img
```

> [!TIP]
> `flash_recovery.py` automatically checks for the presence of all required partition images before executing any fastboot commands. If any critical image is missing, it aborts safely without touching your device.
