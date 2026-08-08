// Ten-frame teach visuals - pure SVG string renderer.
//
// Produces the two-state side-by-side ten-frame visual used by visual practice.
// The renderer is DOM-free: callers receive SVG strings and can render them
// however they want. Dots carry data-frame/data-dot attributes so tests and
// future instrumentation can inspect the representation without parsing layout.
//
// History (newest first):
//   2026-07-26 - frames side-by-side again; setup gains an answer variant so
//                both the "8 + 3" and "10 + 1" lines can show "= 11".
//   2026-07-26 - replaced captioned steps with two stacked teach states.
//   2026-07-25 - initial double ten-frame renderer and caption script helper.

const COLOR_A = '#00acc1';
const COLOR_B = '#daa520';
const TEXT_DARK = '#374151';
const CELL = 30;
const GAP = 6;
const DOT_R = 10;
const FRAME_W = 5 * CELL + 4 * GAP;
const LEFT_X = 16;
const RIGHT_X = LEFT_X + FRAME_W + 40;          // 40px gutter holds the between-frames plus
const VIEW_W = RIGHT_X + FRAME_W + 76;          // right margin leaves room for "= NN"
const VIEW_H = 132;
const FRAME_Y = 10;
const MID_X = LEFT_X + FRAME_W + 20;            // center of the gutter
const EQ_Y = 118;                                // numerals row baseline
const FONT = `font-family="Arial, sans-serif" font-size="34" font-weight="700"`;

function normalizeAddend(n, name) {
  if (!Number.isInteger(n) || n < 0 || n > 10) {
    throw new RangeError(`${name} must be an integer from 0 to 10`);
  }
  return n;
}

function orderedAddends(num1, num2) {
  const a = normalizeAddend(num1, 'num1');
  const b = normalizeAddend(num2, 'num2');
  const sum = a + b;
  if (sum > 20) throw new RangeError('sum must be <= 20');
  if (a >= b) return { larger: a, smaller: b, sum };
  return { larger: b, smaller: a, sum };
}

function cellCenter(x0, index) {
  const col = index % 5;
  const row = Math.floor(index / 5);
  return {
    cx: x0 + col * (CELL + GAP) + CELL / 2,
    cy: FRAME_Y + row * (CELL + GAP) + CELL / 2,
  };
}

function frameSvg(frame, x0) {
  const rects = [];
  for (let i = 0; i < 10; i++) {
    const col = i % 5;
    const row = Math.floor(i / 5);
    const x = x0 + col * (CELL + GAP);
    const y = FRAME_Y + row * (CELL + GAP);
    rects.push(`<rect data-frame="${frame}" data-cell="${i}" x="${x}" y="${y}" width="${CELL}" height="${CELL}" rx="5" fill="#ffffff" stroke="#9ca3af" stroke-width="1.5"/>`);
  }
  return `<g data-frame-group="${frame}">${rects.join('')}</g>`;
}

function dotSvg(frame, x0, index, dotName, fill) {
  const { cx, cy } = cellCenter(x0, index);
  return `<circle data-frame="${frame}" data-dot="${dotName}" data-cell="${index}" cx="${cx}" cy="${cy}" r="${DOT_R}" fill="${fill}"/>`;
}

function dotSeries(frame, x0, start, count, dotName, fill) {
  const dots = [];
  for (let i = 0; i < count; i++) dots.push(dotSvg(frame, x0, start + i, dotName, fill));
  return dots.join('');
}

function text(x, fill, body, extra = '') {
  return `<text x="${x}" y="${EQ_Y}" text-anchor="middle" ${FONT} fill="${fill}"${extra}>${body}</text>`;
}

// Mid-height plus between the two frames, plus the numerals row beneath them:
// each addend centered under its own frame, "+" in the gutter, and (optionally)
// "= sum" to the right of the second frame.
function equationRow(leftVal, leftFill, rightVal, rightFill, sum) {
  const midFrameY = FRAME_Y + CELL + GAP / 2 + 12;   // between-frames plus, mid-frame height
  let out = `<text x="${MID_X}" y="${midFrameY}" text-anchor="middle" ${FONT} fill="${TEXT_DARK}">+</text>`
    + text(LEFT_X + FRAME_W / 2, leftFill, leftVal)
    + text(MID_X, TEXT_DARK, '+')
    + text(RIGHT_X + FRAME_W / 2, rightFill, rightVal);
  if (sum != null) out += text(RIGHT_X + FRAME_W + 42, TEXT_DARK, `= ${sum}`, ` data-sum="${sum}"`);
  return out;
}

function setupSvg({ larger, smaller, sum }, withAnswer) {
  const label = `${larger} + ${smaller}${withAnswer ? ` equals ${sum}` : ' setup'}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" data-state="${withAnswer ? 'setup-answer' : 'setup'}" viewBox="0 0 ${VIEW_W} ${VIEW_H}" role="img" aria-label="${label}">`
    + frameSvg('first', LEFT_X)
    + dotSeries('first', LEFT_X, 0, larger, 'A', COLOR_A)
    + frameSvg('second', RIGHT_X)
    + dotSeries('second', RIGHT_X, 0, smaller, 'B', COLOR_B)
    + equationRow(larger, COLOR_A, smaller, COLOR_B, withAnswer ? sum : null)
    + `</svg>`;
}

function resultSvg({ larger, smaller, sum }) {
  if (sum > 10) {
    const moved = Math.min(smaller, Math.max(0, 10 - larger));
    const remaining = smaller - moved;
    return `<svg xmlns="http://www.w3.org/2000/svg" data-state="result" viewBox="0 0 ${VIEW_W} ${VIEW_H}" role="img" aria-label="10 plus ${remaining} equals ${sum}">`
      + frameSvg('first', LEFT_X)
      + dotSeries('first', LEFT_X, 0, larger, 'A', COLOR_A)
      + dotSeries('first', LEFT_X, larger, moved, 'B', COLOR_B)
      + frameSvg('second', RIGHT_X)
      + dotSeries('second', RIGHT_X, 0, remaining, 'B', COLOR_B)
      + equationRow(larger + moved, TEXT_DARK, remaining, COLOR_B, sum)
      + `</svg>`;
  }

  // Sum <= 10: both addends combine into the single (first) frame; the second
  // frame stays empty so the layout matches the setup above it.
  return `<svg xmlns="http://www.w3.org/2000/svg" data-state="result" viewBox="0 0 ${VIEW_W} ${VIEW_H}" role="img" aria-label="${larger} plus ${smaller} equals ${sum}">`
    + frameSvg('first', LEFT_X)
    + dotSeries('first', LEFT_X, 0, larger, 'A', COLOR_A)
    + dotSeries('first', LEFT_X, larger, smaller, 'B', COLOR_B)
    + frameSvg('second', RIGHT_X)
    + text(LEFT_X + FRAME_W / 2, TEXT_DARK, `= ${sum}`, ` data-sum="${sum}"`)
    + `</svg>`;
}

// Return the SVG teach states for an addition fact: setup (frames + "8 + 3"),
// setupAnswer (same + "= 11") and result (the make-ten arrangement + "10 + 1
// = 11"). The larger addend is rendered first/left so the visual supports
// count-on-from-larger; ties keep num1 first.
export function tenFrameTeachStates(num1, num2) {
  const state = orderedAddends(num1, num2);
  return {
    ...state,
    setupSvg: setupSvg(state, false),
    setupAnswerSvg: setupSvg(state, true),
    resultSvg: resultSvg(state),
  };
}
