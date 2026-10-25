package io.freemytv;

public final class FireTvHomePolicyTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        FireTvHomePolicy p = new FireTvHomePolicy();
        String home = "com.amazon.tv.launcher.ui.HomeActivity_vNext";
        check(p.shouldRedirect("com.amazon.tv.launcher", home, 10000), "Home must redirect");
        check(p.shouldRedirect("com.amazon.tv.launcher", "com.amazon.tv.launcher.ui.HomeActivity", 10000), "Legacy Home");
        check(!p.shouldRedirect("com.netflix.ninja", home, 10000), "Never interrupt streaming apps");
        check(!p.shouldRedirect("com.amazon.tv.launcher", "android.app.AlertDialog", 10000), "Never intercept dialogs");
        check(!p.shouldRedirect("com.amazon.ftv.screensaver", home, 10000), "Never interrupt the screensaver");
        check(!p.shouldRedirect("com.amazon.tv.launcher", "com.amazon.tv.launcher.ui.SettingsActivity", 10000), "Settings");
        check(!p.shouldRedirect("com.amazon.tv.launcher", home, 11000), "Settings transition must be allowed");
        check(p.shouldRedirect("com.amazon.tv.launcher", home, 13000), "Home must recover after Settings");
        p.shouldRedirect("com.amazon.tv.settings.v2", "Settings", 14000);
        check(!p.shouldRedirect("com.amazon.tv.launcher", home, 15000), "Native Settings transition");
        check(p.shouldRedirect("com.amazon.tv.launcher", home, 17000), "Home after native Settings");
        check(!p.shouldRedirect("", "", 18000), "Incomplete events must be ignored");
        p.pauseForSettings(19000);
        check(!p.shouldRedirect("com.amazon.tv.launcher", home, 20000), "Explicit Settings pause");
        check(p.delayUntilRedirect("com.amazon.tv.launcher", home, 20000) == 1500, "Home during pause must be queued");
        check(p.delayUntilRedirect("com.netflix.ninja", home, 20000) == -1, "Never queue another app");
        check(p.shouldRedirect("com.amazon.tv.launcher", home, 22000), "Explicit Settings pause expires");
        System.out.println("Fire TV Home policy: 15 checks passed");
    }
}
