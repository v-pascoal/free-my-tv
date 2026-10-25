# Reviewed Fire TV telemetry profile

This fork includes a separate computer-side tool, `tools/fire_tv_debloat.py`. It does not change the launcher's broad
Amazon protection rule or give the TV app package-management privileges. Applying is opt-in, uses only a seven-package
allowlist, and is pinned to the hardware/build tested here: AFTKM / RS8185.3891N (Fire OS 8.1.8.5).

## Research and decisions

Reviewed 2026-10-25:

| Source | Useful idea | What this profile does differently |
|---|---|---|
| [firetv-glass-launcher disable list](https://github.com/ivantrj/firetv-glass-launcher/blob/main/debloat/disable-list.txt) | Separates telemetry from content/casting/update features | Uses only telemetry candidates, then checks the actual device |
| [firetv-safe-debloat](https://github.com/roy9611/firetv-safe-debloat) | Computer ADB and reversible disable-user | Does not disable Photos/screensaver/live-TV services, cap background processes, clear caches or change DNS |
| [Fire-Stick-Debloat](https://github.com/cmeraspro-dev/Fire-Stick-Debloat) | Restore support and protecting the launcher/store | Does not apply blanket removals; preserves exact prior package enabled states |
| [tv-tweak](https://github.com/26zl/tv-tweak) | Inventory, protection boundaries and drift-aware verification | Pins this initial profile to the tested model/build and refuses other packages |

These are reference projects, not a guarantee that their entire lists are safe on other Fire TVs. No third-party
script is downloaded and executed by this tool. No root exploits, OTA blocking, system uninstalls, app-data clearing,
global background-process limits, DNS changes, or streaming-app background restrictions are included.

## Included packages

- `com.amazon.neo.minerva`
- `com.amazon.neo.minerva.logcat`
- `com.amazon.device.telemetry.emitter`
- `com.amazon.dp.logger`
- `com.amazon.perfcollection`
- `com.amazon.wirelessmetrics.service`
- `com.amazon.tv.acr`

Before disabling, the tool checks installed state, Wi-Fi ownership, dedicated application UID and declared hardware
permissions. If it cannot establish Wi-Fi owners or package state, it does not guess. Unknown models/builds are
audit-only. Protected-package refusals are recorded without bypassing them.

## Use and restore

Connect the computer's ADB to the TV, then run (substitute your address and ADB path):

```powershell
python tools/fire_tv_debloat.py audit --device '<address>:5555' --adb '<path-to-adb.exe>'
python tools/fire_tv_debloat.py apply --device '<address>:5555' --adb '<path-to-adb.exe>'
python tools/fire_tv_debloat.py restore --device '<address>:5555' --adb '<path-to-adb.exe>'
```

The persistent rollback journal is under `.local/fire-tv-debloat/`, ignored by Git and preserved by rebuilds. It is
written and flushed **before** each mutation, so interrupted changes can still be restored. Do not delete it while
using this profile. Restore validates device identity and every allowlisted entry; it restores `default-state` when
that was the original state, instead of blindly enabling everything. Existing disabled packages are never claimed
or enabled. Subsequent state drift is left unchanged.

The launcher's Home Screen → Original switch only stops Home redirection. It does **not** undo this separate
computer-applied profile: use the tool's `restore` action and keep the local journal.

`apply` also asks Android to kill only background-safe processes of packages successfully disabled. This is not
`force-stop`: it does not persist a stopped-package flag. Fire OS may ignore it for persistent services. Re-run
`audit` and check `running`; a disabled package does not prove that its existing process has exited.

## Observed on the owner's Fire TV

- All seven packages were installed, default-enabled (`enabled=0`), had dedicated app UIDs and no identified
  hardware-control permission. The saved Wi-Fi belonged to the setup app, outside this allowlist.
- All seven accepted `disable-user --user 0` and subsequently reported `enabled=3`.
- A full restore test returned all seven to their exact original state (`enabled=0`); the profile was then reapplied.
- Minerva, Minerva Logcat and Telemetry Emitter remained running with their original PIDs even after the request to
  kill background-safe processes. Their sampled pre-change PSS totaled 6,495 KiB (about 6.3 MiB). **No immediate RAM
  saving or complete telemetry blocking was established.** Do not substitute a package count for a performance gain.
- After an owner-authorized reboot, boot completion was confirmed and all seven packages remained disabled. Minerva,
  Minerva Logcat and Telemetry Emitter nevertheless started again with new PIDs. Their combined sampled PSS was
  5,719 KiB; comparison with the pre-reboot sample is not a controlled performance measurement. The accessibility
  service rebound and pressing Home returned to Free My TV. Immediate automatic Home display during startup and
  long-session reliability remain unverified. The launcher's Home redirection continues to need Amazon Home.
- After application, Prime Video, Amazon Appstore and Home returns were checked. The initial native-Settings probe
  did not retain focus; a direct `am start -W` retest and three subsequent open/stay-open trials passed. There was no
  AndroidRuntime crash in the inspected log window. This is basic navigation verification, not a streaming/DRM test.

## Tests

`python -m unittest discover -s tests -p 'test_*.py'` exercises write-before-mutate, exact restoration, interruption,
drift, pre-disabled packages, cross-device rejection and the protection boundaries. Hardware observations above are
separate from those tests. Raw device dumps, the device hash and rollback state remain local.
