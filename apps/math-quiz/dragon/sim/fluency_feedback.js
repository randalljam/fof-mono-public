// Post-quiz fluency readout for the kid HUD. Toggle off to silence the lines
// without removing the wiring — progress-bar sync still runs either way.
export const SHOW_FLUENCY_FEEDBACK = true;
export function fluencyFeedbackMessage(pctBefore, pctAfter) {
  const before = Math.round(Number(pctBefore) || 0);
  const after = Math.round(Number(pctAfter) || 0);
  if (after > before) {
    return `Great — you improved from ${before}% to ${after}%! Great job!`;
  }
  if (after < before) {
    return `Something happened — your fluency went down from ${before}% to ${after}%.`;
  }
  return `Holding steady at ${after}%.`;
}
export function fluencyFeedbackForResult(result, enabled = SHOW_FLUENCY_FEEDBACK) {
  if (!enabled || !result || !result.saved) return null;
  return fluencyFeedbackMessage(result.initialPct, result.newPct);
}
