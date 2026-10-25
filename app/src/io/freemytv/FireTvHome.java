package io.freemytv;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.provider.Settings;

/** Fire OS keeps its launcher: redirect Home without disabling Amazon packages or using on-device ADB. */
final class FireTvHome {
    private FireTvHome() {}

    static boolean serviceEnabled(Context c) {
        String services = Settings.Secure.getString(c.getContentResolver(), Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        ComponentName ours = new ComponentName(c, FireTvHomeService.class);
        if (services != null) for (String entry : services.split(":")) {
            if (ours.equals(ComponentName.unflattenFromString(entry))) return true;
        }
        return false;
    }

    static boolean active(Context c) {
        org.json.JSONObject s = HomeMode.state(c);
        return HomeMode.AMAZON && HomeMode.FREE.equals(s.optString("mode")) && !s.optBoolean("homeReverted");
    }

    static void open(Context c) {
        c.startActivity(new Intent(c, FireHomeActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP));
    }

    static void original(Context c) {
        c.startActivity(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
                .setPackage("com.amazon.tv.launcher").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
    }

    /** The stock Settings UI sometimes passes through the launcher. Let it settle without intercepting it. */
    static void openSettings(Context c) {
        FireTvHomeService.pauseForSettings(c);
        c.startActivity(new Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
    }
}
