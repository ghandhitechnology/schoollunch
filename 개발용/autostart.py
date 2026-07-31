# -*- coding: utf-8 -*-
"""OS 시작 시 자동 실행 등록."""
import getpass
import os
import plistlib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "하태욱프로그램"
TASK_NAME = "하태욱프로그램"
MACOS_LAUNCH_AGENT_LABEL = "com.hataewook.program"
TASK_XML_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"


def _program_arguments() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--background"]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "main.py")
    return [sys.executable, main_py, "--background"]


def _macos_plist_path() -> str:
    launch_agents = os.path.expanduser("~/Library/LaunchAgents")
    os.makedirs(launch_agents, exist_ok=True)
    return os.path.join(launch_agents, f"{MACOS_LAUNCH_AGENT_LABEL}.plist")


def _macos_launchctl(*args: str) -> None:
    try:
        subprocess.run(["launchctl", *args], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _macos_enable() -> None:
    plist_path = _macos_plist_path()
    payload = {
        "Label": MACOS_LAUNCH_AGENT_LABEL,
        "ProgramArguments": _program_arguments(),
        "RunAtLoad": True,
        "KeepAlive": False,
        "WorkingDirectory": os.path.dirname(os.path.abspath(__file__)),
        "StandardOutPath": os.path.join(os.path.expanduser("~"), "Library", "Logs", "hataewook-program.log"),
        "StandardErrorPath": os.path.join(os.path.expanduser("~"), "Library", "Logs", "hataewook-program.err.log"),
    }
    with open(plist_path, "wb") as f:
        plistlib.dump(payload, f)
    uid = os.getuid()
    _macos_launchctl("bootout", f"gui/{uid}", plist_path)
    _macos_launchctl("bootstrap", f"gui/{uid}", plist_path)


def _macos_disable() -> None:
    plist_path = _macos_plist_path()
    uid = os.getuid()
    _macos_launchctl("bootout", f"gui/{uid}", plist_path)
    try:
        os.remove(plist_path)
    except FileNotFoundError:
        pass


def _windows_remove_registry_run() -> None:
    if sys.platform != "win32":
        return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, VALUE_NAME)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _windows_task_xml(command: str, arguments: str) -> str:
    ns = TASK_XML_NS
    ET.register_namespace("", ns)
    task = ET.Element(f"{{{ns}}}Task", attrib={"version": "1.4"})
    triggers = ET.SubElement(task, f"{{{ns}}}Triggers")
    logon = ET.SubElement(triggers, f"{{{ns}}}LogonTrigger")
    ET.SubElement(logon, f"{{{ns}}}Enabled").text = "true"
    ET.SubElement(logon, f"{{{ns}}}Delay").text = "PT30S"

    principals = ET.SubElement(task, f"{{{ns}}}Principals")
    principal = ET.SubElement(principals, f"{{{ns}}}Principal", attrib={"id": "Author"})
    ET.SubElement(principal, f"{{{ns}}}LogonType").text = "InteractiveToken"
    ET.SubElement(principal, f"{{{ns}}}RunLevel").text = "LeastPrivilege"
    ET.SubElement(principal, f"{{{ns}}}UserId").text = getpass.getuser()

    settings = ET.SubElement(task, f"{{{ns}}}Settings")
    ET.SubElement(settings, f"{{{ns}}}MultipleInstancesPolicy").text = "IgnoreNew"
    ET.SubElement(settings, f"{{{ns}}}DisallowStartIfOnBatteries").text = "false"
    ET.SubElement(settings, f"{{{ns}}}StopIfGoingOnBatteries").text = "false"
    ET.SubElement(settings, f"{{{ns}}}AllowHardTerminate").text = "true"
    ET.SubElement(settings, f"{{{ns}}}StartWhenAvailable").text = "true"
    ET.SubElement(settings, f"{{{ns}}}RunOnlyIfNetworkAvailable").text = "true"
    ET.SubElement(settings, f"{{{ns}}}AllowStartOnDemand").text = "true"
    ET.SubElement(settings, f"{{{ns}}}Enabled").text = "true"
    ET.SubElement(settings, f"{{{ns}}}Hidden").text = "false"
    ET.SubElement(settings, f"{{{ns}}}RunOnlyIfIdle").text = "false"
    ET.SubElement(settings, f"{{{ns}}}WakeToRun").text = "false"
    ET.SubElement(settings, f"{{{ns}}}ExecutionTimeLimit").text = "PT0S"
    ET.SubElement(settings, f"{{{ns}}}Priority").text = "7"

    actions = ET.SubElement(task, f"{{{ns}}}Actions", attrib={"Context": "Author"})
    exec_action = ET.SubElement(actions, f"{{{ns}}}Exec")
    ET.SubElement(exec_action, f"{{{ns}}}Command").text = command
    if arguments:
        ET.SubElement(exec_action, f"{{{ns}}}Arguments").text = arguments

    return '<?xml version="1.0" encoding="UTF-16"?>\n' + ET.tostring(task, encoding="unicode")


def _windows_enable() -> None:
    args = _program_arguments()
    command = args[0]
    arguments = " ".join(f'"{a}"' if " " in a else a for a in args[1:])
    xml_text = _windows_task_xml(command, arguments)
    fd, xml_path = tempfile.mkstemp(suffix=".xml")
    try:
        with os.fdopen(fd, "w", encoding="utf-16") as f:
            f.write(xml_text)
        subprocess.run(
            ["schtasks", "/Create", "/TN", TASK_NAME, "/XML", xml_path, "/F"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        try:
            os.remove(xml_path)
        except OSError:
            pass
    _windows_remove_registry_run()


def _windows_disable() -> None:
    subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _windows_remove_registry_run()


def enable() -> None:
    if sys.platform == "darwin":
        _macos_enable()
        return
    if sys.platform != "win32":
        return
    _windows_enable()


def disable() -> None:
    if sys.platform == "darwin":
        _macos_disable()
        return
    if sys.platform != "win32":
        return
    _windows_disable()


def apply(enabled: bool) -> None:
    enable() if enabled else disable()
