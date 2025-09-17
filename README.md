# QuickForcedEjectPortableDisk

English | 简体中文

---
## Overview / 项目简介
A lightweight Windows GUI utility (Python + PowerShell + diskpart) to enumerate external/removable disks, run an Offline→Online cycle to release abnormal locks, and attempt logical eject.
一个基于 Python + PowerShell + diskpart 的 Windows 图形工具，用于枚举外接/可移动磁盘，执行“脱机→联机”释放异常占用，并尝试逻辑弹出。

---
## Features (Current) / 当前功能
- External disk heuristic detection (USB / Removable / External / USBSTOR / DriveType=2)
- Offline→Online (diskpart)
- Multi‑strategy eject (Shell COM → Win32_Volume Dismount → PnP Remove (Invoke‑Pnp / pnputil / devcon) → Disk offline fallback)
- Debug log (core/disk_query_debug.log)
- Auto elevation (UAC)
- 外接磁盘识别（USB / Removable / External / USBSTOR / DriveType=2）
- 脱机→联机（diskpart）
- 多策略弹出（Shell COM → 卷卸载 → PnP 移除(Invoke‑Pnp / pnputil / devcon) → 离线兜底）
- 调试日志（core/disk_query_debug.log）
- 自动提权（UAC）

---
## Environment / 运行环境
Windows 10/11 · Python 3.10+ · Admin rights for disk operations
适用 Windows 10/11 · Python 3.10+ · 脱机/联机需管理员权限

---
## Install & Run / 安装与运行
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
If UAC prompts, allow elevation.
若出现 UAC 提示请允许提权。

---
## Usage / 使用说明
1. Refresh disk list ("刷新磁盘") (optional if auto-loaded).
2. Select target disk.
3. Click "脱机->联机" to release abnormal locks.
4. Click "多策略弹出" to perform multi‑strategy eject.
5. Check log panel.
1. 点“刷新磁盘”（初次已加载可选）
2. 选中目标磁盘
3. 点“脱机->联机”释放异常占用
4. 点“多策略弹出”执行多层弹出策略
5. 查看日志面板反馈

---
## Multi‑strategy Eject (Implementation) / 多策略弹出实现说明
English Order:
1. Shell COM Verb
   Command: Shell.Application NameSpace(17).ParseName('E:').InvokeVerb('Eject')
   Success: drive letter disappears (Test-Path E:\ returns false)
2. Volume Dismount (Win32_Volume)
   PowerShell: Get-CimInstance Win32_Volume -Filter "DriveLetter='E:'" | Invoke-CimMethod -MethodName Dismount -Arguments @{ Force=$false; Permanent=$false }
   Success: letter disappears
3. PnP Removal (hardware level)
   a) Invoke-PnpDeviceAction -Action 9 (if available)
   b) pnputil /remove-device <PNPDeviceID>
   c) devcon remove <PNPDeviceID> (if devcon present)
   Success: Win32_DiskDrive no longer returns that PNPDeviceID
4. Disk Offline Fallback
   Set-Disk -Number N -IsReadOnly $true; Set-Disk -Number N -IsOffline $true
   Success: Get-Disk shows IsOffline=True (tray may still show device)
Returned stage values: shell_com, volume_dismount, pnp_remove, disk_offline, all_failed

中文执行顺序：
1. Shell COM 动作
   命令：Shell.Application NameSpace(17).ParseName('E:').InvokeVerb('Eject')
   成功：盘符消失 (Test-Path E:\ 为 false)
2. 卷卸载（Win32_Volume）
   PowerShell：Get-CimInstance Win32_Volume -Filter "DriveLetter='E:'" | Invoke-CimMethod Dismount -Arguments @{ Force=$false; Permanent=$false }
   成功：盘符消失
3. PnP 设备移除（硬件层）
   a) Invoke-PnpDeviceAction -Action 9（若支持）
   b) pnputil /remove-device <PNPDeviceID>
   c) devcon remove <PNPDeviceID>（若已放置 devcon）
   成功：Win32_DiskDrive 不再包含该 PNPDeviceID
4. 磁盘离线兜底
   Set-Disk -Number N -IsReadOnly $true; Set-Disk -Number N -IsOffline $true
   成功：Get-Disk 显示 IsOffline=True（托盘可能仍显示）
阶段返回：shell_com / volume_dismount / pnp_remove / disk_offline / all_failed

Notes / 说明：
- Admin rights required for steps 2+ / 第 2 步及之后需管理员权限
- PnP 移除前应确保无进程占用（后续可加占用检测）
- 若仅到 disk_offline，说明未能硬件移除，可物理拔出或托盘手动安全移除
- devcon 需自行安装（WDK 工具），pnputil 需 Win10 1903+

---
## Safety / 安全
Offline can cause data loss if writes are pending.
脱机可能造成未完成写入丢失。
Tool does not guarantee hardware safe removal.
本工具不保证硬件级安全移除。

---
## Detection Logic / 识别逻辑
Match if any: InterfaceType=USB, MediaType has REMOVABLE/EXTERNAL, DriveType=2 logical volume, PNPDeviceID contains USBSTOR/USB; else fallback to non‑system disks.
判定条件任一满足：InterfaceType=USB；MediaType 含 REMOVABLE/EXTERNAL；逻辑卷 DriveType=2；PNPDeviceID 含 USBSTOR/USB；否则回退显示非系统盘。

---
## Limitations / 已知限制
- Some USB-SATA bridges appear as fixed disks
- Shell eject often ineffective for external HDD/SSD
- BitLocker not handled
- 某些桥接芯片被识别为固定盘
- 外置硬盘壳通常无法 Shell 弹出
- 不处理 BitLocker 状态

---
## Disclaimer / 免责声明
Use at your own risk; educational only.
仅供学习演示，风险自负。

---
## Contribution / 参与
Issues & suggestions welcome.
欢迎提交 Issue 与建议。
