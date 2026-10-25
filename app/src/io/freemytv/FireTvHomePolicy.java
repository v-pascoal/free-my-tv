package io.freemytv;

/** Pure decision logic, kept independent of Android so Settings/sleep exclusions can be tested on the host. */
final class FireTvHomePolicy {
    private long settingsUntil;

    void pauseForSettings(long now) { settingsUntil = now + 2500; }

    boolean shouldRedirect(String pkg, String cls, long now) {
        return delayUntilRedirect(pkg, cls, now) == 80;
    }

    /** -1 ignores the window; otherwise wait for Settings transitions before opening Home. */
    long delayUntilRedirect(String pkg, String cls, long now) {
        if (pkg.startsWith("com.amazon.tv.settings") || pkg.equals("com.amazon.android.settings")
                || (pkg.equals("com.amazon.tv.launcher") && cls.toLowerCase(java.util.Locale.ROOT).contains("settings"))) {
            pauseForSettings(now);
            return -1;
        }
        if (!pkg.equals("com.amazon.tv.launcher")) return -1;
        // Excludes dialogs, input methods, profiles, voice search, pairing and the stock screensaver.
        if (!cls.equals("com.amazon.tv.launcher.ui.HomeActivity_vNext")
                && !cls.equals("com.amazon.tv.launcher.ui.HomeActivity")) return -1;
        return Math.max(80, settingsUntil - now);
    }
}
