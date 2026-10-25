"""Small, journalled Fire OS telemetry profile. Computer ADB only; no root or on-device listener."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

PROFILE = (
    "com.amazon.neo.minerva",
    "com.amazon.neo.minerva.logcat",
    "com.amazon.device.telemetry.emitter",
    "com.amazon.dp.logger",
    "com.amazon.perfcollection",
    "com.amazon.wirelessmetrics.service",
    "com.amazon.tv.acr",
)
SUPPORTED = {("AFTKM", "RS8185.3891N")}
HARDWARE = {"TV_INPUT_HARDWARE", "BIND_INPUT_METHOD", "BLUETOOTH_PRIVILEGED", "NETWORK_SETTINGS"}
STATES = {0: "default-state", 1: "enable", 2: "disable", 3: "disable-user", 4: "disable-until-used"}


def enabled_state(dump):
    match = re.search(r"User 0:[^\n]*\benabled=(\d+)", dump)
    if not match or int(match[1]) not in STATES:
        raise ValueError("Cannot establish user-0 package state")
    return int(match[1])


def block_reason(pkg, dump, wifi_owners):
    if pkg not in PROFILE:
        return "outside reviewed telemetry allowlist"
    if pkg in wifi_owners:
        return "owns a saved Wi-Fi network"
    uid = re.search(r"\buserId=(\d+)", dump)
    if not uid or int(uid[1]) < 10000 or "sharedUser=" in dump or "sharedUserId=" in dump:
        return "system or shared UID"
    requested = re.search(r"requested permissions:(.*?)(?:install permissions:|runtime permissions:|User \d+:)", dump, re.S)
    if not requested:
        return "requested permissions unavailable"
    if any(p in requested[1] for p in HARDWARE):
        return "declares hardware/network-control permissions"
    return None


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class Device:
    def __init__(self, adb, address):
        self.command = [adb, "-s", address, "shell"]

    def shell(self, *args):
        result = subprocess.run(self.command + list(args), capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=30)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip()[:400])
        return result.stdout.strip()

    def identity(self):
        # Keep raw device identity out of reports and Git. The hash prevents cross-device restoration.
        serial = self.shell("getprop", "ro.serialno")
        if not serial:
            raise RuntimeError("Device identity unavailable")
        return {"device_hash": hashlib.sha256(serial.encode()).hexdigest(),
                "model": self.shell("getprop", "ro.product.model"),
                "build": self.shell("getprop", "ro.build.display.id")}

    def dump(self, pkg):
        return self.shell("dumpsys", "package", pkg)


def audit(device):
    identity = device.identity()
    wifi = device.shell("dumpsys", "wifi")
    wifi_owners = set(re.findall(r"cname=([\w.]+)", wifi))
    wifi_known = bool(wifi_owners)
    processes = device.shell("ps", "-A", "-o", "NAME").splitlines()
    packages = set(device.shell("pm", "list", "packages").splitlines())
    candidates = []
    for pkg in PROFILE:
        if "package:" + pkg not in packages:
            candidates.append({"package": pkg, "blocked": "not installed"})
            continue
        dump = device.dump(pkg)
        reason = block_reason(pkg, dump, wifi_owners) if wifi_known else "Wi-Fi ownership unknown"
        candidates.append({"package": pkg, "enabled_state": enabled_state(dump), "blocked": reason,
                           "running": any(p.strip() == pkg or p.strip().startswith(pkg + ":") for p in processes)})
    return {**identity, "supported": (identity["model"], identity["build"]) in SUPPORTED,
            "candidates": candidates}


def apply(device, report, path):
    if not report["supported"]:
        raise RuntimeError("Unverified model/build: audit only; no changes made")
    if path.exists():
        journal = json.loads(path.read_text(encoding="utf-8"))
        if journal.get("device_hash") != report["device_hash"]:
            raise RuntimeError("Journal belongs to another device")
    else:
        journal = {k: report[k] for k in ("device_hash", "model", "build")}
        journal.update(schema=1, entries={})
    results = []
    for item in report["candidates"]:
        pkg = item["package"]
        if pkg not in PROFILE:
            raise RuntimeError("Unreviewed package in audit")
        if item["blocked"] or item["enabled_state"] in (2, 3, 4):
            results.append({"package": pkg, "result": item["blocked"] or "already disabled; unchanged"})
            continue
        if enabled_state(device.dump(pkg)) != item["enabled_state"]:
            results.append({"package": pkg, "result": "state changed since audit; left unchanged"})
            continue
        entry = journal["entries"].get(pkg)
        if entry and entry.get("changed"):
            results.append({"package": pkg, "result": "state drift; left unchanged"})
            continue
        # Write intent BEFORE mutation. If ADB disconnects afterwards, restore still knows the original state.
        entry = {"original": item["enabled_state"], "pending": True, "changed": False,
                 "at": datetime.now(timezone.utc).isoformat()}
        journal["entries"][pkg] = entry
        atomic_json(path, journal)
        try:
            output = device.shell("pm", "disable-user", "--user", "0", pkg)
            actual = enabled_state(device.dump(pkg))
            entry.update(pending=False, changed=actual == 3,
                         result="disabled" if actual == 3 else "refused; unchanged")
            if actual != 3:
                entry["detail"] = output[:300]
        except RuntimeError as error:
            # Confirm a protected-package refusal, but leave intent pending if the transport itself disappeared.
            entry["detail"] = str(error)[:300]
            try:
                actual = enabled_state(device.dump(pkg))
            except (RuntimeError, ValueError):
                atomic_json(path, journal)
                raise
            entry.update(pending=False, changed=actual == 3,
                         result="disabled" if actual == 3 else "refused; unchanged")
            atomic_json(path, journal)
        atomic_json(path, journal)
        if entry["changed"]:
            try:
                # Unlike force-stop, kill asks AMS to terminate only background-safe processes and doesn't persist
                # a stopped-package flag. Fire OS may still keep privileged/persistent processes alive.
                device.shell("am", "kill", "--user", "0", pkg)
            except RuntimeError:
                pass
        results.append({"package": pkg, "result": entry["result"]})
    return results


def restore(device, path):
    journal = json.loads(path.read_text(encoding="utf-8"))
    if journal.get("device_hash") != device.identity()["device_hash"]:
        raise RuntimeError("Journal belongs to another device")
    entries = journal.get("entries", {})
    # Validate every entry before restoring anything. Never execute arbitrary package names from a state file.
    for pkg, entry in entries.items():
        if pkg not in PROFILE or type(entry.get("original")) is not int or entry["original"] not in STATES:
            raise RuntimeError("Invalid journal entry; no changes made")
    results = []
    for pkg, entry in entries.items():
        if not (entry.get("changed") or entry.get("pending")):
            continue
        actual = enabled_state(device.dump(pkg))
        if actual == entry["original"]:
            entry.update(changed=False, pending=False, result="already restored")
        elif actual != 3:
            results.append({"package": pkg, "result": "state drift; left unchanged"})
            continue
        else:
            device.shell("pm", STATES[entry["original"]], "--user", "0", pkg)
            if enabled_state(device.dump(pkg)) != entry["original"]:
                raise RuntimeError("Restoration not confirmed for " + pkg)
            entry.update(changed=False, pending=False, result="restored")
        atomic_json(path, journal)
        results.append({"package": pkg, "result": entry["result"]})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("audit", "apply", "restore"))
    parser.add_argument("--device", required=True, help="ADB device address, usually IP:5555")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--state", type=Path, help="Persistent local rollback journal (never inside out/)")
    args = parser.parse_args()
    device = Device(args.adb, args.device)
    identity = device.identity()
    state = args.state or Path(__file__).resolve().parents[1] / ".local" / "fire-tv-debloat" / (identity["device_hash"] + ".json")
    if args.action == "audit":
        result = audit(device)
        result.pop("device_hash")
    elif args.action == "apply":
        result = apply(device, audit(device), state)
    else:
        result = restore(device, state)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        print("Stopped: " + str(error), file=sys.stderr)
        sys.exit(1)
