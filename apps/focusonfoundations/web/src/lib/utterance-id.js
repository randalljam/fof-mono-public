// Stable id for a spoken line: readable slug + short djb2 hash (collision guard).
// Shared by every applet's spoken-line inventory and by scripts/generate-tts.js.
export function utteranceId(text) {
  const slug = text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48).replace(/-+$/g, "");
  let h = 5381;
  for (let i = 0; i < text.length; i++) h = ((h * 33) ^ text.charCodeAt(i)) >>> 0;
  return `${slug}-${h.toString(16)}`;
}
