package io.freemytv;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.List;

/** Opens installed stores only. This launcher neither downloads APKs nor requests installation privileges. */
final class AppStores {
    private AppStores() {}
    private static final String[][] STORES = {
            {"com.amazon.venezia", "Amazon Appstore"},
            {"cm.aptoidetv.pt", "Aptoide TV"},
            {"app.flicky", "Flicky (F-Droid)"},
            {"org.fdroid.fdroid", "F-Droid"},
            {"com.aurora.store", "Aurora Store"}
    };

    static boolean open(Activity activity) {
        PackageManager pm = activity.getPackageManager();
        List<Intent> intents = new ArrayList<>();
        List<String> labels = new ArrayList<>();
        for (String[] store : STORES) {
            Intent launch = null;
            if ("com.amazon.venezia".equals(store[0])) {
                // Fire OS 8's launcher alias routes through Amazon Home, where our Home redirect would intercept it.
                Intent direct = new Intent().setComponent(new ComponentName(store[0], store[0] + ".ade.ADEHomeActivity"));
                android.content.pm.ResolveInfo resolved = pm.resolveActivity(direct, 0);
                if (resolved != null && resolved.activityInfo.exported && resolved.activityInfo.enabled) launch = direct;
            }
            if (launch == null) launch = pm.getLeanbackLaunchIntentForPackage(store[0]);
            if (launch == null) launch = pm.getLaunchIntentForPackage(store[0]);
            if (launch == null) continue;
            intents.add(launch);
            labels.add(store[1]);
        }
        if (intents.isEmpty()) {
            Toast.makeText(activity, Ui.tr("No app store is installed."), Toast.LENGTH_LONG).show();
            return false;
        }
        new AlertDialog.Builder(activity).setTitle(Ui.tr("App stores"))
                .setItems(labels.toArray(new String[0]), (dialog, index) -> launch(activity, intents.get(index)))
                .setNegativeButton(Ui.tr("Back"), null).show();
        return true;
    }

    private static boolean launch(Activity activity, Intent intent) {
        try {
            activity.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            return true;
        } catch (ActivityNotFoundException | SecurityException e) {
            Toast.makeText(activity, Ui.tr("Couldn't open the app store."), Toast.LENGTH_LONG).show();
            return false;
        }
    }
}
