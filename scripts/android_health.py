"""Adds Health Connect step reading to the generated Capacitor Android project.
Run from android-app/ after `npx cap add android`."""
import re
M = 'android/app/src/main/AndroidManifest.xml'
s = open(M).read()
if 'health.READ_STEPS' not in s:
    s = s.replace('<uses-permission android:name="android.permission.INTERNET" />',
                  '<uses-permission android:name="android.permission.INTERNET" />\n'
                  '    <uses-permission android:name="android.permission.health.READ_STEPS" />', 1)
if 'com.google.android.apps.healthdata' not in s:
    s = s.replace('<application', '<queries>\n        <package android:name="com.google.android.apps.healthdata" />\n    </queries>\n\n    <application', 1)
# Health Connect opens the app to explain why it wants steps:
# the rationale intent (Android 13 and older) and the permission-usage alias (Android 14+).
if 'ACTION_SHOW_PERMISSIONS_RATIONALE' not in s:
    s, n = re.subn(r'(<category android:name="android.intent.category.LAUNCHER"\s*/>\s*</intent-filter>)',
                   r'\1\n            <intent-filter>\n                <action android:name="androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE" />\n            </intent-filter>', s, count=1)
    assert n == 1, 'launcher intent-filter not found'
if 'VIEW_PERMISSION_USAGE' not in s:
    s = s.replace('</application>', '''    <activity-alias
            android:name="ViewPermissionUsageActivity"
            android:exported="true"
            android:targetActivity=".MainActivity"
            android:permission="android.permission.START_VIEW_PERMISSION_USAGE">
            <intent-filter>
                <action android:name="android.intent.action.VIEW_PERMISSION_USAGE" />
                <category android:name="android.intent.category.HEALTH_PERMISSIONS" />
            </intent-filter>
        </activity-alias>
    </application>''', 1)
open(M, 'w').write(s)
V = 'android/variables.gradle'
v = open(V).read()
v = re.sub(r'minSdkVersion\s*=\s*\d+', 'minSdkVersion = 26', v)  # Health Connect needs Android 8+
open(V, 'w').write(v)
print('Health Connect added; minSdk 26')
