# -*- coding: utf-8 -*-
"""Checksum-verified Windows updater using GitHub Releases."""
import hashlib
import os
from pathlib import Path
import string
import subprocess
import sys
import time
from urllib.parse import urlparse

import requests

import config
from version import APP_VERSION

REPOSITORY = "ghandhitechnology/schoollunch"
RELEASE_API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
EXE_ASSET_NAME = "hataewook-program-windows.exe"
CHECKSUM_ASSET_NAME = f"{EXE_ASSET_NAME}.sha256"
CHECK_INTERVAL_SEC = 6 * 60 * 60
MAX_DOWNLOAD_BYTES = 150 * 1024 * 1024
REQUEST_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": f"schoollunch-updater/{APP_VERSION}",
    "X-GitHub-Api-Version": "2022-11-28",
}

_REPLACE_SCRIPT = r'''param(
    [Parameter(Mandatory=$true)][int]$ParentProcessId,
    [Parameter(Mandatory=$true)][string]$CurrentExe,
    [Parameter(Mandatory=$true)][string]$NewExe,
    [Parameter(Mandatory=$true)][ValidateSet("default", "background")][string]$LaunchMode
)
$ErrorActionPreference = "Stop"
try {
    Wait-Process -Id $ParentProcessId -Timeout 90 -ErrorAction SilentlyContinue
} catch { }

$backup = "$CurrentExe.old"
$deadline = (Get-Date).AddMinutes(3)
$swapped = $false
while ((Get-Date) -lt $deadline) {
    $oldMoved = $false
    try {
        if (Test-Path -LiteralPath $backup) {
            Remove-Item -LiteralPath $backup -Force
        }
        Move-Item -LiteralPath $CurrentExe -Destination $backup -Force
        $oldMoved = $true
        Move-Item -LiteralPath $NewExe -Destination $CurrentExe -Force
        $swapped = $true
        break
    } catch {
        if ($oldMoved -and -not (Test-Path -LiteralPath $CurrentExe) -and (Test-Path -LiteralPath $backup)) {
            Move-Item -LiteralPath $backup -Destination $CurrentExe -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }
}

if (-not $swapped) {
    exit 1
}

if ($LaunchMode -eq "background") {
    Start-Process -FilePath $CurrentExe -ArgumentList "--background"
} else {
    Start-Process -FilePath $CurrentExe
}
Start-Sleep -Seconds 3
Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
'''


def _parse_version(value):
    value = value.strip().lstrip("vV")
    parts = value.split(".")
    if not 1 <= len(parts) <= 4 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Invalid release version: {value!r}")
    return tuple(int(part) for part in parts) + (0,) * (4 - len(parts))


def _asset_url(release, name):
    for asset in release.get("assets", []):
        if asset.get("name") == name:
            return asset.get("browser_download_url")
    return None


def _trusted_release_url(url):
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    expected_prefix = f"/{REPOSITORY}/releases/download/"
    return parsed.scheme == "https" and parsed.hostname == "github.com" and parsed.path.startswith(expected_prefix)


def _checksum_from_text(text, filename):
    valid_chars = set(string.hexdigits)
    for line in text.splitlines():
        fields = line.strip().split()
        if not fields:
            continue
        digest = fields[0].lower()
        listed_name = fields[-1].lstrip("*") if len(fields) > 1 else filename
        if len(digest) == 64 and set(digest) <= valid_chars and listed_name == filename:
            return digest
    raise ValueError("Release checksum is missing or invalid")


def _mark_checked(marker):
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


def _recently_checked(marker):
    try:
        return time.time() - marker.stat().st_mtime < CHECK_INTERVAL_SEC
    except OSError:
        return False


def _download_text(url):
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=(5, 15))
    response.raise_for_status()
    if len(response.content) > 100_000:
        raise ValueError("Checksum response is unexpectedly large")
    return response.content.decode("utf-8-sig")


def _download_executable(url, destination, expected_hash):
    partial = destination.with_suffix(".download")
    digest = hashlib.sha256()
    downloaded = 0
    try:
        with requests.get(url, headers=REQUEST_HEADERS, stream=True, timeout=(5, 60)) as response:
            response.raise_for_status()
            content_length = int(response.headers.get("Content-Length", 0))
            if content_length > MAX_DOWNLOAD_BYTES:
                raise ValueError("Update is larger than the allowed download size")
            with open(partial, "wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if downloaded > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Update is larger than the allowed download size")
                    digest.update(chunk)
                    output.write(chunk)
        if downloaded == 0 or digest.hexdigest() != expected_hash:
            raise ValueError("Downloaded update failed SHA-256 verification")
        os.replace(partial, destination)
    finally:
        try:
            partial.unlink()
        except FileNotFoundError:
            pass


def _start_replacement(new_exe, launch_mode):
    update_dir = new_exe.parent
    script_path = update_dir / "apply-update.ps1"
    script_path.write_text(_REPLACE_SCRIPT, encoding="utf-8-sig")
    command = [
        "powershell.exe", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
        "-File", str(script_path),
        "-ParentProcessId", str(os.getpid()),
        "-CurrentExe", sys.executable,
        "-NewExe", str(new_exe),
        "-LaunchMode", launch_mode,
    ]
    subprocess.Popen(
        command,
        close_fds=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def check_and_install(launch_mode="background", force=False):
    """Download a newer stable Windows release and schedule its installation."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False

    update_dir = Path(config.app_dir()) / "updates"
    marker = update_dir / "last-check"
    if not force and _recently_checked(marker):
        return False
    try:
        _mark_checked(marker)
        response = requests.get(RELEASE_API_URL, headers=REQUEST_HEADERS, timeout=(5, 15))
        response.raise_for_status()
        release = response.json()
        if not isinstance(release, dict):
            raise ValueError("GitHub returned invalid release metadata")
        latest_version = _parse_version(release.get("tag_name", ""))
        if latest_version <= _parse_version(APP_VERSION):
            return False

        exe_url = _asset_url(release, EXE_ASSET_NAME)
        checksum_url = _asset_url(release, CHECKSUM_ASSET_NAME)
        if not _trusted_release_url(exe_url) or not _trusted_release_url(checksum_url):
            raise ValueError("Release assets are missing or use an unexpected URL")

        expected_hash = _checksum_from_text(_download_text(checksum_url), EXE_ASSET_NAME)
        update_dir.mkdir(parents=True, exist_ok=True)
        new_exe = update_dir / f"{EXE_ASSET_NAME}.{release['tag_name']}.new"
        _download_executable(exe_url, new_exe, expected_hash)
        _start_replacement(new_exe, launch_mode)
        config.log(f"자동 업데이트 설치 시작: {APP_VERSION} -> {release['tag_name']}")
        return True
    except (OSError, KeyError, TypeError, ValueError, requests.RequestException) as exc:
        config.log(f"자동 업데이트 확인 실패: {exc!r}")
        return False
