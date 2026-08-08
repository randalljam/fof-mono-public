// SOURCE: https://github.com/hannibal002/SkyHanni/blob/beta/src/main/java/at/hannibal2/skyhanni/api/event/HandleEvent.kt
//
// This is the @HandleEvent ANNOTATION — the core of SkyHanni's event system.
// Key things to notice:
//   - It's a Kotlin annotation class with default parameter values
//   - Supports filtering by SkyBlock status, specific islands, and priority
//   - Any function annotated with this in a @SkyHanniModule will be auto-registered
//   - The annotation processing happens at compile time via KSP

package at.hannibal2.skyhanni.api.event

import at.hannibal2.skyhanni.config.enums.OutsideSBFeature
import at.hannibal2.skyhanni.data.IslandType
import at.hannibal2.skyhanni.data.IslandTypeTag
import kotlin.reflect.KClass

@Retention(AnnotationRetention.RUNTIME)
@Target(AnnotationTarget.FUNCTION)
annotation class HandleEvent(
    val eventType: KClass<out SkyHanniEvent> = SkyHanniEvent::class,
    val eventTypes: Array<KClass<out SkyHanniEvent>> = [],

    // Only fire this handler when on Hypixel SkyBlock
    val onlyOnSkyblock: Boolean = false,

    // Fire on SkyBlock, OR outside SkyBlock if specific features are enabled
    val onlyOnSkyblockOrFeatures: Array<OutsideSBFeature> = [],

    // Only fire on a specific SkyBlock island
    val onlyOnIsland: IslandType = IslandType.ANY,

    // Only fire on islands within specific island type tags
    val onlyOnIslandTypeTag: Array<KClass<out IslandTypeTag>> = [],

    // Only fire on multiple specific islands
    vararg val onlyOnIslands: IslandType = [],

    // Lower priority executes first
    val priority: Int = 0,

    // If true, handler still fires even if the event was cancelled
    val receiveCancelled: Boolean = false,
) {
    companion object {
        const val HIGHEST = -2 // First to execute
        const val HIGH = -1
        const val LOW = 1
        const val LOWEST = 2 // Last to execute
    }
}
