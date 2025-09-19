import subprocess
import shutil
from typing import List, Dict, Any
from . import diskpart_ops  # 新增：用于兜底离线磁盘

# 统一的子进程隐藏窗口配置（Windows）
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
    if subprocess._mswindows:  # type: ignore[attr-defined]
        creationflags |= _CREATE_NO_WINDOW
    return subprocess.run(cmd, startupinfo=startupinfo, creationflags=creationflags, **kwargs)


_PS_BASE = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]


def _run_ps(script: str) -> subprocess.CompletedProcess:
    return _run_hidden(_PS_BASE + [script], capture_output=True, text=True)

# ---------------- 基础检测 ----------------

def _letter_exists(letter: str) -> bool:
    script = f"if(Test-Path {letter}:\\){{'1'}} else {{'0'}}"
    p = _run_ps(script)
    return '1' in p.stdout

# ---------------- 策略 1：Shell COM ----------------

def _shell_com_eject(letter: str) -> bool:
    script = (
        f"$app=New-Object -ComObject Shell.Application;"
        f"$ns=$app.NameSpace(17);"
        f"$target='{letter}:';"
        "foreach($i in $ns.Items()){ if($i.Path -eq $target){ try { $i.InvokeVerb('Eject'); Start-Sleep -Milliseconds 400 } catch {} } }"
    )
    _run_ps(script)
    # 仅判断盘符是否消失（部分设备不会马上消失）
    return not _letter_exists(letter)

# ---------------- 策略 2：卷卸载 (Win32_Volume) ----------------

def _volume_dismount(letter: str) -> bool:
    script = (
        f"$vol=Get-CimInstance Win32_Volume -Filter \"DriveLetter='{letter}:'\" -ErrorAction SilentlyContinue;"
        "if($vol){ try { Invoke-CimMethod -InputObject $vol -MethodName Dismount -Arguments @{Force=$false;Permanent=$false} | Out-Null; Start-Sleep -Milliseconds 300 } catch {} }"
    )
    _run_ps(script)
    return not _letter_exists(letter)

# ---------------- 新增：获取 PNPDeviceID ----------------

def _get_pnp_id(disk_index: int) -> str:
    script = (
        f"$d=Get-CimInstance Win32_DiskDrive -Filter \"Index={disk_index}\" -ErrorAction SilentlyContinue;"
        "$d.PNPDeviceID"
    )
    p = _run_ps(script)
    return p.stdout.strip().splitlines()[0].strip() if p.stdout.strip() else ''

# ---------------- 新增：检测 Invoke-PnpDeviceAction 支持 ----------------

def _has_invoke_pnp() -> bool:
    script = "if(Get-Command Invoke-PnpDeviceAction -ErrorAction SilentlyContinue){'YES'} else {'NO'}"
    p = _run_ps(script)
    return 'YES' in p.stdout

# ---------------- 策略 4（重排到 3）：PnP 设备移除（多回退） ----------------

def _pnp_remove(disk_index: int, details: List[str]) -> bool:
    pnp_id = _get_pnp_id(disk_index)
    if not pnp_id:
        details.append("未获取��� PNPDeviceID，跳过 PnP 移除")
        return False
    # 转义反斜杠
    esc = pnp_id.replace('\\', '\\\\').replace('"', '\"')
    success = False

    # 1) Invoke-PnpDeviceAction
    if _has_invoke_pnp():
        script = (
            f"$id=\"{esc}\"; $dev=Get-PnpDevice -InstanceId $id -ErrorAction SilentlyContinue;"
            "if($dev){ try { Invoke-PnpDeviceAction -InstanceId $id -Action 9 -ErrorAction SilentlyContinue | Out-Null; Start-Sleep -Milliseconds 500 } catch {} }"
            f"$again=Get-PnpDevice -InstanceId \"{esc}\" -ErrorAction SilentlyContinue; if($again){{'PRESENT'}} else {{'REMOVED'}}"
        )
        r = _run_ps(script)
        if 'REMOVED' in r.stdout:
            details.append(f"PnP 移除成功 (Invoke-PnpDeviceAction) => {pnp_id}")
            return True
        else:
            details.append(f"Invoke-PnpDeviceAction 未移除设备 (stdout={r.stdout.strip()} stderr={r.stderr.strip()})")
    else:
        details.append("系统不支持 Invoke-PnpDeviceAction，尝试其他方式")

    # 2) pnputil /remove-device （Windows 10 1903+）
    if shutil.which('pnputil'):
        cmd = ["pnputil", "/remove-device", pnp_id]
        r = _run_hidden(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            # 再检测是否仍存在
            verify = _run_ps(f"if(Get-CimInstance Win32_DiskDrive | Where-Object {{$_.PNPDeviceID -eq '{esc}'}}){{'PRESENT'}} else {{'REMOVED'}}")
            if 'REMOVED' in verify.stdout:
                details.append(f"PnP 移除成功 (pnputil) => {pnp_id}")
                return True
            else:
                details.append(f"pnputil 执行后仍检测到设备 (out={r.stdout.strip()})")
        else:
            details.append(f"pnputil 移除失败 code={r.returncode} out={r.stdout.strip()} err={r.stderr.strip()}")
    else:
        details.append("未找到 pnputil，跳过 pnputil 阶段")

    # 3) devcon remove （可选 WDK 工具）
    if shutil.which('devcon'):
        r = _run_hidden(["devcon", "remove", pnp_id], capture_output=True, text=True)
        if r.returncode == 0:
            verify = _run_ps(f"if(Get-CimInstance Win32_DiskDrive | Where-Object {{$_.PNPDeviceID -eq '{esc}'}}){{'PRESENT'}} else {{'REMOVED'}}")
            if 'REMOVED' in verify.stdout:
                details.append(f"PnP 移除成功 (devcon) => {pnp_id}")
                return True
            else:
                details.append("devcon 执行后仍存在设备")
        else:
            details.append(f"devcon 失败 code={r.returncode} out={r.stdout.strip()} err={r.stderr.strip()}")
    else:
        details.append("未找到 devcon，跳过 devcon 阶段")

    details.append("PnP 移除阶段全部失败")
    return success

# ---------------- 统一对外接口 ----------------

# 新增：兜底离线函数

def _disk_offline(disk_index: int) -> bool:
    try:
        diskpart_ops.offline_disk(disk_index)
        return True
    except Exception:
        return False


def eject_disk(disk_index: int, letters: List[str]) -> Dict[str, Any]:
    """多策略弹出/卸载。返回 {success, stage, details[]} 顺序: Shell -> 卷卸载 -> PnP 移除 -> 离线"""
    details: List[str] = []

    # 1. Shell COM
    shell_any = False
    for lt in letters:
        if _shell_com_eject(lt):
            details.append(f"ShellCOM 弹出成功: {lt}:")
            shell_any = True
        else:
            details.append(f"ShellCOM 未生效: {lt}:")
    if shell_any:
        return {"success": True, "stage": "shell_com", "details": details}

    # 2. 卷卸载
    vol_any = False
    for lt in letters:
        if _volume_dismount(lt):
            details.append(f"卷卸载成功: {lt}:")
            vol_any = True
        else:
            details.append(f"卷卸载未确认: {lt}:")
    if vol_any:
        return {"success": True, "stage": "volume_dismount", "details": details}

    # 3. PnP 移除
    if _pnp_remove(disk_index, details):
        return {"success": True, "stage": "pnp_remove", "details": details}

    # 4. 磁盘离线兜底
    if _disk_offline(disk_index):
        details.append("磁盘已离线")
        return {"success": True, "stage": "disk_offline", "details": details}
    else:
        details.append("磁盘离线失败或仍在线")

    return {"success": False, "stage": "all_failed", "details": details}

# 兼容旧接口（仅做简单调用，不再推荐）

def eject_letters(letters: List[str]) -> bool:
    # 旧逻辑：仅尝试 Shell COM
    ok = False
    for lt in letters:
        if _shell_com_eject(lt):
            ok = True
    return ok
