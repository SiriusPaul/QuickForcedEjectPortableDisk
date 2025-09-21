# QuickForcedEjectPortableDisk

[English](README.en.md) | 简体中文

---
## 背景
使用“安全删除硬件并弹出媒体”时，Windows 可能会提示“设备当前正在使用中”，即使没有打开任何文件。这可能是由于后台进程或系统服务对驱动器持有锁定，阻止安全移除。固然可以通过事件查看器来查找占用磁盘的应用，但是如果是系统级别的进程，盲目中止可能会导致系统崩溃。一个简单的解决方案是对硬盘执行“脱机→联机”操作，释放异常占用。但是对于 Windows 10/11 家庭版用户，无法使用“磁盘”进行脱机操作，因此需要借助 diskpart 命令行工具，较为不便，本工具旨在简化这些步骤。

---
## 项目简介
一个基于 Python + PowerShell + diskpart 的 Windows 图形工具，用于枚举外接/可移动磁盘，执行“脱机→联机”释放异常占用，并尝试逻辑弹出。

---
## 当前功能
- 外接磁盘识别（USB / Removable / External / USBSTOR / DriveType=2）
- 脱机→联机（diskpart）
- 多策略弹出（Shell COM → 卷卸载 → PnP 移除(Invoke‑Pnp / pnputil / devcon) → 离线兜底）
- 调试日志（core/disk_query_debug.log）
- 自动提权（UAC）

---
## 运行环境
适用 Windows 10/11 · Python 3.10+ · 脱机/联机需管理员权限

---
## 安装与运行
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
若出现 UAC 提示请允许提权。

---
## 使用说明
1. 点“刷新磁盘”（初次已加载可选）
2. 选中目标磁盘
3. 点“脱机->联机”释放异常占用
4. 点“多策略弹出”执行多层弹出策略
5. 查看日志面板反馈

---
## 多策略弹出实现说明
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

说明：
- 第 2 步及之后需管理员权限
- PnP 移除前应确保无进程占用（后续可加占用检测）
- 若仅到 disk_offline，说明未能硬件移除，可物理拔出或托盘手动安全移除
- devcon 需自行安装（WDK 工具），pnputil 需 Win10 1903+

---
## 安全
脱机可能造成未完成写入丢失。
本工具不保证硬件级安全移除。

---
## 识别逻辑
判定条件任一满足：InterfaceType=USB；MediaType 含 REMOVABLE/EXTERNAL；逻辑卷 DriveType=2；PNPDeviceID 含 USBSTOR/USB；否则回退显示非系统盘。

---
## 已知限制
- 某些桥接芯片被识别为固定盘
- 外置硬盘壳通常无法 Shell 弹出
- 不处理 BitLocker 状态

---
## 免责声明
仅供学习演示，风险自负。

---
## 参与
欢迎提交 Issue 与建议。
