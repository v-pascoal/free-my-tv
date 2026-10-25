# Free My TV on Fire TV — experimental fork

This fork adds a Home-button redirect for Fire OS without root, disabling Amazon packages, reading logs, or using
the TV's loopback ADB. The Amazon launcher remains the system Home. A narrow accessibility service observes only
foreground package/class names and opens `FireHomeActivity` when the Amazon Home activity appears. It cannot read
screen content, intercept keys, or retrieve accessibility window trees. No continuous polling runs.

## Setup

Build with the usual `./build.sh` and install `FreeMyTV.apk` using computer ADB. Keep your signing key and
`config.properties` locally; neither belongs in Git. A build signed with your own key cannot update an official
release. If replacing an official release, uninstall that user app first (its preferences will be lost).

Enable `io.freemytv/io.freemytv.FireTvHomeService` once using computer ADB. Preserve other services in
`settings get secure enabled_accessibility_services`: append this component with a colon instead of replacing the
list. Then set `settings put secure accessibility_enabled 1`. Fire OS does not list third-party services in its
Accessibility menu. No usage-access, overlay, storage, notification or device-administrator grant is needed for Home.

On Windows, after installing the APK and connecting ADB, use the helper (substitute your address):

```powershell
powershell -File tools/fire-tv-service.ps1 -DeviceAddress '<address>:5555' -Adb '<path-to-adb.exe>'
# Remove only this fork's accessibility service, preserving all other entries:
powershell -File tools/fire-tv-service.ps1 -DeviceAddress '<address>:5555' -Adb '<path-to-adb.exe>' -Remove
```

On the TV open Free My TV → its settings → Home Screen → Free My TV. This opt-in is saved locally. The service
reconnects after a boot and restores the chosen Home redirect. The Home switch never calls `pm disable-user` on Fire
OS. Stock Settings launches get a short exemption to keep Amazon's configuration UI reachable.

Choose Home Screen → Original to stop redirecting immediately. Amazon Home remains available. The crash watchdog
also stops redirection after three recent crashes, without needing ADB. Uninstalling the app removes its service.

## Scope and limits

- Fire OS may show its launcher briefly before the redirect. This is not a bootloader unlock or native HOME-role
  replacement. Amazon components remain in memory: the upstream 60% RAM figure does not apply to this mode.
- On-device ADB stays blocked. The sleep timer uses the accessibility screen-lock action on API 28+, with no device
  administrator. Its result depends on Fire OS honoring that action and needs a real timed test. Remote remapping
  and automatic system-screensaver replacement remain unavailable. Screensaver preview and personal photos
  remain available in the app. Native sleep/screen-off behavior stays with Fire OS.
- Weather/currency/location follow local config or Home Settings. Recommendations need the user's TMDB key in local
  `config.properties`. The key is embedded in a personal APK; never publish that personal APK.
- A Fire OS update may disable the service or change launcher class names. Recheck Home after updates.
- Boot persistence and every hardware/streaming combination require on-device verification. See the validation notes
  below rather than assuming all Fire TVs are supported.

## Validation

Run `bash tools/test-fire-tv.sh` for Home, Settings, dialog, screensaver and unrelated-app policy checks. Run
`tools/check.sh` for the upstream build, catalogues and web packages. Device test results are recorded separately
after real hardware checks; do not infer them from a successful compilation.

### App store shortcut (1.2-firetv.2)

Fire TV defaults now include a storefront button beside Live TV in the upper-right corner. Existing custom top-button
orders receive it once, after Live TV (or first if Live TV was hidden); removing it later in Top Buttons is respected.
The button always opens a remote-navigable chooser of installed stores, even when only one is installed.
Supported packages: Amazon Appstore, Aptoide TV, Flicky/F-Droid, F-Droid and Aurora Store. The launcher does not download
APKs or request package-install privileges. Store apps need to be installed separately from their own official sources.
On Fire OS 8, Amazon's generic launcher alias returns through Amazon Home; this button uses the exported Appstore
`ADEHomeActivity` when available to avoid the Home redirect intercepting the store. Other versions fall back to the
store's advertised launcher intent.

On the test device Aptoide TV 5.1.3 (official Aptoide metadata/download, checksum and certificate checked) and Flicky
4.6.1 armeabi-v7a (official GitHub release, SHA-256 and APK signature checked) were installed alongside Amazon Appstore.
These are separate applications, not bundled in this fork. Their first-run setup and package-install prompts belong to
each store. The launcher neither bypasses purchases nor grants the stores privileged installation permissions.

### Hardware validation

Tested on AFTKM / karat, Fire OS 8.1.8.5, Android 11 (API 30):

- Personal APK installed successfully; service bound with `capabilities=0` (no screen-content/key access).
- Owner confirmed the physical Home button opens Free My TV.
- Host-driven Home tests from native Amazon Settings, Prime Video and repeated Home all returned to
  `FireHomeActivity`. Observed end-to-end times, including ADB inspection overhead: 2.39 s, 1.91 s and 1.81 s.
  These are not frame-accurate launcher benchmarks.
- Native Amazon Settings and Prime Video stayed accessible.
- Recommendations loaded (24 titles); the lower drawer displayed São Paulo weather, a five-day forecast, and
  Bitcoin/dollar quotes in BRL. From an app on the shelf, press Down to open that drawer; Back closes it.
- No system packages were disabled. No device administrator, storage, notification or overlay permission was granted.
- Full `tools/check.sh` passed: Android build, 15 Home policy checks, 244 translation keys, LG/Samsung builds and ES5.
- Cold boot, the timed screen-lock action, custom background import, DRM/playback quality and every remote app button
  remain unverified. This is an experimental adaptation, not a claim of complete Fire OS replacement.
