import json
import subprocess
import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from datetime import datetime

# Windows 隐藏子进程窗口配置
try:
    from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW  # type: ignore
    _HAS_STARTUPINFO = True
except Exception:  # pragma: no cover
    _HAS_STARTUPINFO = False

_CREATE_NO_WINDOW = 0x08000000


def _run_hidden(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    startupinfo = None
    creationflags = kwargs.pop('creationflags', 0)
    if _HAS_STARTUPINFO:
        startupinfo = STARTUPINFO()
        startupinfo.dwFlags |= STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
        startupinfo.wShowWindow = 0  # SW_HIDE
    if subprocess._mswindows:  # type: ignore[attr-defined]
        creationflags |= _CREATE_NO_WINDOW
    return subprocess.run(cmd, startupinfo=startupinfo, creationflags=creationflags, **kwargs)

# 固定 PowerShell 路径并隐藏窗口
_PS_EXE = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), r'System32\WindowsPowerShell\v1.0\powershell.exe')
_POWERSHELL = [_PS_EXE, '-NoProfile', '-NonInteractive', '-NoLogo', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-Command']

@dataclass
class DiskInfo:
    index: int
    model: str
    size: int  # bytes
    letters: List[str]
    is_external: bool  # 新增：是否判定为外接/可移动

_cache: List[DiskInfo] = []

_DEBUG_LOG_PATH = os.path.join(os.path.dirname(__file__), 'disk_query_debug.log')

# ---------------- Debug assist ----------------

def _debug_enabled() -> bool:
    return bool(os.environ.get('QFE_DEBUG'))

def _dbg(msg: str):
    if not _debug_enabled():
        return
    line = f"[disk_query][{datetime.now().strftime('%H:%M:%S.%f')}] {msg}"
    try:
        print(line)
    except Exception:
        pass
    try:
        with open(_DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

# ---------------- PowerShell 调用 ----------------

def _run_ps_json(script: str):
    proc = _run_hidden(_POWERSHELL + [script], capture_output=True, text=True)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        raise RuntimeError(stderr or stdout or 'PowerShell 执行失败')
    raw = proc.stdout.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _dbg(f"JSON 解析失败 script={script[:60]}")
        return []
    if isinstance(data, dict):
        return [data]
    return data

# ---------------- 批量数据获取 ----------------

def _collect_disks() -> List[Dict]:
    script = (
        "Get-CimInstance Win32_DiskDrive | Select-Object Index,Model,Size,InterfaceType,MediaType,PNPDeviceID | ConvertTo-Json -Depth 3"
    )
    disks = _run_ps_json(script)
    _dbg(f"Raw disks count={len(disks)}")
    return disks

def _collect_partitions() -> List[Dict]:
    # 可能在旧系统上 Get-Partition 不可用，失败后返回空数组
    script = (
        "Get-Partition 2>$null | Where-Object {$_.DriveLetter} | Select-Object DiskNumber,DriveLetter | ConvertTo-Json"
    )
    try:
        parts = _run_ps_json(script)
        _dbg(f"Partitions with letters count={len(parts)}")
        return parts
    except Exception as e:
        _dbg(f"Get-Partition failed: {e}")
        return []

def _collect_logical_drive_types() -> Dict[str, int]:
    script = "Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,DriveType | ConvertTo-Json"
    mapping: Dict[str, int] = {}
    for d in _run_ps_json(script):
        dev = (d.get('DeviceID') or '').replace(':', '')
        dt = d.get('DriveType')
        if dev and dt is not None:
            mapping[dev] = int(dt)
    _dbg(f"Logical drive type map={mapping}")
    return mapping

# ---------------- 主查询逻辑 ----------------

def query_disks(refresh: bool = True, show_all: bool = False) -> List[DiskInfo]:
    global _cache
    if not refresh and _cache:
        return _cache

    try:
        disks_raw = _collect_disks()
    except Exception as e:
        _dbg(f"_collect_disks error: {e}")
        return []

    parts_raw = _collect_partitions()
    logical_types = _collect_logical_drive_types()
    removable_letters = {l for l, t in logical_types.items() if t == 2}

    # 建立 diskNumber -> letters 映射
    disk_letter_map: Dict[int, List[str]] = {}
    for p in parts_raw:
        dn = p.get('DiskNumber')
        dl = p.get('DriveLetter')
        if dn is None or not dl:
            continue
        disk_letter_map.setdefault(int(dn), []).append(dl)
    _dbg(f"disk_letter_map={disk_letter_map}")

    # 有些系统上 Get-Partition 失败时，尝试降级一次性关联所有分区 (可选)
    if not disk_letter_map:
        _dbg("Fallback to per-disk association (slow path)")
        disk_letter_map = _fallback_association(disks_raw)
        _dbg(f"fallback disk_letter_map={disk_letter_map}")

    result: List[DiskInfo] = []
    for d in disks_raw:
        index = d.get('Index')
        if index is None:
            continue
        idx = int(index)
        letters = disk_letter_map.get(idx, [])
        interface = (d.get('InterfaceType') or '').upper()
        media = (d.get('MediaType') or '').upper()
        pnp = (d.get('PNPDeviceID') or '').upper()
        has_removable_letter = any(l in removable_letters for l in letters)
        pnp_usb = 'USBSTOR' in pnp or ('USB' in pnp)
        media_external = 'EXTERNAL' in media
        is_external = (("USB" in interface) or ("REMOVABLE" in media) or has_removable_letter or pnp_usb or media_external)
        cond = is_external
        _dbg(
            f"Disk idx={idx} interface={interface} media={media} letters={letters} has_removable_letter={has_removable_letter} pnp_usb={pnp_usb} media_external={media_external} is_external={is_external}"
        )
        if show_all:
            result.append(DiskInfo(index=idx, model=d.get('Model') or '', size=int(d.get('Size') or 0), letters=letters, is_external=is_external))
        else:
            if cond:
                result.append(DiskInfo(index=idx, model=d.get('Model') or '', size=int(d.get('Size') or 0), letters=letters, is_external=is_external))

    # 仅在非 show_all 且结果为空时，做一次回退（排除典型系统盘）
    if not show_all and not result:
        _dbg("No disk matched filters, fallback to showing all disks with letters (excluding system-like)")
        for d in disks_raw:
            idx = d.get('Index')
            if idx is None:
                continue
            letters = disk_letter_map.get(int(idx), [])
            if not letters:
                continue
            # 简单排除：仅 C 或 C,D 的典型系统盘组合
            if letters == ['C'] or (letters == ['C', 'D'] and len(letters) <= 2):
                continue
            # 标注 is_external=False（回退视为内置）
            result.append(DiskInfo(index=int(idx), model=d.get('Model') or '', size=int(d.get('Size') or 0), letters=letters, is_external=False))
        _dbg(f"Fallback result count={len(result)}")

    _cache = result
    _dbg(f"Final visible disks count={len(result)} -> {result}")
    return result

# ---------------- 回退路径：逐磁盘关联（旧逻辑整合） ----------------

def _fallback_association(disks_raw: List[Dict]) -> Dict[int, List[str]]:
    mapping: Dict[int, List[str]] = {}
    for d in disks_raw:
        idx = d.get('Index')
        if idx is None:
            continue
        letters = _query_letters_single(int(idx))
        if letters:
            mapping[int(idx)] = letters
    return mapping


def _query_letters_single(index: int) -> List[str]:
    script_assoc = (
        f"$d=Get-CimInstance Win32_DiskDrive -Filter \"Index={index}\";"
        "$parts=$d|Get-CimAssociatedInstance -Association Win32_DiskDriveToDiskPartition;"
        "$letters=@();foreach($p in $parts){$lds=$p|Get-CimAssociatedInstance -Association Win32_LogicalDiskToPartition;foreach($l in $lds){$letters+=$l.DeviceID}};"
        "$letters|ConvertTo-Json"
    )
    try:
        data = _run_ps_json(script_assoc)
        letters: List[str] = []
        for item in data:
            if isinstance(item, str):
                letters.append(item.replace(':', ''))
            elif isinstance(item, dict):
                # 不会出现这种结构，防御
                pass
        # 去重
        return list(dict.fromkeys([l.replace(':', '') for l in letters]))
    except Exception as e:
        _dbg(f"_query_letters_single fail idx={index}: {e}")
        return []

# ---------------- 查询缓存访问 ----------------

def find_disk_by_index(idx: int) -> Optional[DiskInfo]:
    for d in _cache:
        if d.index == idx:
            return d
    return None
