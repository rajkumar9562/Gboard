# Gboard patches — experimental partial port for 18.4.6

Target: `com.google.android.inputmethod.latin`, version
`18.4.6.985164140-release-arm64-v8a`, versionCode `176027358`.

**Partial source port: 34 of 43 features admitted; 9 remain disabled.**
127 method/field/type bindings and selected bytecode/resource shapes were checked
against the supplied APKM. Compilation, Morphe patch application, installation,
and Android runtime behavior have **not** been verified. No compiled `.mpp` or
patched APK is included. This ZIP is not installable on Android.

Revision: `4.0.0-port1846.3`. The Java metadata subset and regression checks passed; the complete Android build remains untested.

See [PORT-1846.md](PORT-1846.md) for the exact status, features and build steps.
Upstream documentation is preserved in [README-UPSTREAM.md](README-UPSTREAM.md).
Upstream code and GPL-3.0 license notices are retained; this is an unofficial port.

## Standalone Gboard Mod (original Gboard safe)

**Important fix:** All enabled public patches now depend on the **Package Rename**
resource transform, even when the user does not explicitly select the Package Rename
option. This prevents a successfully patched APK from retaining the official Gboard
package identity. The default app label is **Gboard Mod**. If Package Rename is
selected and a different display name is chosen, that custom label is retained.

- Stock Gboard: `com.google.android.inputmethod.latin` (do not uninstall)
- Gboard Mod: `dev.jason.com.google.android.inputmethod.latin` (install separately)

Rebuild the `.mpp` from this ZIP; do not reuse the previous compiled patch bundle.
Import the new `.mpp` in Morphe and re-patch the original supported 18.4.6 input.
Before installing, inspect the *final* output APK's manifest/package ID; it MUST
be `dev.jason.com.google.android.inputmethod.latin` and not the original package.
Only a genuinely installable **single/universal APK** with this package name can
coexist; original-package split APKs must not be mixed into a renamed install set.
A `base.apk` alone is not guaranteed to include all required ABI/configuration splits.
If patching or rebuilding a complete standalone APK fails, do not uninstall the
system Gboard. This repository still does not contain a built APK and does not
claim device installation is verified.

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
