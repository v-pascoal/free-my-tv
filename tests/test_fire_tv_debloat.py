import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fire_tv_debloat as debloat

PKG = debloat.PROFILE[0]


def dump(state=0, uid=10123, permissions="", shared=""):
    return f"userId={uid}\n{shared}\nrequested permissions:\n{permissions}\ninstall permissions:\nUser 0: installed=true enabled={state}\n"


class FakeDevice:
    def __init__(self, state=0, refuse=False):
        self.state = state
        self.calls = []
        self.refuse = refuse
        self.before_mutation = lambda: None

    def identity(self):
        return {"device_hash": "test-device", "model": "AFTKM", "build": "RS8185.3891N"}

    def dump(self, pkg):
        return dump(self.state)

    def shell(self, *args):
        if args[:2] == ("am", "kill"):
            return ""
        self.before_mutation()
        self.calls.append(args)
        if self.refuse:
            raise RuntimeError("Cannot disable a protected package")
        self.state = next(state for state, command in debloat.STATES.items() if command == args[1])
        return "new state: " + str(self.state)


def report(state=0):
    return {"device_hash": "test-device", "model": "AFTKM", "build": "RS8185.3891N", "supported": True,
            "candidates": [{"package": PKG, "enabled_state": state, "blocked": None}]}


class DebloatTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / ".local" / "test-temp"
        test_root.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=test_root)
        assert Path(self.directory.name).resolve().is_relative_to(test_root.resolve())
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "journal.json"

    def test_critical_packages_never_enter_allowlist(self):
        for pkg in ("com.amazon.tv.launcher", "com.amazon.venezia", "com.amazon.device.software.ota",
                    "com.android.systemui", "com.amazon.tv.oobe", "com.amazon.tv.ime", "com.amazon.firebat"):
            self.assertIsNotNone(debloat.block_reason(pkg, dump(), set()))

    def test_wifi_owner_is_blocked(self):
        self.assertIn("Wi-Fi", debloat.block_reason(PKG, dump(), {PKG}))

    def test_system_shared_and_hardware_packages_are_blocked(self):
        self.assertIsNotNone(debloat.block_reason(PKG, dump(uid=1000), set()))
        self.assertIsNotNone(debloat.block_reason(PKG, dump(shared="sharedUser=system"), set()))
        self.assertIsNotNone(debloat.block_reason(PKG, dump(permissions="android.permission.TV_INPUT_HARDWARE"), set()))

    def test_pending_journal_is_durable_before_disable(self):
        device = FakeDevice()
        def before():
            entry = json.loads(self.path.read_text())["entries"][PKG]
            self.assertTrue(entry["pending"])
            self.assertEqual(entry["original"], 0)
        device.before_mutation = before
        debloat.apply(device, report(), self.path)
        self.assertTrue(json.loads(self.path.read_text())["entries"][PKG]["changed"])

    def test_restore_preserves_default_state_not_just_enabled(self):
        device = FakeDevice()
        debloat.apply(device, report(), self.path)
        debloat.restore(device, self.path)
        self.assertEqual(device.calls[-1], ("pm", "default-state", "--user", "0", PKG))
        self.assertEqual(device.state, 0)

    def test_already_disabled_is_not_owned_by_tool(self):
        device = FakeDevice(3)
        debloat.apply(device, report(3), self.path)
        self.assertFalse(device.calls)
        self.assertFalse(self.path.exists())

    def test_protected_refusal_is_recorded_without_workaround(self):
        device = FakeDevice(refuse=True)
        result = debloat.apply(device, report(), self.path)
        self.assertEqual(result[0]["result"], "refused; unchanged")
        self.assertEqual(len(device.calls), 1)
        self.assertFalse(json.loads(self.path.read_text())["entries"][PKG]["changed"])

    def test_pending_disable_can_be_restored_after_interruption(self):
        self.path.write_text(json.dumps({"device_hash": "test-device", "entries": {
            PKG: {"original": 1, "pending": True, "changed": False}}}))
        device = FakeDevice(3)
        debloat.restore(device, self.path)
        self.assertEqual(device.state, 1)

    def test_other_device_or_unreviewed_package_is_rejected(self):
        self.path.write_text(json.dumps({"device_hash": "other", "entries": {}}))
        with self.assertRaises(RuntimeError):
            debloat.restore(FakeDevice(), self.path)
        self.path.write_text(json.dumps({"device_hash": "test-device", "entries": {
            "com.amazon.tv.launcher": {"original": 0, "changed": True}}}))
        device = FakeDevice(3)
        with self.assertRaises(RuntimeError):
            debloat.restore(device, self.path)
        self.assertFalse(device.calls)

    def test_state_drift_is_not_overwritten(self):
        device = FakeDevice()
        debloat.apply(device, report(), self.path)
        device.state = 4
        result = debloat.restore(device, self.path)
        self.assertEqual(device.state, 4)
        self.assertIn("drift", result[0]["result"])

    def test_unverified_device_is_audit_only(self):
        device = FakeDevice()
        unverified = report()
        unverified["supported"] = False
        with self.assertRaises(RuntimeError):
            debloat.apply(device, unverified, self.path)
        self.assertFalse(device.calls)


if __name__ == "__main__":
    unittest.main()
