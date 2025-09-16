import subprocess
from typing import List

_PS = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]


def _run_ps(script: str) -> bool:
    proc = subprocess.run(_PS + [script], capture_output=True, text=True)
    return proc.returncode == 0


def shell_eject(letter: str) -> bool:
    # 使用 COM Shell 尝试弹出
    script = (
        f"$app=New-Object -ComObject Shell.Application;"
        f"$ns=$app.NameSpace(17);"
        f"$item=$ns.ParseName('{letter}:');"
        f"if($item){{$item.InvokeVerb('Eject')}}"
    )
    return _run_ps(script)


def eject_letters(letters: List[str]) -> bool:
    ok = False
    for lt in letters:
        if shell_eject(lt):
            ok = True
    return ok

