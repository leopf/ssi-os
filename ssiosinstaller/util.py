from ssiosinstaller.context import ExecContext
import re

def is_intel_processor(lscpu_stdout: str):
    return lscpu_stdout.find("GenuineIntel") != -1

def is_amd_processor(lscpu_stdout: str):
    return lscpu_stdout.find("AuthenticAMD") != -1 or lscpu_stdout.find("AMDisbetter!") != -1

def find_memory_size(context: ExecContext):
    res = context.exec_no_err("grep MemTotal /proc/meminfo")
    size_in_kb = int(re.sub(r'[^0-9]', "", res["stdout"]), 10)
    return int(size_in_kb / 1000)