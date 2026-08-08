export function createBurst(itemsInput) {
  const items = itemsInput.slice();
  let index = 0;
  const entries = [];
  function correctAnswer(item) {
    if (item.operation === '+') return item.num1 + item.num2;
    return null;
  }
  function current() {
    if (index >= items.length) return null;
    return items[index];
  }
  function record(userValue, isCorrect, rt, shownAtWall, startTime, flags = []) {
    const item = items[index];
    if (!item) return null;
    const entry = {
      id: `${startTime}-${entries.length}`,
      fact_key: item.key,
      problem_text: item.problemText || `${item.num1} ${item.operation} ${item.num2}`,
      correct_answer: correctAnswer(item),
      user_answer_string: userValue === null || userValue === undefined ? '' : String(userValue),
      user_answer: userValue,
      is_correct: isCorrect,
      response_time_ms: Math.round(rt),
      presented_at: shownAtWall,
      flags: flags.slice(),
    };
    entries.push(entry);
    index += 1;
    return entry;
  }
  function lastEntry() {
    return entries.length ? entries[entries.length - 1] : null;
  }
  function setFlags(entry, flags) {
    if (!entry) return;
    const idx = entries.indexOf(entry);
    if (idx < 0) return;
    entry.flags = flags.slice();
  }
  function insertItem(item, gap = 5) {
    if (!item) return;
    const pos = Math.min(index + gap, items.length);
    items.splice(pos, 0, { ...item });
  }
  function insert(gap = 5) {
    insertItem(items[index], gap);
  }
  function skipCurrent(gap = 5) {
    const item = items[index];
    if (!item) return;
    index += 1;
    const pos = Math.min(index + gap, items.length);
    items.splice(pos, 0, { ...item });
  }
  function done() { return index >= items.length; }
  function progress() { return { index, total: items.length, entries: entries.slice() }; }
  function allItems() { return items.map((item) => ({ ...item })); }
  return { current, record, lastEntry, setFlags, insert, insertItem, skipCurrent, done, progress, allItems };
}
