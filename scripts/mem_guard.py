"""进程内内存看门狗（2026-08-31）。

为什么不用 RLIMIT：macOS 13 上实测 setrlimit(RLIMIT_AS/RLIMIT_DATA) 直接报
`ValueError: current limit exceeds maximum limit`，`ulimit -v/-d` 也报
`cannot modify limit: Invalid argument` —— 内核不提供按进程虚拟内存硬上限，
6GB bytearray 照样分配成功。所以只剩这一条路：采样峰值 RSS，越线立刻 SIGKILL 自己。
让整机不被拖死（不触发长按电源键）比让这次解析跑完更重要。
"""
import os, resource, signal, sys, threading, time

GB_SAFE_NOTE = "改走 cad_scan.sh 低内存路径（只解文字/图层/块名）"


def peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0


def start(cap_mb, name: str = "cad内存闸", interval: float = 0.08):
    if not cap_mb or cap_mb <= 0:
        return None
    def loop():
        while True:
            time.sleep(interval)
            p = peak_mb()
            if p > cap_mb:
                sys.stderr.write(
                    "[%s] 峰值内存 %.0fMB 已超上限 %dMB → 主动终止，防整机卡死。%s\n"
                    % (name, p, cap_mb, GB_SAFE_NOTE))
                sys.stderr.flush()
                os.kill(os.getpid(), signal.SIGKILL)
    t = threading.Thread(target=loop, daemon=True, name=name)
    t.start()
    return t
