# Troubleshooting & Hardware Guide

This guide covers real-world edge cases, hardware pitfalls, and software anomalies encountered when unbricking and optimizing the Xiaomi TV Stick 4K (`MDZ-27-AA`).

---

## 1. Hardware & Power Delivery

### Symptom: macOS disables USB port (`failed to create device 0xe00002bc`)
* **Error Log (macOS Console / dmesg):**
  ```text
  AppleUSBHostPort::disconnect: port 2 power off
  kernel: (IOUSBHostFamily) [IOUSBHostDevice.cpp:274] failed to create device (0xe00002bc)
  AppleUSBHostPort::setPowerState: disabling port due to excessive current draw
  ```
* **Cause:**
  The TV Stick 4K requires **5V / 1.0A to 1.5A** during bootup and NAND flash operations. If connected through an unpowered/passive USB hub (especially one sharing power with Ethernet or SD card readers), the sudden voltage sag triggers macOS or Linux hardware overcurrent protection, causing the OS to immediately disable the USB controller port.
* **Solution:**
  1. **Do not use unpowered multi-port hubs.**
  2. Connect the TV Stick directly to a native USB 3.0 / USB-C port on your computer using a certified data-capable Micro-USB cable.
  3. If using a hub, ensure it is an **externally powered USB hub** (with its own 12V/5V DC wall adapter).

---

## 2. Fastboot Stages & Bootloader Transition

### Symptom: Fastboot hangs or returns `FAILED (Variable not implemented)`
* **Log:**
  ```text
  $ fastboot getvar current-slot
  FAILED (remote: 'Variable not implemented')
  $ fastboot flash super super.img
  FAILED (remote: 'Permission denied' or 'unknown partition')
  ```
* **Cause:**
  The device is in **Stage 1 (Primary Amlogic Bootloader)**:
  * USB VID/PID: `VID_1B8E & PID_C004`
  * Product: `amlogic`
  * Bootloader version: `0.1`
  In Stage 1, the bootloader only accepts minimal commands (`reboot`, `reboot bootloader`, `getvar`). Dynamic partitions like `super` and A/B slot switching are not yet loaded into memory.
* **Solution:**
  * Transition to **Stage 2** by executing:
    ```bash
    fastboot reboot bootloader
    ```
  * Wait 3–5 seconds. The stick will re-enumerate with USB VID/PID `VID_18D1 & PID_4EE7` and `product: soul`.
  * `flash_recovery.py` handles this transition automatically.

---

## 3. Persistent Bootloop on Logo After Manual Erase

### Symptom: Fastboot completes without errors, but stick hangs forever on "MI" logo
* **Cause:**
  Running `fastboot erase userdata` leaves the partition as raw, unformatted zeroed blocks. Modern Android 14 `init` requires an initialized **ext4 or f2fs filesystem structure** with cryptographic metadata in `/metadata`. If unformatted, the kernel aborts mount during early boot.
* **Solution:**
  * Always use `fastboot -w` rather than `fastboot erase`:
    ```bash
    fastboot -w
    ```
  * `fastboot -w` invokes host-side `mke2fs` to generate clean, valid filesystem structures on both `userdata` and `metadata`.

---

## 4. Wi-Fi Turns ON but Scans No Networks

### Symptom: Wi-Fi toggle is ON, but the list of available networks remains empty
* **Diagnosis via ADB:**
  ```bash
  adb shell cmd wifi status
  # Radio is active, MT7663 firmware loaded, but no APs displayed in Settings
  ```
* **Cause:**
  Following a factory reset or wipe, the internal Real-Time Clock (RTC) resets to a factory timestamp (e.g., June 10, 2026 or January 1970). Android's `WifiTracker` compares the timestamp of received beacon frames against the local system clock. When the clock is out of sync by months, `WifiTracker` classifies all scanned packets as "stale" or "expired" and drops them from the UI.
* **Solution:**
  Synchronize the system clock with your computer:
  ```bash
  python3 optimize_stick.py --fix-time
  ```
  Or via manual ADB:
  ```bash
  # Current Unix timestamp in milliseconds
  adb shell cmd alarm set-time $(python3 -c 'import time; print(int(time.time()*1000))')
  adb shell cmd wifi start-scan
  ```
  The Wi-Fi network list will populate immediately.

---

## 5. Remote Button Bug: "Open / Move / Remove" Menu on Click

### Symptom: Short-pressing "OK" on an app icon opens the long-press context menu instead of opening the app
* **Cause:**
  Xiaomi's proprietary background service `mitv.service` registers an internal `AccessibilityKeyService`. This service intercepts key events (`KEYCODE_DPAD_CENTER`, `KEYCODE_ENTER`). On non-original or replacement Bluetooth remotes, it fails to send key-release events promptly, delaying the release signal. The Android TV launcher interprets the delayed release as a continuous long-press.
* **Solution:**
  Run the automated fix:
  ```bash
  python3 optimize_stick.py --fix-menu
  ```
  Which executes:
  ```bash
  adb shell pm disable-user --user 0 mitv.service
  adb shell settings put secure long_press_timeout 800
  ```
  Apps will now launch instantly on a standard click.
