import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import dev.jason.gboardpatches.extension.shared.Gboard1846MetadataArrays;

public final class MetadataArraysSelfTest {
    public static void main(String[] args) {
        CharSequence[] labels = {"ㄅ", "A"};
        if (!Gboard1846MetadataArrays.asList(labels).equals(Arrays.asList("ㄅ", "A")))
            throw new AssertionError("Native label array order was lost");
        Object first = new Object(), second = new Object();
        Object[] entries = {first, null, second};
        List<?> actions = Gboard1846MetadataArrays.asList(entries);
        if (actions.size() != 3 || actions.get(0) != first || actions.get(1) != null
                || actions.get(2) != second)
            throw new AssertionError("Native action objects were changed");
        List<String> existing = Collections.singletonList("existing");
        if (Gboard1846MetadataArrays.asList(existing) != existing)
            throw new AssertionError("List fallback was copied");
        for (Object invalid : new Object[] {null, 3, new int[] {1}}) {
            if (!Gboard1846MetadataArrays.asList(invalid).isEmpty())
                throw new AssertionError("Invalid metadata was accepted");
        }
        System.out.println("Metadata array regression checks passed");
    }
}
