# Gboard Mod — alag APK / side-by-side installation fix

## Problem

System Gboard ka package ID `com.google.android.inputmethod.latin` hai.
Agar patched APK bhi isi package ID se banta hai, Android use existing Gboard
ka update samajhta hai. Signature match na hone par install fail hota hai.
System Gboard ko uninstall karne ki zarurat nahi hai.

## Is source ZIP mein kya fix hai?

- Har enabled public patch ab **Package Rename** resource transformation ko
  mandatory dependency ki tarah use karta hai, chahe user ne alag se
  **Package Rename** option select kiya ho ya nahin.
- Final package ID: `dev.jason.com.google.android.inputmethod.latin`.
- Default visible app name: **Gboard Mod**.
- User ne Package Rename mein koi aur app naam select kiya ho to wahi rahega.
- Original system Gboard: `com.google.android.inputmethod.latin` — untouched.
- Package-related provider authorities aur permissions ko rename karne ka
  existing transformation bana rehta hai.

## Dobara patch kaise karein

1. Is updated ZIP ki **saari** files GitHub repository mein rakhein.
2. Repository Actions mein **Build experimental Gboard 18.4.6 port** run karein.
   README.md mein `MORPHE_PACKAGES_TOKEN` set karne ke steps hain.
3. Naya `.mpp` build artifact download karke Morphe mein import karein.
   Purana patch bundle reuse mat karein.
4. Sirf supported original Gboard 18.4.6.985164140 arm64-v8a APKM se patch karein.
5. Install karne se *pehle* final APK ke manifest ka package name check karein:
   `dev.jason.com.google.android.inputmethod.latin` hona chahiye.
   `com.google.android.inputmethod.latin` ho to APK install **na** karein.
6. Official Gboard ke naam wale split APKs ko renamed base APK ke saath mix
   na karein. Aapko complete, consistent, installable standalone APK chahiye.

## Important

Ye **source project ZIP** hai; ismein already built APK ya `.mpp` nahi hai.
Static tests pass hue hain, lekin Android build, patched APK ka device test aur
split-to-standalone packaging verify nahi hui. Isliye installation ki guarantee
nahi hai. System Gboard ko uninstall na karein.
