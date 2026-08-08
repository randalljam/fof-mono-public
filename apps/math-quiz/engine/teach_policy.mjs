// Teach visual trigger policy - one place for ten-frame offer/show rules.
//
// Central policy for when/where the ten-frame teach visual is offered or shown.
// Every trigger rule lives here; the anchor controller asks, then acts.
//
// History (newest first):
//   2026-07-26 - initial app-wide teach visual policy.

export const TEACH_TRIGGERS = {
  lightbulbAlways: true,
  autoShowOnWrong: true,
  lightbulbInFlagPanel: true,
};

export function teachableProblem(item) {
  if (!item || item.operation !== '+') return false;
  const { num1, num2 } = item;
  return Number.isInteger(num1) && Number.isInteger(num2)
    && num1 >= 0 && num1 <= 10
    && num2 >= 0 && num2 <= 10
    && num1 + num2 <= 20;
}

export function showLightbulbOnRender(item) {
  return !!TEACH_TRIGGERS.lightbulbAlways && teachableProblem(item);
}

export function autoTeachOnWrong(item) {
  return !!TEACH_TRIGGERS.autoShowOnWrong && teachableProblem(item);
}

export function showLightbulbInFlagPanel(item) {
  return !!TEACH_TRIGGERS.lightbulbInFlagPanel && teachableProblem(item);
}
