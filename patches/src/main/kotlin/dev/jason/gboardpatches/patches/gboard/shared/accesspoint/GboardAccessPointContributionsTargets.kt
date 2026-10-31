package dev.jason.gboardpatches.patches.gboard.shared.accesspoint

import dev.jason.gboardpatches.patches.gboard.shared.GboardMethodTarget

internal object GboardAccessPointContributionsTargets {
    val orderFactory = GboardMethodTarget(
        classType = "Lmow;",
        name = "n",
        parameterTypes = listOf(
            "Landroid/content/Context;",
            "Lncn;",
            "Lnsn;",
            "Lwgz;",
            "Lwgz;",
        ),
        returnType = "Lmow;",
    )

    val controllerConstructor = GboardMethodTarget(
        classType = "Lmqk;",
        name = "<init>",
        parameterTypes = listOf("Landroid/content/Context;", "Lmrt;"),
        returnType = "V",
    )
}
