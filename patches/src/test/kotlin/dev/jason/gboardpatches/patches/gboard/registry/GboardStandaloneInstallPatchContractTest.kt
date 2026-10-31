package dev.jason.gboardpatches.patches.gboard.registry

import dev.jason.gboardpatches.patches.gboard.features.packagerename.DEFAULT_STANDALONE_GBOARD_DISPLAY_NAME
import dev.jason.gboardpatches.patches.gboard.features.packagerename.gboardPackageRenameResourcePatch
import dev.jason.gboardpatches.patches.shared.Constants.GBOARD_PACKAGE_NAME
import dev.jason.gboardpatches.patches.shared.Constants.GBOARD_PATCHED_PACKAGE_NAME
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The patched keyboard must never be installed as an update to system Gboard. */
class GboardStandaloneInstallPatchContractTest {
    @Test
    fun `every admitted public patch forces package rename even when its UI toggle is off`() {
        val patches = GboardPublishedPatchCatalog.morpheRegistrations
        assertTrue(patches.isNotEmpty())
        assertTrue(patches.any { it.name == "Package Rename" })
        patches.forEach { patch ->
            assertTrue("${patch.name} can still overwrite stock Gboard", 
                gboardPackageRenameResourcePatch in patch.dependencies)
        }
    }

    @Test
    fun `default mod name and package identity differ from official Gboard`() {
        assertEquals("Gboard Mod", DEFAULT_STANDALONE_GBOARD_DISPLAY_NAME)
        assertEquals("Gboard Mod", gboardPackageRenamePatch.options["app_display_name"]?.default)
        assertEquals("com.google.android.inputmethod.latin", GBOARD_PACKAGE_NAME)
        assertEquals("dev.jason.com.google.android.inputmethod.latin", GBOARD_PATCHED_PACKAGE_NAME)
        assertFalse(GBOARD_PACKAGE_NAME == GBOARD_PATCHED_PACKAGE_NAME)
    }
}
