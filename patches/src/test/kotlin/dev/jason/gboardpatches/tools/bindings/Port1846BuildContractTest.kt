package dev.jason.gboardpatches.tools.bindings

import com.google.gson.JsonParser
import java.nio.file.Files
import java.nio.file.Path
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class Port1846BuildContractTest {
    @Test
    fun `1846 partial bundle compiles with exact admission and artifact identity`() {
        val port = Path.of("../port-18.4.6")
        val compiled = GboardTargetBuildCompiler.compile(
            Files.readString(Path.of("src/main/resources/gboard/gboard-port-product-catalog.json")),
            Files.readString(port.resolve("port-bundle.json")),
            Files.readString(port.resolve("reviewed-bindings.json")),
        )
        val review = JsonParser.parseString(
            Files.readString(port.resolve("static-review.json")),
        ).asJsonObject
        val expected = review.getAsJsonArray("admitted_features").map { it.asString }.toSet()
        assertEquals("18.4.6", compiled.targetVersion)
        assertEquals(expected, compiled.admittedFeatureIds)
        assertEquals(34, compiled.admittedFeatureIds.size)
        assertEquals(127, compiled.requiredBindingKeys.size)
        assertEquals(listOf("18.4.6.985164140-release-arm64-v8a"), compiled.artifactIdentity.versionNames)
        assertEquals("APKM", compiled.artifactIdentity.apkFileType)
        assertEquals(
            setOf("f0fd6c5b410f25cb25c3b53346c8972fae30f8ee7411df910480ad6b2d60db83"),
            compiled.artifactIdentity.signatures,
        )
        assertTrue(compiled.bindingsKotlinSource.contains("Lodx;"))
        assertTrue(compiled.bindingsKotlinSource.contains("Lflx;"))
        assertTrue(compiled.bindingsKotlinSource.contains("Binding ocr_thin_init is unavailable"))
        assertFalse("advanced_voice_typing" in compiled.admittedFeatureIds)
        assertFalse("ai_writing_tools" in compiled.admittedFeatureIds)
        // Compare actual build output with the selected 18.4.6 port, rather
        // than with the historical 18.5.4 fixture used by compiler unit tests.
        val generatedDirectory = Path.of(
            "build/generated/sources/versionBindings/kotlin/main/dev/jason/" +
                "gboardpatches/patches/gboard/shared/generated",
        )
        assertEquals(
            compiled.bindingsKotlinSource,
            Files.readString(generatedDirectory.resolve("GboardVersionBindings.kt")),
        )
        assertEquals(
            compiled.admissionKotlinSource,
            Files.readString(generatedDirectory.resolve("GboardTargetAdmission.kt")),
        )
    }
}
