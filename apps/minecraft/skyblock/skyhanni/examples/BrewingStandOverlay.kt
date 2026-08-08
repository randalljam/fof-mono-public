// SOURCE: https://github.com/hannibal002/SkyHanni/blob/beta/src/main/java/at/hannibal2/skyhanni/features/misc/BrewingStandOverlay.kt
//
// This is a SIMPLE example of a SkyHanni feature. It shows the core pattern:
//   1. Kotlin object (singleton) annotated with @SkyHanniModule
//   2. Event handler annotated with @HandleEvent
//   3. Config toggle check at the top of the handler
//   4. Modify the event to change what's rendered
//
// This feature adds text overlays to the Brewing Stand inventory UI.

package at.hannibal2.skyhanni.features.misc

import at.hannibal2.skyhanni.SkyHanniMod
import at.hannibal2.skyhanni.api.event.HandleEvent
import at.hannibal2.skyhanni.events.RenderInventoryItemTipEvent
import at.hannibal2.skyhanni.skyhannimodule.SkyHanniModule
import at.hannibal2.skyhanni.utils.compat.formattedTextCompatLeadingWhiteLessResets

@SkyHanniModule
object BrewingStandOverlay {

    @HandleEvent(onlyOnSkyblock = true)
    fun onRenderItemTip(event: RenderInventoryItemTipEvent) {
        // Guard clause: bail out if this feature is disabled in config
        if (!SkyHanniMod.feature.misc.brewingStandOverlay) return

        // Guard clause: only act when viewing a Brewing Stand
        if (event.inventoryName != "Brewing Stand") return

        val stack = event.stack
        val name = stack.hoverName.formattedTextCompatLeadingWhiteLessResets()

        val slotNumber = event.slot.index
        when (slotNumber) {
            13, // Ingredient input
            21, // Progress
            42, // Output right side
            -> Unit

            else -> return
        }

        if (slotNumber == 21) {
            event.offsetX = 55
        }

        // Hide the progress slot when not active
        if (name.contains(" or ")) return

        // Set the overlay text and position
        event.stackTip = name
        event.offsetX += 3
        event.offsetY = -5
        event.alignLeft = false
    }
}
