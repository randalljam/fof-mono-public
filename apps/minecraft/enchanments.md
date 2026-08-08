### Inconsistencies I found in the original AI list

| # | Issue                             | Details / Fix                                                                                                                                                                                                                                               |
| - | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | **Missing max-level information** | Only the new mace enchants (Density, Breach, Wind Burst) and Riptide listed levels; every other entry needs one.                                                                                                                                            |
| 2 | **Armor grouping wording**        | “Chest/Legs (general)” implies those enchants can’t go on helmets/boots, but the four Protection variants and Thorns can be applied to **any** armour piece. I’ve relabelled that block to “All Armour” and kept Swift Sneak called out as “leggings-only.” |
| 3 | **Universal section scope**       | Binding/Vanishing curses do **not** apply to every item type (they’re only for wearable gear and some curios). They are still “universal” enough for most players, so I left them but added a note.                                                         |
| 4 | **Weapon categories**             | Density/Breach/Wind Burst work only on the **mace**, not on all “melee weapons,” so that subsection heading is now “Mace-only (1.21).”                                                                                                                      |
| 5 | **Version tag**                   | The text said “Java 1.21.5”. Snapshot numbers aren’t final yet; the released spec is simply “Java 1.21.”                                                                                                                                                    |

Everything else (names, descriptions, item compatibility) matches the authoritative list you supplied.

---

## Updated AI list (now with a **K2 Level** column)

<details>
<summary>Click to expand</summary>

### Universal (most gear)

| Enchantment         | K2 Level | What it does                                                |
| ------------------- | --------- | ----------------------------------------------------------- |
| Mending             | **I**     | XP you pick up repairs the item instead of filling your bar |
| Unbreaking          | **III**   | Chance to *not* consume durability on use                   |
| Curse of Binding¹   | **I**     | Once worn, the item can’t be removed until you die/break it |
| Curse of Vanishing¹ | **I**     | Item disappears instead of dropping on death                |

<sub>¹Only applies to wearable gear & a few curios, not to every tool/weapon.</sub>

---

### Armour & Movement

#### Helmet

| Enchantment   | K2 Level | Effect                                       |
| ------------- | --------- | -------------------------------------------- |
| Respiration   | **III**   | Longer underwater breathing & clearer vision |
| Aqua Affinity | **I**     | Normal mining speed while underwater         |

#### All Armour (helmets, chestplates, leggings, boots)

| Enchantment           | K2 Level | Effect                                              |
| --------------------- | --------- | --------------------------------------------------- |
| Protection            | **IV**    | General damage reduction                            |
| Blast Protection      | **IV**    | Extra resistance to explosions                      |
| Fire Protection       | **IV**    | Cuts fire / lava damage & burn time                 |
| Projectile Protection | **IV**    | Reduces arrow, trident, ghast-fireball, etc. damage |
| Thorns                | **III**   | Returns damage to attackers                         |

#### Leggings-only

| Enchantment | K2 Level | Effect                               |
| ----------- | --------- | ------------------------------------ |
| Swift Sneak | **III**   | Sneak speed up to 75 % of walk speed |

#### Boots

| Enchantment     | K2 Level | Effect                                             |
| --------------- | --------- | -------------------------------------------------- |
| Feather Falling | **IV**    | Less fall & end-pearl damage                       |
| Depth Strider   | **III**   | Faster movement in water                           |
| Frost Walker    | **II**    | Freezes water beneath you; no magma-block burn     |
| Soul Speed      | **III**   | Sprint quickly on soul sand/soil (extra boot wear) |

---

### Tools (pickaxe, axe, shovel, hoe, shears)

| Enchantment | K2 Level | Effect                                                  |
| ----------- | --------- | ------------------------------------------------------- |
| Efficiency  | **V**     | Break blocks faster                                     |
| Fortune     | **III**   | More drops from ores, crops & some blocks               |
| Silk Touch  | **I**     | Harvest blocks “as-is” (glass, ores, bookshelves, etc.) |

---

### Swords & Other Melee Weapons

| Enchantment        | K2 Level | Effect                                   |
| ------------------ | --------- | ---------------------------------------- |
| Sharpness          | **V**     | Flat damage boost to everything          |
| Smite              | **V**     | Bonus damage to undead mobs              |
| Bane of Arthropods | **V**     | Bonus damage & Slowness to spiders, etc. |
| Sweeping Edge      | **III**   | Wider, stronger sweep attack (swords)    |
| Fire Aspect        | **II**    | Sets target on fire, cooks drops         |
| Knockback          | **II**    | Pushes mobs/players back                 |
| Looting            | **III**   | Extra/rarer mob drops                    |

#### Mace-only (1.21)

| Enchantment | K2 Level | Effect                                               |
| ----------- | --------- | ---------------------------------------------------- |
| Density     | **V**     | +0.5 ♥ smash damage per fallen block per level       |
| Breach      | **IV**    | Ignores 15 % of target armour per level (up to 60 %) |
| Wind Burst  | **III**   | After a smash, launches you upward 7 blocks/level    |

---

### Bow & Crossbow

| Enchantment             | K2 Level | Effect                                         |
| ----------------------- | --------- | ---------------------------------------------- |
| Power (bow)             | **V**     | More arrow damage                              |
| Punch (bow)             | **II**    | Extra knockback                                |
| Flame (bow)             | **I**     | Arrows ignite targets & light campfires        |
| Infinity (bow)          | **I**     | One arrow becomes unlimited shots (not tipped) |
| Quick Charge (crossbow) | **III**   | Faster reload                                  |
| Multishot (crossbow)    | **I**     | Fires 3 bolts for the cost of 1                |
| Piercing (crossbow)     | **IV**    | Bolts pass through up to 4 entities & shields  |

---

### Trident

| Enchantment | K2 Level | Effect                                                        |
| ----------- | --------- | ------------------------------------------------------------- |
| Loyalty     | **III**   | Trident returns after each throw                              |
| Riptide     | **III**   | Throwing in water/rain hurls *you* forward                    |
| Channeling  | **I**     | Lightning strike during thunderstorm on hit                   |
| Impaling    | **V**     | Extra damage to aquatic mobs (all mobs if in rain, Java-only) |

---

### Fishing Rod

| Enchantment     | K2 Level | Effect                             |
| --------------- | --------- | ---------------------------------- |
| Lure            | **III**   | Fish bite sooner                   |
| Luck of the Sea | **III**   | Higher treasure, lower junk chance |

</details>

---

#### Quick reference

*Universal Mending + Unbreaking keep everything durable, Protection variants tailor your armour, Efficiency/Fortune/Silk Touch optimise mining, weapon enchants specialise damage, bows & crossbows add power and utility, tridents grant mobility or storms, and 1.21’s Density/Breach/Wind Burst turn the new mace into a sky-high wrecking ball.*
