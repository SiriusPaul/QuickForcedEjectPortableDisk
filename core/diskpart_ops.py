import subprocess
from typing import List

# Windows 隐藏控制台标志
try:
    from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW  # type: ignore
    _HAS_STARTUPINFO = True
except Exception:  # pragma: no cover
    _HAS_STARTUPINFO = False

_CREATE_NO_WINDOW = 0x08000000  # Windows 常量，其他平台忽略


def _run_diskpart(lines: List[str]) -> str:
    script = "\n".join(lines) + "\n"
    # --- 隐藏窗口设置 ---
    startupinfo = None
    creationflags = 0
    if _HAS_STARTUPINFO:
        startupinfo = STARTUPINFO()
        startupinfo.dwFlags |= STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
    # 仅在 Windows 使用 CREATE_NO_WINDOW
    if subprocess._mswindows:  # type: ignore[attr-defined]
        creationflags |= _CREATE_NO_WINDOW

    proc = subprocess.run(
        ["diskpart"],
        input=script,
        text=True,
        capture_output=True,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout or proc.stderr or "diskpart 执行失败")
    return proc.stdout


def offline_disk(index: int) -> str:
    return _run_diskpart([
        f"select disk {index}",
        "offline disk"
    ])


def online_disk(index: int) -> str:
    return _run_diskpart([
        f"select disk {index}",
        "online disk"
    ])


def offline_online(index: int) -> str:
    out1 = offline_disk(index)
    out2 = online_disk(index)
    return out1 + "\n" + out2
