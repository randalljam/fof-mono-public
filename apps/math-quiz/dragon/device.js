// Shared device classification for Dragon Baby (controls, how-to, handoff).
export function isTouchDevice() {
  if (typeof window === 'undefined') return false;
  return (navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window;
}
export function deviceType() {
  return isTouchDevice() ? 'touch' : 'desktop';
}
export function transferTargetType() {
  return isTouchDevice() ? 'desktop' : 'touch';
}
export function transferButtonLabel() {
  return isTouchDevice() ? 'Transfer to desktop' : 'Transfer to mobile';
}
