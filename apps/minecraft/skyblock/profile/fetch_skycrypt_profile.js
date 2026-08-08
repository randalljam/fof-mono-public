#!/usr/bin/env node
// Full SkyCrypt markdown report (maximize what the APIs return):
//   From repo root:  node minecraft/skyblock/profile/fetch_skycrypt_profile.js rjcomp Lemon
//   From this dir:  node fetch_skycrypt_profile.js rjcomp Lemon
// Use "all" instead of "Lemon" for one file per co-op profile. No extra flag turns on "more":
// the word "loadout" is a different mode (append a named loadout to the latest .md only).
// If /api/gear, /api/pets, etc. return HTTP 403 (Cloudflare), those sections are skipped; the
// /api/inventory/ dump still includes main inv, ender, vault, talisman/potion/fishing bags, etc.
//
// Loadout mode (optional): after a full run, re-equip in-game, then e.g.:
//   node fetch_skycrypt_profile.js rjcomp Lemon loadout Mining
// That appends a "Loadout: …" block to the most recent skycrypt_*.md for that profile; it
// does not produce the full report by itself.

const fs = require("fs");
const path = require("path");

// Usage:
//   Full profile (markdown):  node fetch_skycrypt_profile.js <username> [profile]
//   All profiles:             node fetch_skycrypt_profile.js <username> all
//   Add loadout section:     node fetch_skycrypt_profile.js <username> [profile] loadout <label>
//
// Armor/wardrobe/weapon *summaries* come from /api/gear (when not blocked). *Every* listed item
// in each storage bag is under ## Inventories from /api/inventory (when not blocked). Net worth
// always includes coin rollups by category.
//
// Examples:
//   node fetch_skycrypt_profile.js rjcomp              → Lemon (default) full profile
//   node fetch_skycrypt_profile.js rjcomp all         → all profiles, full report each
//   node fetch_skycrypt_profile.js rjcomp Lemon loadout Farming

const BASE_URL = "https://sky.shiiyu.moe/api";
const USERNAME = process.argv[2] || "rjcomp";
const PROFILE_FILTER = (process.argv[3] || "Lemon").toLowerCase();
const IS_LOADOUT = (process.argv[4] || "").toLowerCase() === "loadout";
const LOADOUT_LABEL = process.argv[5] || "Unnamed";
const DELAY_MS = 1000;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function dateStamp() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `_${yyyy}-${mm}-${dd}_${hh}${min}`;
}

const HEADERS = {
  "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
  Accept: "application/json",
};

async function fetchJSON(url) {
  const maxAttempts = 4;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const res = await fetch(url, { headers: HEADERS });
    if (res.ok) return res.json();
    const status = res.status;
    const retry = status === 429 || (status >= 500 && status < 600);
    if (retry && attempt < maxAttempts) {
      const wait = Math.min(12_000, 600 * 2 ** attempt);
      process.stdout.write(`  [HTTP ${status}, retry in ${(wait / 1000).toFixed(1)}s] `);
      await sleep(wait);
      continue;
    }
    throw new Error(`HTTP ${status} for ${url}`);
  }
}

async function fetchEndpoint(name, url) {
  try {
    process.stdout.write(`  Fetching ${name}...`);
    const data = await fetchJSON(url);
    await sleep(DELAY_MS);
    console.log(" OK");
    return data;
  } catch (err) {
    console.log(` SKIP (${err.message})`);
    return null;
  }
}

// ── Formatting ──

function fmt(n) {
  if (n == null) return "N/A";
  if (typeof n !== "number") return String(n);
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n % 1 === 0 ? n.toLocaleString("en-US") : n.toFixed(2);
}

function fmtCoins(n) {
  return fmt(n) + " coins";
}

function title(s) {
  if (!s) return "";
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function cleanName(s) {
  if (!s) return "Unknown";
  return s.replace(/§[0-9a-fk-or]/gi, "");
}

/** Two significant figures with K / M / B (for display of coin magnitudes). */
function fmtSig2(n) {
  if (n == null || !isFinite(n) || n < 0) return "—";
  if (n === 0) return "0";
  if (n < 1e3) return String(Math.round(n));
  if (n < 1e6) {
    const k = n / 1e3;
    return String(Number(k.toPrecision(2))) + "K";
  }
  if (n < 1e9) {
    const m = n / 1e6;
    return String(Number(m.toPrecision(2))) + "M";
  }
  const b = n / 1e9;
  return String(Number(b.toPrecision(2))) + "B";
}

const ITEM_VALUE_RE = /Item Value:\s*([0-9,]+)\s*Coins/i;
const SACK_CONTENTS_RE = /Sack Contents Value:\s*([0-9,]+)\s*Coins/i;

/**
 * For display: "Item Value" coins, optional "Sack Contents Value" coins, and a hint tag (BZ/AH/NPC) when lore says so.
 * Default SkyCrypt "Item Value" is tagged SC (internal estimate, not a live AH/BZ quote).
 */
function valueInfoFromLore(lore) {
  let itemValue = null;
  let contentsValue = null;
  if (!lore?.length) return { itemValue, contentsValue, subtag: "SC" };
  for (const line of lore) {
    const cl = cleanName(line);
    if (ITEM_VALUE_RE.test(cl)) {
      const m = cl.match(ITEM_VALUE_RE);
      if (m) itemValue = parseInt(m[1].replace(/,/g, ""), 10);
    }
    if (SACK_CONTENTS_RE.test(cl)) {
      const m = cl.match(SACK_CONTENTS_RE);
      if (m) contentsValue = parseInt(m[1].replace(/,/g, ""), 10);
    }
  }
  const blob = lore.map(cleanName).join(" ").toLowerCase();
  let subtag = "SC";
  if (/(bazaar|buy order|sell offer|insta\s*buy|insta\s*sell)/i.test(blob)) subtag = "BZ";
  else if (/(auction|lowest\s*bin|\/ah\b)/i.test(blob)) subtag = "AH";
  else if (/(npc|merchant|sell to)/i.test(blob) && /sell/i.test(blob)) subtag = "NPC";

  return { itemValue, contentsValue, subtag };
}

/**
 * For section total: use sack contents when present, else item value.
 */
function econPrimaryCoins(info) {
  if (info.contentsValue != null) return info.contentsValue;
  if (info.itemValue != null) return info.itemValue;
  return 0;
}

function maxEconInItemList(items) {
  let m = 0;
  for (const it of items) {
    if (!it || !it.display_name) continue;
    const e = econPrimaryCoins(valueInfoFromLore(it.lore));
    if (e > m) m = e;
  }
  return m;
}

function formatItemValueSuffix(info, italic) {
  const { itemValue, contentsValue, subtag } = info;
  const parts = [];
  if (itemValue != null) {
    parts.push(`${fmtSig2(itemValue)} ${subtag === "SC" ? "SC" : subtag} (Item)`);
  }
  if (contentsValue != null) {
    parts.push(`${fmtSig2(contentsValue)} Sack+ (contents)`);
  }
  if (parts.length === 0) return "";
  const text = ` — ${parts.join(" · ")}`;
  return italic ? ` — *${parts.join(" · ")}*` : text;
}

function bar(pct) {
  const p = Math.min(100, Math.max(0, pct));
  const filled = Math.round((p / 100) * 15);
  return "█".repeat(filled) + "░".repeat(15 - filled) + ` ${p.toFixed(1)}%`;
}

function msToTime(ms) {
  if (!ms || ms <= 0) return "—";
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
}

// ── Section Builders ──

function buildHeader(stats, uuid) {
  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });
  const timeStr = now.toLocaleTimeString("en-US", {
    hour: "2-digit", minute: "2-digit", second: "2-digit", timeZoneName: "short",
  });
  const rank = stats.rank;
  const rankDisplay = rank ? `[${rank.rankText}${rank.plusText || ""}]` : "";
  const profileName = stats.profile_cute_name;
  const joined = stats.joined ? new Date(stats.joined).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : "Unknown";

  let md = `## ${rankDisplay} ${stats.displayName} — Hypixel SkyBlock Profile\n\n`;
  md += `| Field | Value |\n|---|---|\n`;
  md += `| **Player** | ${stats.displayName} |\n`;
  md += `| **Rank** | ${rankDisplay || "None"} |\n`;
  md += `| **UUID** | \`${uuid}\` |\n`;
  md += `| **Profile** | ${profileName} (${stats.selected ? "Selected" : "Not Selected"}) |\n`;
  md += `| **Game Mode** | Normal |\n`;
  md += `| **First Joined** | ${joined} |\n`;
  md += `| **Co-op Members** | ${stats.members?.filter(m => !m.removed).map(m => m.username).join(", ") || "Solo"} |\n`;
  md += `| **Date Retrieved** | ${dateStr} |\n`;
  md += `| **Time Retrieved** | ${timeStr} |\n`;
  md += `| **Source** | [SkyCrypt](https://sky.shiiyu.moe/stats/${USERNAME}/${profileName}) |\n\n`;
  md += `---\n\n`;
  return md;
}

function buildOverview(stats) {
  if (!stats) return "";
  let md = `## Overview\n\n`;

  const sl = stats.skyblock_level;
  md += `- **SkyBlock Level:** ${sl?.level || "?"} / ${sl?.maxLevel || "?"}`;
  if (sl?.progress != null) md += ` ${bar(sl.progress * 100)}`;
  md += `\n`;
  md += `- **Purse:** ${fmtCoins(stats.purse)}\n`;
  md += `- **Bank:** ${fmtCoins(stats.bank)}\n`;
  if (stats.personalBank) md += `- **Personal Bank:** ${fmtCoins(stats.personalBank)}\n`;
  md += `- **Fairy Souls:** ${stats.fairySouls?.found || 0} / ${stats.fairySouls?.total || 267}\n`;

  const sk = stats.skills;
  if (sk) {
    md += `- **Skill Average:** ${sk.averageSkillLevel?.toFixed(1) || "?"} (${sk.averageSkillLevelWithProgress?.toFixed(2) || "?"})\n`;
    md += `- **Total Skill XP:** ${fmt(sk.totalSkillXp)}\n`;
  }

  md += `\n### All Profiles\n\n`;
  md += `| Profile | Game Mode | Selected |\n|---|---|---|\n`;
  for (const p of stats.profiles || []) {
    md += `| ${p.cute_name} | ${title(p.game_mode)} | ${p.selected ? "✅" : "—"} |\n`;
  }
  md += `\n`;
  return md;
}

function buildSkills(stats) {
  const sk = stats?.skills;
  if (!sk?.skills) return "";
  let md = `## Skills\n\n`;
  md += `| Skill | Level | K2 | XP | Progress |\n`;
  md += `|---|---|---|---|---|\n`;

  const order = ["farming", "mining", "combat", "foraging", "fishing", "enchanting", "alchemy", "taming", "carpentry", "runecrafting", "social", "hunting"];
  for (const name of order) {
    const s = sk.skills[name];
    if (!s) continue;
    md += `| ${title(name)} | ${s.level} | ${s.maxLevel} | ${fmt(s.xp)} | ${bar(s.progress * 100)} |\n`;
  }

  md += `\n- **Average Skill Level:** ${sk.averageSkillLevel?.toFixed(1)}\n`;
  md += `- **Total Skill XP:** ${fmt(sk.totalSkillXp)}\n\n`;
  return md;
}

function buildNetworth(nw) {
  if (!nw) return "";
  const data = nw.nonCosmetic || nw.normal || nw;
  if (!data?.networth) return "";

  let md = `## Net Worth\n\n`;
  md += `**Total Net Worth:** ${fmtCoins(data.networth)}\n`;
  md += `**Unsoulbound Net Worth:** ${fmtCoins(data.unsoulboundNetworth)}\n\n`;

  if (data.types) {
    md += `| Category | Value | Unsoulbound |\n|---|---|---|\n`;
    const sorted = Object.entries(data.types).sort((a, b) => b[1].total - a[1].total);
    for (const [name, info] of sorted) {
      if (info.total <= 0) continue;
      md += `| ${title(name)} | ${fmtCoins(info.total)} | ${fmtCoins(info.unsoulboundTotal)} |\n`;
    }
  }

  md += `\n| Source | Amount |\n|---|---|\n`;
  md += `| Purse | ${fmtCoins(data.purse)} |\n`;
  md += `| Bank | ${fmtCoins(data.bank)} |\n`;
  if (data.personalBank) md += `| Personal Bank | ${fmtCoins(data.personalBank)} |\n`;
  md += `\n`;
  return md;
}

/** Full bag dumps from /api/inventory/… (main inv, ender, vault, talisman, etc.) when SkyCrypt returns 200. */
function buildInventories(sections) {
  if (!Array.isArray(sections) || sections.length === 0) return "";
  let md = `## Inventories (all bags & storage)\n\n`;
  md += `SkyCrypt \`/api/inventory/\`: **SC** = *Item Value* (site estimate). **Sack+** = *Sack Contents Value* when that line exists. **BZ** / **AH** / **NPC** only if the item lore mentions them. Totals use Sack+ when present, else Item Value (2 significant figures, e.g. 440K, 3.0M, 620M). Missing *Item Value* rows = no number in the API (e.g. soulbound Ender gear, many potions). Sacks that look “too cheap” are usually *Item* (empty sack) vs *Sack+* (contents); bazaar instant-sell can still differ from SkyCrypt.\n\n`;

  const ENDER_PAGE = 45;

  for (const sec of sections) {
    const name = sec.name || "Unknown";
    const items = sec.items;
    if (!items || items.length === 0) {
      md += `### ${name}\n\n*Empty.*\n\n`;
      continue;
    }

    let sumCoins = 0;
    for (const it of items) {
      if (!it || !it.display_name) continue;
      const vi = valueInfoFromLore(it.lore);
      sumCoins += econPrimaryCoins(vi);
    }

    const showSum = name !== "Search";
    const totalBit = showSum && sumCoins > 0 ? ` · ${fmtSig2(sumCoins)} total` : "";
    md += `### ${name} (${items.length} items${totalBit})\n\n`;
    if (name === "Potion Bag") {
      md += `*Most potions have no Item Value in SkyCrypt.*\n\n`;
    }
    if (name === "Sacks") {
      md += `*Header total = Sack+ (contents) when in lore, else Item (empty sack).*\n\n`;
    }

    if (name === "Ender Chest") {
      for (let p = 0; p * ENDER_PAGE < items.length; p++) {
        const slice = items.slice(p * ENDER_PAGE, (p + 1) * ENDER_PAGE);
        let pageSum = 0;
        for (const it of slice) {
          if (!it || !it.display_name) continue;
          pageSum += econPrimaryCoins(valueInfoFromLore(it.lore));
        }
        const pageMaxE = maxEconInItemList(slice);
        md += `#### Page ${p + 1} · ${fmtSig2(pageSum)} page total\n\n`;
        for (const it of slice) {
          if (!it || !it.display_name) continue;
          const vi = valueInfoFromLore(it.lore);
          const e = econPrimaryCoins(vi);
          const doItalic = pageMaxE > 0 && e === pageMaxE;
          const base = `- **${cleanName(it.display_name)}** (${title(it.rarity || "unknown")})`;
          const suff = formatItemValueSuffix(vi, doItalic);
          md += suff ? `${base}${suff}\n` : `${base}\n`;
        }
        md += `\n`;
      }
      continue;
    }

    const sectionMaxE = maxEconInItemList(items);
    for (const it of items) {
      if (!it || !it.display_name) continue;
      const vi = valueInfoFromLore(it.lore);
      const e = econPrimaryCoins(vi);
      const doItalic = sectionMaxE > 0 && e === sectionMaxE;
      const base = `- **${cleanName(it.display_name)}** (${title(it.rarity || "unknown")})`;
      const suff = formatItemValueSuffix(vi, doItalic);
      md += suff ? `${base}${suff}\n` : `${base}\n`;
    }
    md += `\n`;
  }
  return md;
}

function buildGear(gear) {
  if (!gear) return "";
  let md = `## Armor, Equipment & Weapons\n\n`;

  // Current (equipped) armor
  if (gear.armor?.armor) {
    md += `### Active Armor — ${gear.armor.set_name || "Mixed"} (${title(gear.armor.set_rarity || "")})\n\n`;
    const slotNames = ["Helmet", "Chestplate", "Leggings", "Boots"];
    const armorPieces = gear.armor.armor;
    for (const [idx, piece] of Object.entries(armorPieces)) {
      const slot = slotNames[idx] || `Slot ${idx}`;
      md += `- **${slot}:** ${cleanName(piece.display_name)} (${title(piece.rarity)})\n`;
    }
    if (gear.armor.stats) {
      md += `\n**Set Stats:**\n`;
      for (const [stat, val] of Object.entries(gear.armor.stats)) {
        md += `- ${title(stat)}: ${typeof val === "number" ? (val > 0 ? "+" : "") + fmt(val) : val}\n`;
      }
    }
    md += `\n`;
  }

  // Wardrobe (non-active armor sets)
  if (gear.wardrobe) {
    const slotNames = ["Helmet", "Chestplate", "Leggings", "Boots"];
    const wardrobeSets = [];

    for (let i = 0; i < 18; i++) {
      const slot = gear.wardrobe[String(i)];
      if (!Array.isArray(slot)) continue;
      const pieces = slot.filter(p => p && p.display_name);
      if (pieces.length === 0) continue;
      wardrobeSets.push({ slotNum: i + 1, pieces });
    }

    if (wardrobeSets.length > 0) {
      md += `### Wardrobe — Non-Active Armor Sets (${wardrobeSets.length} slots)\n\n`;
      for (const { slotNum, pieces } of wardrobeSets) {
        md += `**Slot ${slotNum}:**\n`;
        for (const piece of pieces) {
          const name = cleanName(piece.display_name);
          const slotType = slotNames.find(s => name.toLowerCase().includes(s.toLowerCase()))
            || (name.match(/Helmet|Hat|Fedora|Crown|Hood|Mask/i) ? "Helmet"
            : name.match(/Chestplate|Suit|Jacket|T-Shirt/i) ? "Chestplate"
            : name.match(/Leggings|Trousers|Pants/i) ? "Leggings"
            : name.match(/Boots|Shoes/i) ? "Boots" : "");
          md += `- ${cleanName(piece.display_name)} (${title(piece.rarity)})`;
          if (piece.lore?.length > 0) {
            const statLines = piece.lore.filter(l => l.match(/§[0-9a-f](?:Health|Defense|Strength|Speed|Intelligence|Crit)/i)).slice(0, 3);
            if (statLines.length > 0) {
              md += ` — ${statLines.map(l => cleanName(l).trim()).join(", ")}`;
            }
          }
          md += `\n`;
        }
        md += `\n`;
      }
    }
  }

  // Equipment (necklace, cloak, belt, gloves)
  if (gear.equipment) {
    const eqSlotNames = ["Gloves", "Belt", "Cloak", "Necklace"];
    const eqData = gear.equipment.equipment || gear.equipment;
    const eqList = Array.isArray(eqData) ? eqData : Object.values(eqData);
    const validEq = eqList.filter(e => e && e.display_name);

    if (validEq.length > 0) {
      md += `### Equipment (Necklace, Cloak, Belt, Gloves)\n\n`;
      for (const eq of validEq) {
        md += `- **${cleanName(eq.display_name)}** (${title(eq.rarity)})`;
        if (eq.lore?.length > 0) {
          const statLines = eq.lore.filter(l => /§[0-9a-f].*:/.test(l) && !l.includes("§l") && !l.includes("Obtained") && !l.includes("Item Value")).slice(0, 3);
          if (statLines.length > 0) {
            md += ` — ${statLines.map(l => cleanName(l).trim()).join(", ")}`;
          }
        }
        md += `\n`;
      }

      if (gear.equipment.stats) {
        md += `\n**Equipment Stats:**\n`;
        for (const [stat, val] of Object.entries(gear.equipment.stats)) {
          md += `- ${title(stat)}: ${typeof val === "number" ? (val > 0 ? "+" : "") + fmt(val) : val}\n`;
        }
      }
      md += `\n`;
    }
  }

  // Weapons (items in inventory classified as weapons by SkyCrypt)
  if (gear.weapons?.weapons) {
    md += `### Weapons (Inventory)\n\n`;
    const weapons = gear.weapons.weapons;
    if (gear.weapons.highest_priority_weapon) {
      md += `*Highest priority: ${cleanName(gear.weapons.highest_priority_weapon.display_name)}*\n\n`;
    }
    for (const w of weapons) {
      md += `- **${cleanName(w.display_name)}** (${title(w.rarity)})`;
      if (w.lore?.length > 0) {
        const dmgLine = w.lore.find(l => l.includes("Damage:"));
        if (dmgLine) md += ` — ${cleanName(dmgLine).trim()}`;
      }
      md += `\n`;
    }
    md += `\n`;
  }

  return md;
}

function buildAccessories(acc) {
  if (!acc) return "";
  let md = `## Accessories\n\n`;
  md += `- **Unique:** ${acc.unique || 0}\n`;
  md += `- **Total:** ${acc.total || 0}\n`;
  md += `- **Recombobulated:** ${acc.recombobulated || 0} / ${acc.totalRecombobulated || 0}\n`;
  md += `- **Selected Power:** ${acc.selectedPower || "None"}\n`;
  const mp = acc.magicalPower;
  md += `- **Magical Power:** ${typeof mp === "object" ? fmt(mp.total) : fmt(mp)}\n\n`;

  if (acc.stats) {
    md += `### Accessory Stats\n\n`;
    md += `| Stat | Bonus |\n|---|---|\n`;
    for (const [stat, val] of Object.entries(acc.stats)) {
      md += `| ${title(stat)} | ${val > 0 ? "+" : ""}${val} |\n`;
    }
    md += `\n`;
  }

  if (acc.accessories?.length > 0) {
    const byRarity = {};
    for (const a of acc.accessories) {
      const r = a.rarity || "unknown";
      if (!byRarity[r]) byRarity[r] = [];
      byRarity[r].push(a);
    }
    const order = ["mythic", "legendary", "epic", "rare", "uncommon", "common"];
    for (const rarity of order) {
      const items = byRarity[rarity];
      if (!items) continue;
      md += `### ${title(rarity)} (${items.length})\n\n`;
      for (const a of items) {
        const inactive = a.isInactive ? " *(inactive)*" : "";
        md += `- ${cleanName(a.display_name)}${inactive}\n`;
      }
      md += `\n`;
    }
  }

  return md;
}

function buildPets(pets) {
  if (!pets) return "";
  let md = `## Pets\n\n`;
  md += `- **Owned:** ${pets.amount || 0} / ${pets.total || 0}\n`;
  md += `- **Pet Score:** ${pets.petScore?.amount || 0} (Magic Find: +${pets.petScore?.stats?.magic_find || 0})\n`;
  md += `- **Total Pet XP:** ${fmt(pets.totalPetExp)}\n\n`;

  if (pets.pets?.length > 0) {
    md += `| Pet | Rarity | Level | Active |\n|---|---|---|---|\n`;
    const sorted = [...pets.pets].sort((a, b) => (b.level || 0) - (a.level || 0));
    for (const p of sorted) {
      const active = p.active ? "✅" : "";
      const petName = p.display_name || p.name || title(p.type);
      md += `| ${petName} | ${title(p.rarity)} | ${p.level || "?"} | ${active} |\n`;
    }
    md += `\n`;
  }

  return md;
}

function buildDungeons(dng) {
  if (!dng) return "";
  let md = `## Dungeons\n\n`;

  const lvl = dng.level;
  if (lvl) {
    md += `- **Catacombs Level:** ${lvl.level} / ${lvl.maxLevel} (${fmt(lvl.xp)} XP)\n`;
    md += `- **Progress:** ${bar(lvl.progress * 100)}\n\n`;
  }

  if (dng.classes) {
    md += `### Classes\n\n`;
    md += `- **Selected Class:** ${title(dng.classes.selectedClass)}\n`;
    md += `- **Class Average:** ${dng.classes.classAverage?.toFixed(1)}\n\n`;
    md += `| Class | Level | XP | Progress |\n|---|---|---|---|\n`;
    for (const [name, c] of Object.entries(dng.classes.classes || {})) {
      md += `| ${title(name)} | ${c.level} | ${fmt(c.xp)} | ${bar(c.progress * 100)} |\n`;
    }
    md += `\n`;
  }

  if (dng.catacombs?.length > 0) {
    md += `### Floor Completions\n\n`;
    md += `| Floor | Completions | Best Score | Fastest Time |\n|---|---|---|---|\n`;
    for (const floor of dng.catacombs) {
      const s = floor.stats || {};
      md += `| ${floor.name} | ${s.tier_completions ?? 0} | ${s.best_score ?? "—"} | ${msToTime(s.fastest_time)} |\n`;
    }
    md += `\n`;
  }

  if (dng.master_catacombs?.length > 0) {
    md += `### Master Mode\n\n`;
    md += `| Floor | Completions | Best Score | Fastest Time |\n|---|---|---|---|\n`;
    for (const floor of dng.master_catacombs) {
      const s = floor.stats || {};
      md += `| ${floor.name} | ${s.tier_completions ?? 0} | ${s.best_score ?? "—"} | ${msToTime(s.fastest_time)} |\n`;
    }
    md += `\n`;
  }

  return md;
}

function buildSlayers(slayer) {
  if (!slayer) return "";
  let md = `## Slayers\n\n`;
  md += `- **Total Slayer XP:** ${fmt(slayer.totalSlayerExp)}\n\n`;

  md += `| Slayer | Boss Name | Level | K2 | XP | Total Kills |\n|---|---|---|---|---|---|\n`;
  for (const [id, data] of Object.entries(slayer.data || {})) {
    md += `| ${title(id)} | ${data.name} | ${data.level?.level ?? 0} | ${data.level?.maxLevel ?? "?"} | ${fmt(data.level?.xp)} | ${data.kills?.total ?? 0} |\n`;
  }

  if (slayer.data) {
    md += `\n### Kill Breakdown\n\n`;
    for (const [id, data] of Object.entries(slayer.data)) {
      if (!data.kills || data.kills.total === 0) continue;
      md += `**${data.name}:**`;
      for (const [tier, count] of Object.entries(data.kills)) {
        if (tier === "total") continue;
        if (count > 0) md += ` T${tier}: ${count}`;
      }
      md += `\n`;
    }
  }
  md += `\n`;
  return md;
}

function buildMinions(minions) {
  if (!minions) return "";
  let md = `## Minions\n\n`;
  md += `- **Total Unique Minions:** ${minions.totalMinions}\n`;
  md += `- **Maxed Minions:** ${minions.maxedMinions}\n`;
  md += `- **Crafted Tiers:** ${minions.totalTiers} / ${minions.maxedTiers}\n`;
  md += `- **Minion Slots:** ${minions.minionsSlots?.current ?? "?"} (next at ${minions.minionsSlots?.next ?? "?"})\n\n`;

  const categories = minions.minions;
  if (typeof categories === "object" && !Array.isArray(categories)) {
    for (const [cat, data] of Object.entries(categories)) {
      const craftedMinions = data.minions?.filter(m => m.tiers?.length > 0) || [];
      if (craftedMinions.length === 0) continue;
      md += `### ${title(cat)}\n\n`;
      md += `| Minion | Crafted Tiers | K2 Tier |\n|---|---|---|\n`;
      for (const m of craftedMinions) {
        md += `| ${m.name} | ${m.tiers.join(", ")} | ${m.maxTier} |\n`;
      }
      md += `\n`;
    }
  }

  return md;
}

function buildCollections(col) {
  if (!col) return "";
  let md = `## Collections\n\n`;
  md += `- **Total Collections Unlocked:** ${col.totalCollections}\n`;
  md += `- **Maxed Collections:** ${col.maxedCollections}\n\n`;

  for (const [catName, catData] of Object.entries(col.categories || {})) {
    md += `### ${catData.name || title(catName)}\n\n`;
    md += `| Item | Amount | Tier | K2 Tier |\n|---|---|---|---|\n`;
    for (const item of catData.items || []) {
      const tierStr = item.tier > 0 ? String(item.tier) : "—";
      md += `| ${item.name || title(item.id)} | ${fmt(item.totalAmount ?? item.amount)} | ${tierStr} | ${item.maxTier} |\n`;
    }
    md += `\n`;
  }

  return md;
}

function buildBestiary(best) {
  if (!best) return "";
  let md = `## Bestiary\n\n`;
  md += `- **Bestiary Level:** ${best.level?.toFixed(1) ?? "?"} / ${best.maxLevel?.toFixed(1) ?? "?"}\n`;
  md += `- **Families Unlocked:** ${best.familiesUnlocked} / ${best.totalFamilies}\n`;
  md += `- **Families Completed:** ${best.familiesCompleted}\n`;
  md += `- **Family Tiers:** ${best.familyTiers} / ${best.maxFamilyTiers}\n\n`;

  for (const [catId, catData] of Object.entries(best.categories || {})) {
    const activeMobs = catData.mobs?.filter(m => m.kills > 0) || [];
    if (activeMobs.length === 0) continue;

    md += `### ${catData.name || title(catId)}\n\n`;
    md += `| Mob | Kills | Tier | K2 Tier |\n|---|---|---|---|\n`;
    for (const mob of activeMobs) {
      md += `| ${mob.name} | ${fmt(mob.kills)} | ${mob.tier} | ${mob.maxTier} |\n`;
    }
    md += `\n`;
  }

  return md;
}

function buildCrimsonIsle(ci) {
  if (!ci) return "";
  let md = `## Crimson Isle\n\n`;

  md += `### Factions\n\n`;
  md += `- **Selected Faction:** ${ci.factions?.selectedFaction || "None"}\n`;
  md += `- **Barbarians Reputation:** ${ci.factions?.barbariansReputation ?? 0}\n`;
  md += `- **Mages Reputation:** ${ci.factions?.magesReputation ?? 0}\n\n`;

  if (ci.kuudra) {
    md += `### Kuudra\n\n`;
    md += `- **Total Kills:** ${ci.kuudra.totalKills}\n\n`;
    if (ci.kuudra.tiers?.length > 0) {
      md += `| Tier | Kills |\n|---|---|\n`;
      for (const t of ci.kuudra.tiers) {
        md += `| ${t.name} | ${t.kills} |\n`;
      }
      md += `\n`;
    }
  }

  if (ci.dojo) {
    md += `### Dojo\n\n`;
    md += `- **Total Points:** ${ci.dojo.totalPoints}\n\n`;
    if (ci.dojo.challenges?.length > 0) {
      md += `| Challenge | Points | Rank |\n|---|---|---|\n`;
      for (const c of ci.dojo.challenges) {
        md += `| ${c.name} | ${c.points} | ${c.rank} |\n`;
      }
      md += `\n`;
    }
  }

  return md;
}

function buildRift(rift) {
  if (!rift) return "";
  let md = `## The Rift\n\n`;
  md += `- **Visits:** ${rift.visits ?? 0}\n`;
  md += `- **Motes Purse:** ${fmt(rift.motes?.purse)}\n`;
  md += `- **Lifetime Motes:** ${fmt(rift.motes?.lifetime)}\n`;
  md += `- **Motes Orbs:** ${rift.motes?.orbs ?? 0}\n\n`;

  md += `### Enigma\n\n`;
  md += `- **Souls Found:** ${rift.enigma?.souls ?? 0} / ${rift.enigma?.totalSouls ?? 52}\n\n`;

  md += `### Castle\n\n`;
  md += `- **Grubber Stacks:** ${rift.castle?.grubberStacks ?? 0}\n`;
  md += `- **K2 Burgers:** ${rift.castle?.maxBurgers ?? 0}\n\n`;

  if (rift.timecharms) {
    md += `### Timecharms\n\n`;
    md += `- **Found:** ${rift.timecharms.timecharmsFound ?? 0}\n\n`;
    if (rift.timecharms.timecharms?.length > 0) {
      md += `| Timecharm | Unlocked |\n|---|---|\n`;
      for (const tc of rift.timecharms.timecharms) {
        md += `| ${tc.name} | ${tc.unlocked ? "✅" : "❌"} |\n`;
      }
      md += `\n`;
    }
  }

  return md;
}

function buildMisc(misc) {
  if (!misc) return "";
  let md = `## Miscellaneous\n\n`;

  if (misc.essence?.length > 0) {
    md += `### Essence\n\n`;
    md += `| Type | Amount |\n|---|---|\n`;
    for (const e of misc.essence) {
      md += `| ${e.name} | ${fmt(e.amount)} |\n`;
    }
    md += `\n`;
  }

  if (misc.kills) {
    md += `### Combat Stats\n\n`;
    md += `- **Total Kills:** ${fmt(misc.kills.total_kills)}\n`;
    md += `- **Total Deaths:** ${fmt(misc.kills.total_deaths)}\n`;
    md += `- **K/D Ratio:** ${misc.kills.total_deaths > 0 ? (misc.kills.total_kills / misc.kills.total_deaths).toFixed(1) : "∞"}\n\n`;

    if (misc.kills.kills?.length > 0) {
      md += `**Top 15 Mob Kills:**\n\n`;
      md += `| Mob | Kills |\n|---|---|\n`;
      const sorted = [...misc.kills.kills].sort((a, b) => b.amount - a.amount);
      for (const k of sorted.slice(0, 15)) {
        md += `| ${k.name} | ${fmt(k.amount)} |\n`;
      }
      md += `\n`;
    }
    if (misc.kills.deaths?.length > 0) {
      md += `**Top 10 Death Causes:**\n\n`;
      md += `| Cause | Deaths |\n|---|---|\n`;
      const sorted = [...misc.kills.deaths].sort((a, b) => b.amount - a.amount);
      for (const d of sorted.slice(0, 10)) {
        md += `| ${d.name} | ${fmt(d.amount)} |\n`;
      }
      md += `\n`;
    }
  }

  if (misc.gifts) {
    md += `### Gifts\n\n`;
    md += `- **Given:** ${misc.gifts.given ?? 0}\n`;
    md += `- **Received:** ${misc.gifts.received ?? 0}\n\n`;
  }

  if (misc.damage) {
    md += `### Damage Records\n\n`;
    if (typeof misc.damage === "object") {
      for (const [key, val] of Object.entries(misc.damage)) {
        md += `- **${title(key)}:** ${fmt(val)}\n`;
      }
    }
    md += `\n`;
  }

  if (misc.dragons) {
    md += `### Dragons\n\n`;
    if (typeof misc.dragons === "object") {
      for (const [key, val] of Object.entries(misc.dragons)) {
        if (typeof val === "number") md += `- **${title(key)}:** ${fmt(val)}\n`;
      }
    }
    md += `\n`;
  }

  if (misc.profile_upgrades) {
    md += `### Profile Upgrades\n\n`;
    if (Array.isArray(misc.profile_upgrades)) {
      for (const u of misc.profile_upgrades) {
        md += `- **${u.name || title(u.id || "")}:** Tier ${u.tier ?? u.amount ?? "?"}\n`;
      }
    } else if (typeof misc.profile_upgrades === "object") {
      for (const [k, v] of Object.entries(misc.profile_upgrades)) {
        md += `- **${title(k)}:** ${typeof v === "object" ? JSON.stringify(v) : v}\n`;
      }
    }
    md += `\n`;
  }

  if (misc.auctions) {
    md += `### Auctions\n\n`;
    if (typeof misc.auctions === "object") {
      for (const [k, v] of Object.entries(misc.auctions)) {
        if (typeof v === "number") md += `- **${title(k)}:** ${fmt(v)}\n`;
      }
    }
    md += `\n`;
  }

  if (misc.pet_milestones) {
    md += `### Pet Milestones\n\n`;
    if (typeof misc.pet_milestones === "object") {
      for (const [k, v] of Object.entries(misc.pet_milestones)) {
        if (typeof v === "object" && v !== null) {
          md += `- **${title(k)}:** ${fmt(v.amount ?? v.total ?? 0)} (${title(v.rarity || "")}, ${v.progress || ""})\n`;
        } else {
          md += `- **${title(k)}:** ${v}\n`;
        }
      }
    }
    md += `\n`;
  }

  return md;
}

function buildSkillDetails(skillsEndpoint) {
  if (!skillsEndpoint) return "";
  let md = `## Skill Details\n\n`;

  for (const [skillGroup, data] of Object.entries(skillsEndpoint)) {
    md += `### ${title(skillGroup)}\n\n`;
    if (data.level) {
      md += `- **Heart of the Mountain Level:** ${data.level.level} / ${data.level.maxLevel}\n`;
      md += `- **XP:** ${fmt(data.level.xp)} (${bar(data.level.progress * 100)})\n\n`;
    }
    if (data.miningLevel) {
      md += `- **Mining Level:** ${data.miningLevel.level}\n\n`;
    }
  }

  return md;
}

function buildPlayerStats(ps) {
  if (!ps?.stats) return "";
  let md = `## Player Stats\n\n`;
  md += `| Stat | Base | Total |\n|---|---|---|\n`;

  const sorted = Object.entries(ps.stats).sort((a, b) => a[0].localeCompare(b[0]));
  for (const [stat, val] of sorted) {
    if (typeof val === "object" && val !== null) {
      if (val.total === 0 && val.base === 0) continue;
      md += `| ${title(stat)} | ${fmt(val.base ?? 0)} | ${fmt(val.total ?? 0)} |\n`;
    } else {
      md += `| ${title(stat)} | — | ${typeof val === "number" ? fmt(val) : val} |\n`;
    }
  }
  md += `\n`;
  return md;
}

function buildLoadoutSection(label, gear) {
  if (!gear) return "";
  const now = new Date();
  const timeStr = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  const dateStr = now.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  const slotNames = ["Helmet", "Chestplate", "Leggings", "Boots"];

  let md = `\n### Loadout: ${label}\n\n`;
  md += `*Captured: ${dateStr} at ${timeStr}*\n\n`;

  if (gear.armor?.armor) {
    md += `**Armor — ${gear.armor.set_name || "Mixed"} (${title(gear.armor.set_rarity || "")}):**\n`;
    for (const [idx, piece] of Object.entries(gear.armor.armor)) {
      const slot = slotNames[idx] || `Slot ${idx}`;
      md += `- **${slot}:** ${cleanName(piece.display_name)} (${title(piece.rarity)})`;
      if (piece.lore?.length > 0) {
        const statLines = piece.lore.filter(l => l.match(/§[0-9a-f].*(?:Health|Defense|Strength|Speed|Intelligence|Crit|Fortune|Bonus Pest)/i)).slice(0, 3);
        if (statLines.length > 0) md += ` — ${statLines.map(l => cleanName(l).trim()).join(", ")}`;
      }
      md += `\n`;
    }
    if (gear.armor.stats) {
      md += `\n**Set Stats:** `;
      const statParts = [];
      for (const [stat, val] of Object.entries(gear.armor.stats)) {
        statParts.push(`${title(stat)}: ${val > 0 ? "+" : ""}${fmt(val)}`);
      }
      md += statParts.join(" | ") + `\n`;
    }
    md += `\n`;
  }

  if (gear.equipment) {
    const eqData = gear.equipment.equipment || gear.equipment;
    const eqList = Array.isArray(eqData) ? eqData : Object.values(eqData);
    const validEq = eqList.filter(e => e && e.display_name);
    if (validEq.length > 0) {
      md += `**Equipment:**\n`;
      for (const eq of validEq) {
        md += `- **${cleanName(eq.display_name)}** (${title(eq.rarity)})`;
        if (eq.lore?.length > 0) {
          const statLines = eq.lore.filter(l => /§[0-9a-f].*:/.test(l) && !l.includes("§l") && !l.includes("Obtained") && !l.includes("Item Value")).slice(0, 3);
          if (statLines.length > 0) md += ` — ${statLines.map(l => cleanName(l).trim()).join(", ")}`;
        }
        md += `\n`;
      }
      if (gear.equipment.stats) {
        md += `\n**Equipment Stats:** `;
        const statParts = [];
        for (const [stat, val] of Object.entries(gear.equipment.stats)) {
          statParts.push(`${title(stat)}: ${val > 0 ? "+" : ""}${fmt(val)}`);
        }
        md += statParts.join(" | ") + `\n`;
      }
      md += `\n`;
    }
  }

  return md;
}

function findMostRecentFile(username, profileName) {
  const dir = __dirname;
  const prefix = `skycrypt_${username}_${profileName}`;
  const files = fs.readdirSync(dir)
    .filter(f => f.startsWith(prefix) && f.endsWith(".md"))
    .sort()
    .reverse();
  return files.length > 0 ? path.join(dir, files[0]) : null;
}

// ── Main ──

async function main() {
  console.log(`\n  SkyCrypt Profile Fetcher`);
  console.log(`  =======================\n`);
  console.log(`  Player: ${USERNAME}`);
  if (IS_LOADOUT) {
    console.log(`  Mode: Add loadout "${LOADOUT_LABEL}"`);
  }
  console.log(`  Profile filter: ${PROFILE_FILTER === "all" ? "All profiles" : PROFILE_FILTER}\n`);

  // Step 1: UUID
  console.log("Step 1: Resolving UUID...");
  const uuidData = await fetchJSON(`${BASE_URL}/uuid/${USERNAME}`);
  const uuid = uuidData.uuid || uuidData.id || uuidData;
  console.log(`  UUID: ${uuid}\n`);
  await sleep(DELAY_MS);

  // Step 2: Stats (includes profile list and skills)
  console.log("Step 2: Fetching main stats...");
  const stats = await fetchJSON(`${BASE_URL}/stats/${uuid}`);
  const profileId = stats.profile_id;
  const profileName = stats.profile_cute_name;
  console.log(`  Profile: ${profileName} (${profileId})\n`);
  await sleep(DELAY_MS);

  // Determine which profiles to fetch
  const allProfiles = stats.profiles || [];
  let profilesToFetch;
  if (PROFILE_FILTER === "all") {
    profilesToFetch = allProfiles;
  } else {
    profilesToFetch = allProfiles.filter(p => p.cute_name.toLowerCase() === PROFILE_FILTER);
    if (profilesToFetch.length === 0) {
      const available = allProfiles.map(p => p.cute_name).join(", ");
      throw new Error(`Profile "${PROFILE_FILTER}" not found. Available: ${available}`);
    }
  }

  console.log(`  Fetching ${profilesToFetch.length} profile(s): ${profilesToFetch.map(p => p.cute_name).join(", ")}\n`);

  // ── Loadout mode: fetch only gear and append to most recent file ──
  if (IS_LOADOUT) {
    for (const profile of profilesToFetch) {
      const pId = profile.profile_id;
      const pName = profile.cute_name;

      const targetFile = findMostRecentFile(USERNAME, pName);
      if (!targetFile) {
        console.log(`  No existing file found for ${USERNAME}/${pName}. Run a full profile first.`);
        continue;
      }

      console.log(`  Target file: ${path.basename(targetFile)}`);

      const existing = fs.readFileSync(targetFile, "utf-8");
      const loadoutHeading = `### Loadout: ${LOADOUT_LABEL}`;
      if (existing.includes(loadoutHeading)) {
        console.log(`  Loadout "${LOADOUT_LABEL}" already exists in this file. Skipping.`);
        continue;
      }

      console.log(`  Fetching current gear for "${LOADOUT_LABEL}" loadout...`);
      const gear = await fetchEndpoint("Gear", `${BASE_URL}/gear/${uuid}/${pId}`);
      if (!gear) {
        console.log(`  Could not fetch gear. Skipping.`);
        continue;
      }

      const loadoutMd = buildLoadoutSection(LOADOUT_LABEL, gear);

      const footer = existing.lastIndexOf("\n---\n");
      let updated;
      if (footer !== -1) {
        updated = existing.slice(0, footer) + loadoutMd + existing.slice(footer);
      } else {
        updated = existing + loadoutMd;
      }

      fs.writeFileSync(targetFile, updated, "utf-8");
      console.log(`  Added "${LOADOUT_LABEL}" loadout to: ${path.basename(targetFile)}`);
    }

    console.log("\n  Done!\n");
    return;
  }

  // ── Full profile mode ──
  const endpoints = [
    ["networth", "Net Worth"],
    ["inventory", "Storage (all bags)"],
    ["gear", "Gear"],
    ["accessories", "Accessories"],
    ["pets", "Pets"],
    ["dungeons", "Dungeons"],
    ["slayer", "Slayers"],
    ["minions", "Minions"],
    ["collections", "Collections"],
    ["bestiary", "Bestiary"],
    ["crimson_isle", "Crimson Isle"],
    ["rift", "The Rift"],
    ["misc", "Miscellaneous"],
    ["skills", "Skill Details"],
    ["playerStats", "Player Stats"],
  ];

  for (const profile of profilesToFetch) {
    const pId = profile.profile_id;
    const pName = profile.cute_name;

    console.log(`\n--- Fetching profile: ${pName} ---`);
    const pStats = await fetchJSON(`${BASE_URL}/stats/${uuid}/${pId}`);
    await sleep(DELAY_MS);

    const data = {};
    for (const [ep, label] of endpoints) {
      data[ep] = await fetchEndpoint(label, `${BASE_URL}/${ep}/${uuid}/${pId}`);
    }

    const failedEps = Object.entries(data)
      .filter(([, v]) => v == null)
      .map(([k]) => k);
    if (failedEps.length > 0) {
      console.log(`  Warning: ${failedEps.length} API request(s) failed (${failedEps.join(", ")}).`);
      console.log(`            Output may be missing sections; re-run if the report looks incomplete.`);
    }

    console.log(`  Building markdown...`);
    let md = "";
    md += buildHeader(pStats, uuid);
    md += buildOverview(pStats);
    md += buildSkills(pStats);
    md += buildNetworth(data.networth);
    md += buildInventories(data.inventory);
    md += buildGear(data.gear);
    md += buildAccessories(data.accessories);
    md += buildPets(data.pets);
    md += buildDungeons(data.dungeons);
    md += buildSlayers(data.slayer);
    md += buildMinions(data.minions);
    md += buildCollections(data.collections);
    md += buildBestiary(data.bestiary);
    md += buildCrimsonIsle(data.crimson_isle);
    md += buildRift(data.rift);
    md += buildMisc(data.misc);
    md += buildSkillDetails(data.skills);
    md += buildPlayerStats(data.playerStats);

    const now = new Date();
    md += `---\n\n`;
    md += `*Generated from [SkyCrypt](https://sky.shiiyu.moe/stats/${USERNAME}/${pName}) on ${now.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })} at ${now.toLocaleTimeString("en-US")}*\n`;

    const filename = `skycrypt_${USERNAME}_${pName}${dateStamp()}.md`;
    const outPath = path.join(__dirname, filename);
    fs.writeFileSync(outPath, md, "utf-8");
    console.log(`  Saved: ${outPath}`);
  }

  console.log("\n  Done!\n");
}

main().catch((err) => {
  console.error(`\nError: ${err.message}`);
  process.exit(1);
});
