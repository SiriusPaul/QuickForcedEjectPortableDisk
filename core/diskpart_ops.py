import subprocess
from typing import List


def _run_diskpart(lines: List[str]) -> str:
    script = "\n".join(lines) + "\n"
    proc = subprocess.run(["diskpart"], input=script, text=True, capture_output=True)
    if proc.returncode != 0:
        # diskpart 常把信息写在 stdout，stderr 可能为空
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

