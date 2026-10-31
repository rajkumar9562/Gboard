package dev.jason.gboardpatches.extension.shared;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/** Reads 18.4.6's native array metadata without changing the shared policies. */
public final class Gboard1846MetadataArrays {
    private Gboard1846MetadataArrays() {}

    public static List<?> asList(Object value) {
        if (value instanceof Object[]) return Arrays.asList((Object[]) value);
        if (value instanceof List<?>) return (List<?>) value;
        return Collections.emptyList();
    }
}
