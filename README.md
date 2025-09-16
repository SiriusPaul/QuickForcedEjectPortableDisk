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
- Basic Shell COM eject attempt
- Debug log (core/disk_query_debug.log)
- Auto elevation (UAC)
- 启发式外接磁盘识别（USB / Removable / External / USBSTOR / DriveType=2）
- 脱机→联机（diskpart）
- 基础 Shell COM 弹出尝试
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
1. Refresh disk list ("刷新磁盘").
2. Select target disk.
3. Click "脱机->联机" to release abnormal locks.
4. Click "弹出" to attempt eject.
5. Check log panel.
1. 点“刷新磁盘”
2. 选中磁盘
3. 点“脱机->联机”释放占用
4. 点“弹出”尝试逻辑弹出
5. 查看日志

---
## Safety / 安全
Offline can cause data loss if writes are pending.
脱机可能造成未完成写入丢失。
Tool does not guarantee hardware safe removal.
本工具不��证硬件级安全移除。

---
## Directory / 目录
```
app.py
core/ admin.py disk_query.py diskpart_ops.py eject.py disk_query_debug.log
gui/  main_window.py
utils/ (reserved)
```

---
## Detection Logic / 识别逻辑
English: Match if any of: InterfaceType=USB, MediaType has REMOVABLE/EXTERNAL, any logical drive DriveType=2, PNPDeviceID has USBSTOR/USB. Fallback: show non-system disks.
中文：任一满足：InterfaceType=USB；MediaType 含 REMOVABLE/EXTERNAL；逻辑卷 DriveType=2；PNPDeviceID 含 USBSTOR/USB。若均不匹配则回退显示非系统盘。

---
## Roadmap / 计划
1. Multi-strategy eject (Volume Dismount / Set-Disk / PnP) · 多策略弹出
2. Occupancy detection (psutil / handle.exe) · 占用检测
3. Optional force process termination · 进程强制结束（高风险）
4. UI enhancements (icons/tags) · 界面增强
5. Log export · 日志导出
6. Cross-platform (Linux/macOS) · 跨平台支持

---
## Limitations / 已知限制
- Some USB-SATA bridges appear as fixed disks
- Shell eject often ineffective for external HDD/SSD
- BitLocker states unsupported
- 某些 USB-SATA 转接被识别为固定盘
- 外置硬盘壳常无法通过 Shell 弹出
- 不处理 BitLocker 状态

---
## Disclaimer / 免责声明
Use at your own risk; educational only.
仅供学习演示，风险自负。

---
## Contribution / 参与
Issues & suggestions welcome.
欢迎提交 Issue 与建议。
