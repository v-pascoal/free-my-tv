package io.freemytv;

import android.accessibilityservice.AccessibilityService;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityEvent;

/** Reads only foreground package/class names. No window content, keys, logs, polling, overlay or network. */
public class FireTvHomeService extends AccessibilityService {
    private static volatile FireTvHomeService connected;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final FireTvHomePolicy policy = new FireTvHomePolicy();
    private static final String SETTINGS_PAUSE = "io.freemytv.FIRE_SETTINGS_PAUSE";
    private final android.content.BroadcastReceiver settingsPause = new android.content.BroadcastReceiver() {
        @Override public void onReceive(android.content.Context c, Intent intent) {
            policy.pauseForSettings(SystemClock.uptimeMillis());
            handler.removeCallbacks(redirect);
        }
    };
    private final Runnable redirect = () -> {
        if (!FireTvHome.active(this) || Watchdog.crashedTooOften(this)
                || !getSystemService(PowerManager.class).isInteractive()) return;
        try {
            FireTvHome.open(this);
            AppLog.w("Fire TV: Home redirected");
        } catch (RuntimeException e) {
            AppLog.w("Fire TV Home: " + e.getMessage());
        }
    };

    /** Called from :home; a signature permission keeps the broadcast inside this fork. */
    static void pauseForSettings(android.content.Context c) {
        c.sendBroadcast(new Intent(SETTINGS_PAUSE).setPackage(c.getPackageName()));
    }

    @Override protected void onServiceConnected() {
        connected = this;
        registerReceiver(settingsPause, new android.content.IntentFilter(SETTINGS_PAUSE), "io.freemytv.permission.INTERNAL", null);
        SleepTimer.listen(this);
        AppLog.w("Fire TV: Home service connected");
        if (FireTvHome.active(this)) handler.postDelayed(redirect, 1500);
    }

    @Override public void onAccessibilityEvent(AccessibilityEvent event) {
        if (!HomeMode.AMAZON || event.getEventType() != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) return;
        handler.removeCallbacks(redirect);
        String pkg = event.getPackageName() == null ? "" : event.getPackageName().toString();
        String cls = event.getClassName() == null ? "" : event.getClassName().toString();
        long delay = policy.delayUntilRedirect(pkg, cls, SystemClock.uptimeMillis());
        if (delay >= 0) handler.postDelayed(redirect, delay);
    }

    @Override public void onInterrupt() { handler.removeCallbacks(redirect); }

    /** API 28+: use Android's accessibility lock action instead of blocked loopback ADB. */
    static boolean sleep() {
        FireTvHomeService service = connected;
        return service != null && android.os.Build.VERSION.SDK_INT >= 28
                && service.performGlobalAction(GLOBAL_ACTION_LOCK_SCREEN);
    }

    @Override public void onDestroy() {
        connected = null;
        handler.removeCallbacksAndMessages(null);
        try { unregisterReceiver(settingsPause); } catch (IllegalArgumentException ignored) {}
        super.onDestroy();
    }
}
