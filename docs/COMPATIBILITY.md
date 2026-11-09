# Hardware & Device Compatibility Matrix

This document provides a comprehensive technical overview of Xiaomi TV streaming devices, chipsets (SoCs), partition architectures, and recovery compatibility.

---

## Quick Compatibility Summary

| Device Model | Marketing Name | Codename | SoC | Partition Scheme | Bootloader Type | Recovery Script Compatibility | Optimizer Script Compatibility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MDZ-27-AA** | **Xiaomi TV Stick 4K** | `soul` | Amlogic S905Y4 | Dynamic (`super.img`) + A/B | **2-Stage Fastboot** | **Verified (Native)** | **100% Supported** |
| **MDZ-28-AA** | **Xiaomi TV Box S (2nd Gen)** | `daisy` | Amlogic S905X4 | Dynamic (`super.img`) + A/B | **2-Stage Fastboot** | **Compatible** *(with `daisy` firmware)* | **100% Supported** |
| **MDZ-24-AA** | Mi TV Stick 1080p | `aquaman` | Amlogic S805Y | Legacy (system/vendor) | 1-Stage Fastboot / DNL | **Incompatible** *(Legacy layout)* | **Supported** *(Debloat & Speed)* |
| **MDZ-22-AB** | Mi Box S (1st Gen) | `oneday` | Amlogic S905X | Legacy (Non-dynamic) | Standard Amlogic | **Incompatible** *(Legacy layout)* | **Supported** *(Debloat & Speed)* |
| **MDZ-16-AB** | Mi Box 4K (Global) | `once` | Amlogic S905X-H | Legacy (Non-dynamic) | Standard Amlogic | **Incompatible** *(Legacy layout)* | **Supported** *(Debloat & Speed)* |

---

## Detailed Model Analysis

### 1. Xiaomi TV Stick 4K (`MDZ-27-AA` / `soul`) — PRIMARY TARGET
* **Processor (SoC):** Amlogic S905Y4 (Quad-Core ARM Cortex-A35 @ 2.0 GHz, Mali-G31 MP2 GPU).
* **RAM & Flash:** 2 GB LPDDR4, 8 GB eMMC 5.1.
* **Operating System:** Android TV 11 (initial) $\rightarrow$ Android 14 (V816 build `UKG3.250107.001.V816.0.26.6.10.UZFAATK`).
* **Storage Architecture:** Virtual A/B slots (`_a` and `_b`) with Android Dynamic Partitions (`super.img` encapsulating `system`, `system_ext`, `vendor`, and `product`).
* **Bootloader Mechanism:**
  * **Stage 1:** Initial bootloader exposed over USB (`VID_1B8E & PID_C004`), reports `product: amlogic`, `version-bootloader: 0.1`. Limited command set.
  * **Stage 2:** Secondary full fastboot interface (`VID_18D1 & PID_4EE7`), reports `product: soul`. Allows flashing raw partitions, dynamic container, unlocking, and formatting.
* **Recovery Status:** **Fully supported and tested**. `flash_recovery.py` automatically orchestrates Stage 1 $\rightarrow$ Stage 2 transition, dual-slot partition synchronization, and ext4 `userdata` recreation.

---

### 2. Xiaomi TV Box S 2nd Gen (`MDZ-28-AA` / `daisy`)
* **Processor (SoC):** Amlogic S905X4 (Quad-Core ARM Cortex-A55, Mali-G31 MP2 GPU).
* **RAM & Flash:** 2 GB DDR4, 8 GB eMMC.
* **Operating System:** Google TV based on Android 11 / Android 14.
* **Storage Architecture:** Identical Virtual A/B + dynamic `super.img` container structure as `soul`.
* **Bootloader Mechanism:** 2-Stage Amlogic fastboot bootloader.
* **Recovery Status:** **Architecture-compatible**.
  > [!IMPORTANT]
  > Do **NOT** flash `soul` partition images onto `daisy`. You must supply factory partition images extracted from an official `daisy` firmware package. Once pointed to the correct firmware directory, `flash_recovery.py` will flash `daisy` identically.

---

### 3. Xiaomi Mi TV Stick 1080p (`MDZ-24-AA` / `aquaman`)
* **Processor (SoC):** Amlogic S805Y (Quad-Core Cortex-A53, Mali-450 GPU).
* **RAM & Flash:** 1 GB DDR4, 8 GB eMMC.
* **Operating System:** Android TV 9.0 (Pie).
* **Storage Architecture:** **Legacy partitioning**. Does not use dynamic partitions (`super.img`). Instead, it uses discrete `system.img`, `vendor.img`, `product.img` flashed directly to fixed partition offsets.
* **Recovery Status:** **Incompatible with `flash_recovery.py`**.
  * Unbricking `MDZ-24-AA` requires the classic **Amlogic USB Burning Tool** with a `.img` package or a custom script matching the S805Y partition table.
  * **However:** `optimize_stick.py` and `install_apk.py` are fully compatible over ADB for debloating and installing apps.

---

### 4. Xiaomi Mi Box S 1st Gen (`MDZ-22-AB` / `oneday`)
* **Processor (SoC):** Amlogic S905X.
* **Operating System:** Android 8.1 / 9.0 / Android 12 update.
* **Storage Architecture:** Single slot, non-dynamic partition table.
* **Recovery Status:** Requires Amlogic USB Burning Tool or recovery `.zip` via stock recovery (holding Back + OK on remote). Incompatible with modern S905Y4/X4 dual-slot fastboot script.

---

## The "Two Bricks" Dilemma: Why OTA A11 $\rightarrow$ A14 Breaks

Many users experience a hard bootloop on the "MI" logo after accepting the official Xiaomi Android 14 update. Understanding why this happens is crucial:

```
[Android 11 State] ──(OTA Interrupted)──> [Corrupt Hybrid State]
  Bootloader: A11                           Bootloader: A14 (Updated)
  OS Partitions: A11                        OS / Super: A11 or Half-written
  Rollback Index: 0                         Rollback Index: Incremented (Anti-rollback)
```

1. **Bootloader Updates First:** During the OTA update, the bootloader (`bootloader.img`, `dtbo.img`, and cryptographic keys) is flashed first and the internal Anti-Rollback (ARB) index is burned/incremented into eFuse/rpmb.
2. **Crash / Interruption During Super Flash:** The `super.img` partition on Android 14 is ~1.8 GB. If the device experiences a power drop or storage write timeout, `super.img` remains corrupted or incomplete.
3. **Why Downgrading to Android 11 Fails:**
   * Because the bootloader has already been upgraded to Android 14, attempting to flash Android 11 images will result in `FAILED (remote: rollback version error)` or silent bootloops because the A14 kernel rejects A11 vendor blobs.
4. **The Solution:**
   * You **must** flash a full factory **Android 14** firmware package across both slots (A & B) and perform a clean ext4 format (`fastboot -w`).
