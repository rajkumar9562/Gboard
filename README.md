# Gboard patches — experimental partial port for 18.4.6

Target: `com.google.android.inputmethod.latin`, version
`18.4.6.985164140-release-arm64-v8a`, versionCode `176027358`.

**Partial source port: 34 of 43 features admitted; 9 remain disabled.**
127 method/field/type bindings and selected bytecode/resource shapes were checked
against the supplied APKM. Compilation, Morphe patch application, installation,
and Android runtime behavior have **not** been verified. No compiled `.mpp` or
patched APK is included. This ZIP is not installable on Android.

Revision: `4.0.0-port1846.2`. The Java metadata subset and regression checks passed; the complete Android build remains untested.

See [PORT-1846.md](PORT-1846.md) for the exact status, features and build steps.
Upstream documentation is preserved in [README-UPSTREAM.md](README-UPSTREAM.md).
Upstream code and GPL-3.0 license notices are retained; this is an unofficial port.

## GitHub par build karna

1. ZIP extract karein. Folder ke andar ke files apne GitHub repository mein
   upload karein; `.github`, `gradle`, `patches` aur `extensions` bhi include karein.
2. Repository Settings → Secrets and variables → Actions mein
   `MORPHE_PACKAGES_TOKEN` add karein. Token ko Morphe GitHub Packages registry
   ka read access chahiye. Token owner repository owner se alag ho to
   `MORPHE_PACKAGES_USER` mein uska username add karein. Token source code mein na likhein.
3. Actions → **Build experimental Gboard 18.4.6 port** → Run workflow.
4. Successful run ke artifact se `.mpp` download karein. Morphe mein local patch
   bundle import karke original, complete APKM select karein. Pehle build aur
   device testing zaroori hai; working result ki guarantee nahi di gayi hai.

Workflow build artifact banata hai. Woh GitHub Release publish nahi karta.
`patches-bundle.json` ka download URL khaali hai, kyunki koi hosted release nahi bani.
Original upstream Morphe source add karne se upstream 18.5.4 bundle hi milega,
yeh custom port nahi.
