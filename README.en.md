# QuickForcedEjectPortableDisk

简体中文 (Chinese) | English

---
## Background
When using "Safely Remove Hardware and Eject Media", Windows may report "The device is currently in use" even if no files are open. This is often due to background processes or services holding locks. A practical workaround is to perform an Offline→Online cycle to release abnormal locks. On Windows Home editions, the GUI Disk tool cannot offline a disk, so diskpart must be used. This tool simplifies those steps.

---
## Overview
A lightweight Windows GUI utility (Python + PowerShell + diskpart) to enumerate external/removable disks, run an Offline→Online cycle, and attempt logical eject.

---
## Features
- External disk heuristic detection (USB / Removable / External / USBSTOR / DriveType=2)
- Offline→Online (diskpart)
- Multi‑strategy eject (Shell COM → Win32_Volume Dismount → PnP Remove (Invoke‑Pnp / pnputil / devcon) → Disk offline fallback)
- Debug log (core/disk_query_debug.log)
- Auto elevation (UAC)

---
## Environment
Windows 10/11 · Python 3.10+ · Admin rights required for offline/online operations

---
## Install & Run
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
If UAC prompts, allow elevation.

---
## Usage
1. Click "Refresh Disks" (optional on first load)
2. Select the target disk
3. Click "Offline->Online" to release abnormal locks
4. Click "Multi‑strategy Eject" to perform the layered eject
5. Check the log panel for feedback

---
## Multi‑strategy Eject (Implementation)
Order:
1. Shell COM Verb
   Shell.Application NameSpace(17).ParseName('E:').InvokeVerb('Eject')
   Success: drive letter disappears (Test-Path E:\ returns false)
2. Volume Dismount (Win32_Volume)
   Get-CimInstance Win32_Volume -Filter "DriveLetter='E:'" | Invoke-CimMethod -MethodName Dismount -Arguments @{ Force=$false; Permanent=$false }
   Success: letter disappears
3. PnP Removal (hardware level)
   a) Invoke-PnpDeviceAction -Action 9 (if available)
   b) pnputil /remove-device <PNPDeviceID>
   c) devcon remove <PNPDeviceID> (if present)
   Success: Win32_DiskDrive no longer returns that PNPDeviceID
4. Disk Offline Fallback
   Set-Disk -Number N -IsReadOnly $true; Set-Disk -Number N -IsOffline $true
   Success: Get-Disk shows IsOffline=True (tray may still show device)
Stage values: shell_com, volume_dismount, pnp_remove, disk_offline, all_failed

Notes:
- Steps 2+ require admin rights
- Ensure no process is using the volume before PnP removal
- If only disk_offline succeeds, hardware removal did not happen; unplug or use tray eject manually
- devcon requires WDK; pnputil requires Windows 10 1903+

---
## Safety
Offlining with pending writes can cause data loss. No guarantee of hardware‑level safe removal.

---
## Detection Logic
Match if any: InterfaceType=USB; MediaType has REMOVABLE/EXTERNAL; logical DriveType=2; PNPDeviceID contains USBSTOR/USB; else fallback to non‑system disks.

---
## Limitations
- Some USB‑SATA bridge chips appear as fixed disks
- External HDD/SSD enclosures often ignore Shell eject
- BitLocker not handled

---
## Disclaimer
For educational use only. Use at your own risk.

---
## Contribution
Issues and suggestions are welcome.

