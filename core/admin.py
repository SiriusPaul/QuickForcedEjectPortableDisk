import sys
import ctypes
from typing import Optional


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()  # type: ignore[attr-defined]
    except Exception:
        return False


def relaunch_as_admin(extra_args: Optional[list] = None):
    # 重启自身并请求管理员权限
    params = ' '.join([f'"{a}"' for a in sys.argv])
    if extra_args:
        params += ' ' + ' '.join(extra_args)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)


def ensure_admin() -> bool:
    """确保当前进程拥有管理员权限。
    返回 True 表示已是管理员可继续执行；
    返回 False 表示已发起提权重启，当前进程应立即退出。
    """
    if is_admin():
        return True
    if "--elevated" in sys.argv:
        # 已尝试提权仍失败，直接返回 True 防止死循环（可能用户拒绝）
        return True
    relaunch_as_admin(["--elevated"])
    return False

