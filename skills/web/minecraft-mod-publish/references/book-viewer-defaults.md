file: skills/web/minecraft-mod-publish/references/book-viewer-defaults.md
title: Minecraft book viewer defaults
source-github-url: original
source-guide-url: original
history:
  - 2026-07-19 · Randy True · Cursor [Minecraft bestiary web viewer](03bb58d9-b1ae-4dbf-ae3e-a80fca72b5d1) — captured responsive book behavior and layout lessons from the Ice and Fire bestiary

**Default behavior for publishing Minecraft mod books, bestiaries, manuals, and guide GUIs as responsive static websites.**


## View model
Treat each rendered source image as a two-leaf spread:

```text
spread 0 = leaf 0 (left), leaf 1 (right)
spread 1 = leaf 2 (left), leaf 3 (right)
spread n = floor(leaf / 2)
side = leaf % 2 == 0 ? left : right
```

Desktop and iPad navigate by spread. iPhone portrait navigates by leaf.


## Required responsive behavior
- Desktop and iPad show the full left/right spread at its original aspect ratio.
- iPhone portrait shows one leaf at approximately full display width.
- Phone navigation order is left leaf → right leaf → next spread’s left leaf.
- Phone index uses half the desktop index capacity. A 2×5 desktop index becomes a 1×5 phone index.
- Index and chapter navigation both use the same single-leaf shell on phone.
- Do not optimize phone landscape unless the user requests it; preserve usable controls.


## Phone and iPad detection
Use an explicit iPhone/iPod user-agent check first, then a touch/viewport fallback. Exclude iPad before applying the fallback.

Practical baseline:

```javascript
function isPhoneViewport() {
  const ua = navigator.userAgent || "";
  if (/iPad/.test(ua)) return false;
  if (/iPhone|iPod/.test(ua)) return true;
  if (/Android/i.test(ua) && /Mobile/i.test(ua)) return true;

  const shortEdge = Math.min(innerWidth, innerHeight);
  const longEdge = Math.max(innerWidth, innerHeight);
  const coarse = matchMedia("(pointer: coarse)").matches;

  if (navigator.platform === "MacIntel"
      && navigator.maxTouchPoints > 1
      && shortEdge >= 700) return false;

  return coarse && shortEdge <= 500 && longEdge <= 1000;
}
```

Do not classify every `MacIntel` touch device as iPad; an iPhone requesting a desktop site can expose unusual platform information. Require a tablet-sized short edge for that fallback.


## Cropping a pre-rendered spread
Do not resize a full spread into a single-leaf box; that squashes both pages and keeps text unreadable.

Use an overflow-hidden leaf container with the spread image at 200% width:

```css
.single-page {
  aspect-ratio: 195 / 245;
  overflow: hidden;
}

.page-half {
  position: absolute;
  inset-block-start: 0;
  width: 200%;
  height: 100%;
  max-width: none;
}

.page-half.side-left { left: 0; }
.page-half.side-right { left: -100%; }
```

Adapt `195 / 245` to half the source spread width and full source height.


## Index leaves
The phone index must not retain a two-column grid. Render only the chapters belonging to the active leaf:

```javascript
const desktopIndexSize = 10;
const phoneIndexSize = 5;
const start = indexLeaf * phoneIndexSize;
const chapters = manifest.chapters.slice(start, start + phoneIndexSize);
```

Use a one-column grid and crop or reposition the authentic book background to the active side. Verify the first and second leaves separately.


## Layout sizing
Size the book against a dedicated flex slot above the HUD, not directly against `100dvh`. Safari chrome and standalone mode can report viewport units differently.

Use:

```css
#app {
  min-height: 100svh;
  display: flex;
  flex-direction: column;
}

#book-viewport {
  flex: 1 1 auto;
  min-height: 0;
  container-type: size;
}

#book-shell {
  width: min(100cqw, calc(100cqh * 390 / 245));
  aspect-ratio: 390 / 245;
}
```

For phone leaf mode, replace `390 / 245` with the single-leaf ratio. Keep the HUD as `flex: 0 0 auto`.


## Bottom controls
- Put title/status on its own row.
- Use a three-column grid for Index, Previous, and Next on phone.
- Use `repeat(3, minmax(0, 1fr))` so button intrinsic widths cannot overflow.
- Keep the controls immediately below the book with a small explicit gap.
- Apply a solid/dark HUD background and a higher stacking order than the book.
- Disable unavailable navigation without removing the button; this prevents layout shifts.


## Safari and Add to Home Screen
Include:

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
<meta name="apple-mobile-web-app-title" content="Guide">
<meta name="theme-color" content="#0d0906">
```

Paint `html`, `body`, and the app root with a solid dark fallback beneath any gradient. Handle the bottom safe area on the HUD, not the body:

```css
html { background-color: #0d0906; }
body { padding-bottom: 0; }
#hud { padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px)); }
```

Use `-webkit-fill-available` as a standalone fallback. Add the Home Screen icon from the production URL; adding localhost or a LAN URL creates a shortcut to that local address.


## Rendering lessons
- Reproduce Minecraft’s virtual texture dimensions and UV coordinates; do not raw-crop based only on source PNG size.
- Keep the authentic spine, cover edge, and bottom leather/page rim visible.
- Use `font.getlength()` or equivalent pixel measurement to fit text. Character counts alone can truncate proportional or substituted fonts.
- Prefer readable monospace fallback text over an authentic font that is illegible on the target display.
- Place icons and drawings in measured blank regions. Shrink slightly before moving far from the game coordinates.
- Keep recipes above the page rim and prevent multiple recipe overlays from stacking.
- Pre-render at a scale such as 3×, but perform layout in logical book pixels.
- Add a cache-bust version to CSS and JS references whenever device behavior changes.


## Minimum acceptance checks
- iPhone 15 Plus portrait (`430 × 932`): one index leaf, one chapter leaf, left/right sequence, three equal buttons.
- Regular iPad portrait (`820 × 1180`): full spread and readable HUD title.
- iPad reduced content height (approximately `820 × 1000`): book does not cover title or controls.
- Desktop (`1280 × 800`): full spread unchanged.
- Standalone iPad: no white bottom strip; controls sit above the home indicator.
- Every target: no horizontal overflow and no content outside the book.
