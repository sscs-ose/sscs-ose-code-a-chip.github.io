"""Exact-handle Windows Job Object ownership; no process-name or global OS changes."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import time

if os.name != "nt":
    raise RuntimeError("The local watchdog requires native Windows Job Object support")

import _winapi
import msvcrt

kernel = ctypes.WinDLL("kernel32", use_last_error=True)
ULONG_PTR = ctypes.c_size_t
SIZE_T = ctypes.c_size_t
LARGE_INTEGER = ctypes.c_longlong


class BasicLimit(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", LARGE_INTEGER), ("PerJobUserTimeLimit", LARGE_INTEGER),
        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", SIZE_T),
        ("MaximumWorkingSetSize", SIZE_T), ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ULONG_PTR), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD),
    ]


class IOCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", BasicLimit), ("IoInfo", IOCounters),
        ("ProcessMemoryLimit", SIZE_T), ("JobMemoryLimit", SIZE_T),
        ("PeakProcessMemoryUsed", SIZE_T), ("PeakJobMemoryUsed", SIZE_T),
    ]


class BasicAccounting(ctypes.Structure):
    _fields_ = [(name, LARGE_INTEGER) for name in (
        "TotalUserTime", "TotalKernelTime", "ThisPeriodTotalUserTime", "ThisPeriodTotalKernelTime")] + [
        ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
kernel.CreateJobObjectW.restype = wintypes.HANDLE
kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
kernel.SetInformationJobObject.restype = wintypes.BOOL
kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
kernel.AssignProcessToJobObject.restype = wintypes.BOOL
kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel.TerminateJobObject.restype = wintypes.BOOL
kernel.QueryInformationJobObject.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
kernel.QueryInformationJobObject.restype = wintypes.BOOL
kernel.ResumeThread.argtypes = [wintypes.HANDLE]
kernel.ResumeThread.restype = wintypes.DWORD
kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
kernel.IsProcessInJob.restype = wintypes.BOOL
kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
kernel.GetProcessTimes.restype = wintypes.BOOL
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.GetCurrentProcess.restype = wintypes.HANDLE


def checked(ok, message):
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error(), message)
    return ok


def creation_ticks(handle: int) -> int:
    created, exited, user, kern = (wintypes.FILETIME() for _ in range(4))
    checked(kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                   ctypes.byref(kern), ctypes.byref(user)), "Cannot identify owned process")
    return (created.dwHighDateTime << 32) | created.dwLowDateTime


def current_identity() -> dict:
    return {"pid": os.getpid(), "creation_filetime": creation_ticks(kernel.GetCurrentProcess())}


def open_identity(pid: int, expected_creation: int) -> int:
    handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)  # synchronize and query only
    checked(handle, "Cannot open supervisor process identity")
    if creation_ticks(handle) != expected_creation:
        _winapi.CloseHandle(handle)
        raise RuntimeError("PID was reused; it is not the recorded supervisor")
    return handle


def identity_is_alive(identity: dict) -> bool:
    handle = kernel.OpenProcess(0x00100000 | 0x1000, False, identity["pid"])
    if not handle:
        return False
    try:
        return creation_ticks(handle) == identity["creation_filetime"] and \
            _winapi.WaitForSingleObject(handle, 0) == _winapi.WAIT_TIMEOUT
    finally:
        _winapi.CloseHandle(handle)


class OwnedProcess:
    def __init__(self, process_handle, thread_handle, pid, tid):
        self.handle, self.thread = process_handle, thread_handle
        self.pid, self.tid = pid, tid
        self.creation_filetime = creation_ticks(process_handle)
        self.resumed = False
        self.closed = False

    @classmethod
    def suspended(cls, arguments: list[str], cwd: str, env: dict, output):
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESTDHANDLES
        with open(os.devnull, "rb") as null:
            output_handle = msvcrt.get_osfhandle(output.fileno())
            input_handle = msvcrt.get_osfhandle(null.fileno())
            handles = [input_handle, output_handle]
            previous = [os.get_handle_inheritable(h) for h in handles]
            try:
                for handle in handles:
                    os.set_handle_inheritable(handle, True)
                startup.hStdInput = input_handle
                startup.hStdOutput = output_handle
                startup.hStdError = output_handle
                startup.lpAttributeList = {"handle_list": handles}
                result = _winapi.CreateProcess(
                    arguments[0], subprocess.list2cmdline(arguments), None, None, True,
                    0x00000004 | 0x00000400 | 0x08000000, env, cwd, startup)
            finally:
                for handle, inheritable in zip(handles, previous):
                    os.set_handle_inheritable(handle, inheritable)
        return cls(*result)

    @property
    def identity(self):
        return {"pid": self.pid, "creation_filetime": self.creation_filetime}

    def resume(self):
        if self.resumed:
            raise RuntimeError("Owned process already resumed")
        previous = kernel.ResumeThread(self.thread)
        if previous == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error(), "Cannot resume owned suspended process")
        self.resumed = True
        _winapi.CloseHandle(self.thread)
        self.thread = None

    def poll(self):
        status = _winapi.WaitForSingleObject(self.handle, 0)
        return None if status == _winapi.WAIT_TIMEOUT else _winapi.GetExitCodeProcess(self.handle)

    def wait(self, seconds=None):
        milliseconds = _winapi.INFINITE if seconds is None else max(0, int(seconds * 1000))
        if _winapi.WaitForSingleObject(self.handle, milliseconds) == _winapi.WAIT_TIMEOUT:
            return None
        return _winapi.GetExitCodeProcess(self.handle)

    def terminate(self, code=124):
        if self.poll() is None:
            _winapi.TerminateProcess(self.handle, code)

    def close(self):
        if self.closed:
            return
        if self.thread is not None:
            _winapi.CloseHandle(self.thread)
            self.thread = None
        _winapi.CloseHandle(self.handle)
        self.closed = True


class OwnedJob:
    def __init__(self):
        self.handle = kernel.CreateJobObjectW(None, None)
        checked(self.handle, "Windows Job Objects are unavailable")
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # kill descendants when last owner closes
        try:
            checked(kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits),
                                                   ctypes.sizeof(limits)), "Cannot configure owned job")
        except BaseException:
            _winapi.CloseHandle(self.handle)
            raise
        self.closed = False

    def assign(self, process: OwnedProcess):
        if process.resumed:
            raise RuntimeError("Root process must be assigned before it can spawn descendants")
        checked(kernel.AssignProcessToJobObject(self.handle, process.handle),
                "Cannot isolate worker in owned Windows Job Object")
        member = wintypes.BOOL()
        checked(kernel.IsProcessInJob(process.handle, self.handle, ctypes.byref(member)),
                "Cannot verify owned job assignment")
        if not member.value:
            raise RuntimeError("Suspended root was not placed in the intended job")

    def accounting(self):
        record = BasicAccounting()
        checked(kernel.QueryInformationJobObject(self.handle, 1, ctypes.byref(record),
                                                 ctypes.sizeof(record), None), "Cannot query owned job")
        return {
            "total_processes": record.TotalProcesses, "active_processes": record.ActiveProcesses,
            "terminated_processes": record.TotalTerminatedProcesses,
        }

    def terminate(self, code=124):
        checked(kernel.TerminateJobObject(self.handle, code), "Cannot terminate only the owned job")

    def wait_empty(self, seconds=5):
        end = time.monotonic() + seconds
        while self.accounting()["active_processes"] and time.monotonic() < end:
            time.sleep(0.01)
        return self.accounting()["active_processes"] == 0

    def close(self):
        if not self.closed:
            _winapi.CloseHandle(self.handle)
            self.closed = True
