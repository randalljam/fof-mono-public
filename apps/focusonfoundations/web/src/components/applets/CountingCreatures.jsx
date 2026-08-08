import React, { useState, useEffect, useRef } from "react";
import {
  englishWords, digitWords, MAX_COUNT, SLOTH_MAX, COMPUTER_MAX,
  STEP_INTROS, REVEAL_LINES, PRACTICE_LINES, SCREENS, slothAnswer, computerAnswer,
  nextPracticeTarget,
} from "../../lib/counting-creatures.js";
import { speak, primeSpeech, isMuted, setMuted } from "../../lib/applet-speech.js";

const DISPLAY = 'ui-rounded, "SF Pro Rounded", "Baloo 2", Nunito, system-ui, sans-serif';
const BODY = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';

const THEMES = {
  human: { key: "human", icon: "🧑", bg: "#FDF6E9", panel: "#FFFFFF", ink: "#3A342E", soft: "#8B8178", accent: "#E9922E", accent2: "#5A9E6F", pebble: "#9A8E80", pebbleEdge: "#6F6456", edge: "#B07A28" },
  sloth: { key: "sloth", icon: "🦥", bg: "#E9F1D9", panel: "#FBFDF3", ink: "#33412A", soft: "#6E7C58", accent: "#5E9A2F", accent2: "#8A6D4B", pebble: "#8AA06A", pebbleEdge: "#5E7346", edge: "#4C7A22" },
  computer: { key: "computer", icon: "💻", bg: "#0E1524", panel: "#17223B", ink: "#E7EEF9", soft: "#8DA0BE", accent: "#37E0C8", accent2: "#4D9BFF", pebble: "#5AD1BE", pebbleEdge: "#2A9C8B", edge: "#1E9B89" },
};
// creature colors readable on light backgrounds / dark backgrounds
const HUMAN_C = (dark) => (dark ? "#F2A94E" : "#CF7A1C");
const SLOTH_C = (dark) => (dark ? "#9BCB4E" : "#4E7D1F");
const COMP_C = "#37E0C8";

// ---------- parts ----------
const Pebble = ({ c, e, s = 22 }) => (
  <svg width={s} height={s * 0.82} viewBox="0 0 34 28" style={{ display: "block" }}>
    <ellipse cx="17" cy="15" rx="15" ry="11" fill={c} stroke={e} strokeWidth="2" />
    <ellipse cx="12" cy="10" rx="5" ry="3" fill="rgba(255,255,255,.5)" />
  </svg>
);
function Pile({ n, theme, size = 20, justify = "flex-start" }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 5, justifyContent: justify }}>
      {Array.from({ length: n }).map((_, i) => <Pebble key={i} c={theme.pebble} e={theme.pebbleEdge} s={size} />)}
    </div>
  );
}
function GroupedPile({ n, base, theme, size = 9 }) {
  const groups = []; let rem = n; while (rem > 0) { groups.push(Math.min(base, rem)); rem -= base; }
  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
      {groups.map((g, gi) => (
        <div key={gi} style={{ display: "flex", gap: 2 }}>
          {Array.from({ length: g }).map((_, i) => <Pebble key={i} c={theme.pebble} e={theme.pebbleEdge} s={size} />)}
        </div>
      ))}
    </div>
  );
}
function SlothHand({ size = 70, flip }) {
  return (
    <svg width={size} height={size * 1.16} viewBox="0 0 76 88" style={{ display: "block", transform: flip ? "scaleX(-1)" : "none" }}>
      <path d="M26 4 C22 20 22 30 30 40 L46 40 C54 30 54 20 50 4 Z" fill="#9B7B54" />
      <ellipse cx="38" cy="42" rx="20" ry="13" fill="#9B7B54" />
      <ellipse cx="38" cy="40" rx="20" ry="10" fill="#87683F" opacity=".45" />
      <path d="M22 48 C16 60 16 72 24 82 C29 72 28 58 30 50 Z" fill="#F0E6CE" stroke="#5C4630" strokeWidth="1.6" />
      <path d="M34 50 C31 63 32 76 40 86 C47 76 45 62 44 50 Z" fill="#F0E6CE" stroke="#5C4630" strokeWidth="1.6" />
      <path d="M52 48 C58 60 58 72 50 82 C45 72 46 58 46 50 Z" fill="#F0E6CE" stroke="#5C4630" strokeWidth="1.6" />
    </svg>
  );
}
const TransistorReal = () => (
  <svg width="108" height="118" viewBox="0 0 120 130">
    <rect x="46" y="86" width="5" height="36" rx="2" fill="#B9C2CC" /><rect x="58" y="86" width="5" height="40" rx="2" fill="#B9C2CC" /><rect x="70" y="86" width="5" height="36" rx="2" fill="#B9C2CC" />
    <path d="M32 60 A28 46 0 0 1 88 60 L88 88 Q60 96 32 88 Z" fill="#20242B" /><rect x="30" y="60" width="60" height="6" fill="#12151a" opacity="0.6" /><ellipse cx="52" cy="44" rx="9" ry="5" fill="#3a4049" opacity="0.7" />
  </svg>
);
const TransistorMicro = () => (
  <svg width="134" height="118" viewBox="0 0 150 130">
    <rect x="0" y="0" width="150" height="130" rx="8" fill="#2b2f36" /><rect x="10" y="10" width="130" height="110" rx="4" fill="#3b4048" />
    <rect x="24" y="30" width="34" height="70" rx="4" fill="#8b93a0" /><rect x="92" y="30" width="34" height="70" rx="4" fill="#8b93a0" /><rect x="58" y="46" width="34" height="38" fill="#5a6270" />
    <rect x="66" y="18" width="18" height="94" rx="3" fill="#d7dbe1" /><rect x="16" y="108" width="40" height="4" rx="2" fill="#fff" /><text x="60" y="112" fontSize="10" fill="#fff" fontFamily={BODY}>≈ 100 nm</text>
  </svg>
);

const NumeralText = ({ value, base, theme, size = 30, color }) => (
  <span style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: size, color: color || (theme && theme.accent), letterSpacing: 2 }}>{value.toString(base)}</span>
);

function Digit({ value, base, size, theme, reduced }) {
  const cellH = size * 1.34;
  return (
    <div style={{ height: cellH, width: size * 0.92, overflow: "hidden", borderRadius: size * 0.18, background: theme.bg, boxShadow: "inset 0 3px 8px rgba(0,0,0,.16)", border: `2px solid ${theme.soft}33` }}>
      <div style={{ transform: `translateY(${-value * cellH}px)`, transition: reduced ? "none" : "transform .42s cubic-bezier(.2,.85,.25,1)" }}>
        {Array.from({ length: base }, (_, i) => i).map((d) => (
          <div key={d} style={{ height: cellH, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: DISPLAY, fontWeight: 800, fontSize: size, color: theme.accent, lineHeight: 1 }}>{d}</div>
        ))}
      </div>
    </div>
  );
}
function Numeral({ value, base, theme, reduced, size = 52 }) {
  const digits = value.toString(base).split("").map(Number);
  const L = digits.length;
  return (
    <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
      {digits.map((d, i) => (
        <div key={`p${L - 1 - i}`} style={{ animation: reduced ? "none" : "placeIn .42s ease" }}>
          <Digit value={d} base={base} size={size} theme={theme} reduced={reduced} />
        </div>
      ))}
    </div>
  );
}
function PlaceValue({ value, base, theme }) {
  const digits = value.toString(base).split("").map(Number);
  const L = digits.length;
  return (
    <div>
      <div style={{ display: "flex", gap: 16, justifyContent: "center", alignItems: "flex-start" }}>
        {digits.map((d, i) => {
          const count = d * Math.pow(base, L - 1 - i);
          return (
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
              <NumeralText value={d} base={base} theme={theme} size={36} />
              <div style={{ display: "flex", flexWrap: "wrap", gap: 3, maxWidth: 70, justifyContent: "center", minHeight: 18 }}>
                {Array.from({ length: count }).map((_, k) => <Pebble key={k} c={theme.pebble} e={theme.pebbleEdge} s={14} />)}
                {count === 0 && <span style={{ color: theme.soft, fontSize: 16 }}>·</span>}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ textAlign: "center", margin: "10px 0 8px", fontFamily: DISPLAY, fontWeight: 800, fontSize: 26, color: theme.soft }}>=</div>
      <div style={{ display: "flex", justifyContent: "center" }}><Pile n={value} theme={theme} size={18} justify="center" /></div>
    </div>
  );
}

// ---------- buttons ----------
function RoundBtn({ label, onClick, disabled, theme, primary, size = 66 }) {
  return (
    <button onClick={onClick} disabled={disabled} aria-label={label === "+" ? "add one" : "remove one"} style={{
      width: size, height: size, borderRadius: size / 2, fontSize: size * 0.56, fontFamily: DISPLAY, fontWeight: 800,
      border: primary ? "none" : `3px solid ${theme.soft}66`, background: primary ? theme.accent : "transparent",
      color: primary ? (theme.key === "computer" ? "#08121f" : "#fff") : theme.ink,
      boxShadow: primary && !disabled ? `0 5px 0 ${theme.edge}` : "none", opacity: disabled ? 0.32 : 1,
      cursor: disabled ? "default" : "pointer", touchAction: "manipulation", display: "flex", alignItems: "center", justifyContent: "center", lineHeight: 1, paddingBottom: 4,
    }}>{label}</button>
  );
}
function QMark({ onClick, theme }) {
  return (
    <button onClick={onClick} aria-label="show the answer" style={{
      width: 112, height: 112, borderRadius: 56, fontSize: 62, fontFamily: DISPLAY, fontWeight: 800, border: "none",
      background: theme.accent, color: theme.key === "computer" ? "#08121f" : "#fff", boxShadow: `0 6px 0 ${theme.edge}`,
      cursor: "pointer", touchAction: "manipulation", animation: "pulse 1.4s ease-in-out infinite",
    }}>?</button>
  );
}
function NavBtn({ children, onClick, disabled, theme, primary }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      fontFamily: DISPLAY, fontWeight: 800, fontSize: 18, padding: "12px 20px", borderRadius: 16, cursor: disabled ? "default" : "pointer", touchAction: "manipulation",
      background: primary ? theme.accent : "transparent", color: primary ? (theme.key === "computer" ? "#08121f" : "#fff") : theme.ink,
      border: primary ? "none" : `2.5px solid ${theme.soft}55`, opacity: disabled ? 0.35 : 1, boxShadow: primary && !disabled ? `0 4px 0 ${theme.edge}` : "none",
    }}>{children}</button>
  );
}

// ---------- reveal chart ----------
function RevealChart({ base, max, revealed, theme, sloth, onPlus }) {
  return (
    <div>
      <div>
        {Array.from({ length: revealed + 1 }, (_, n) => n).map((n) => (
          <div key={n} style={{ display: "flex", alignItems: "center", gap: 12, padding: "2px 4px", borderBottom: `1px solid ${theme.soft}18` }}>
            <span style={{ minWidth: 42, textAlign: "center" }}><NumeralText value={n} base={base} theme={theme} size={16} /></span>
            <GroupedPile n={n} base={base} theme={theme} size={9} />
          </div>
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "center", marginTop: 12 }}>
        <RoundBtn label="+" primary theme={theme} disabled={revealed >= max} onClick={onPlus} size={62} />
      </div>
    </div>
  );
}

// ---------- sloth vs human comparison (numerals only, all shown) ----------
function ComparisonChart({ theme }) {
  const sC = SLOTH_C(false), hC = HUMAN_C(false);
  return (
    <div>
      <div style={{ display: "flex", marginBottom: 6 }}>
        <div style={{ flex: 1, textAlign: "center", fontFamily: BODY, fontSize: 12, fontWeight: 700, color: theme.soft }}><div style={{ fontSize: 22 }}>🦥</div>base 6</div>
        <div style={{ flex: 1, textAlign: "center", fontFamily: BODY, fontSize: 12, fontWeight: 700, color: theme.soft }}><div style={{ fontSize: 22 }}>🧑</div>base 10</div>
      </div>
      {Array.from({ length: 12 }, (_, n) => n).map((n) => (
        <button key={n} onClick={() => speak(englishWords(n))} aria-label={`hear ${englishWords(n)}`} style={{ display: "flex", width: "100%", background: "transparent", border: "none", borderBottom: `1px solid ${theme.soft}20`, padding: "2px 0", cursor: "pointer", touchAction: "manipulation" }}>
          <span style={{ flex: 1, textAlign: "center" }}><NumeralText value={n} base={6} theme={theme} size={22} color={sC} /></span>
          <span style={{ flex: 1, textAlign: "center" }}><NumeralText value={n} base={10} theme={theme} size={22} color={hC} /></span>
        </button>
      ))}
    </div>
  );
}

// ---------- final three-way chart (static) ----------
function FinalChart({ theme, max }) {
  const W = { h: 44, s: 44, c: 58 };
  const hC = HUMAN_C(true), sC = SLOTH_C(true);
  const Head = ({ w, ic, lbl }) => (
    <div style={{ width: w, textAlign: "center", fontFamily: BODY, fontSize: 10, fontWeight: 700, color: theme.soft, lineHeight: 1.2 }}><div style={{ fontSize: 18 }}>{ic}</div>{lbl}</div>
  );
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: 5, borderBottom: `2px solid ${theme.soft}44`, marginBottom: 3 }}>
        <Head w={W.h} ic="🧑" lbl="base 10" /><Head w={W.s} ic="🦥" lbl="base 6" /><Head w={W.c} ic="💻" lbl="base 2" />
        <div style={{ flex: 1, textAlign: "center", fontFamily: BODY, fontSize: 10, fontWeight: 700, color: theme.soft }}>pebbles</div>
      </div>
      {Array.from({ length: max + 1 }, (_, n) => n).map((n) => (
        <div key={n} style={{ display: "flex", alignItems: "center", padding: "2px 0", borderBottom: `1px solid ${theme.soft}18` }}>
          <div style={{ width: W.h, textAlign: "center" }}><NumeralText value={n} base={10} theme={theme} size={15} color={hC} /></div>
          <div style={{ width: W.s, textAlign: "center" }}><NumeralText value={n} base={6} theme={theme} size={15} color={sC} /></div>
          <div style={{ width: W.c, textAlign: "center" }}><NumeralText value={n} base={2} theme={theme} size={15} color={COMP_C} /></div>
          <div style={{ flex: 1, paddingLeft: 8 }}><Pile n={n} theme={theme} size={6} /></div>
        </div>
      ))}
    </div>
  );
}

// ---------- binary switches ----------
function Switches({ value, setValue, theme, onChange }) {
  return (
    <div style={{ display: "flex", gap: 14, justifyContent: "center" }}>
      {[4, 2, 1].map((pv) => {
        const on = (value & pv) !== 0;
        return (
          <button key={pv} onClick={() => { const nv = on ? value - pv : value + pv; setValue(nv); onChange && onChange(nv); }} aria-label={`switch worth ${pv}`} aria-pressed={on} style={{ background: "transparent", border: "none", cursor: "pointer", touchAction: "manipulation" }}>
            <div style={{ width: 54, height: 88, borderRadius: 16, padding: 6, background: theme.bg, border: `2px solid ${theme.soft}55`, boxShadow: "inset 0 2px 6px rgba(0,0,0,.3)", display: "flex", flexDirection: "column-reverse" }}>
              <div style={{ height: 36, borderRadius: 11, background: on ? theme.accent : theme.soft + "55", transform: on ? "translateY(0)" : "translateY(-36px)", transition: "transform .28s cubic-bezier(.2,.85,.25,1), background .2s", display: "flex", alignItems: "center", justifyContent: "center", color: on ? "#08121f" : theme.soft, fontFamily: DISPLAY, fontWeight: 800, fontSize: 22, boxShadow: on ? `0 0 16px ${theme.accent}` : "none" }}>{on ? "1" : "0"}</div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ---------- two-way conversion practice ----------
function Converter({ base, maxVal, theme, reduced, showHuman }) {
  const [mode, setMode] = useState("toPebbles");
  const roundIndex = useRef(0);
  const previousTarget = useRef(null);
  const pickTarget = () => {
    const nextTarget = nextPracticeTarget({ base, maxVal, roundIndex: roundIndex.current, previousTarget: previousTarget.current });
    roundIndex.current += 1;
    previousTarget.current = nextTarget;
    return nextTarget;
  };
  const [target, setTarget] = useState(() => pickTarget());
  const [answer, setAnswer] = useState(0);
  const [result, setResult] = useState(null);
  const humanColor = HUMAN_C(theme.key === "computer");
  const prompt = (m) => (m === "toPebbles" ? PRACTICE_LINES.makePebbles : PRACTICE_LINES.makeNumber);
  const newRound = (m) => { setTarget(pickTarget()); setAnswer(0); setResult(null); speak(prompt(m)); };
  const toggle = () => { const m = mode === "toPebbles" ? "toNumeral" : "toPebbles"; setMode(m); newRound(m); };
  const change = (nv) => { const v = Math.max(0, Math.min(maxVal, nv)); setAnswer(v); setResult(null); speak(mode === "toPebbles" ? englishWords(v) : digitWords(v, base)); };
  const submit = () => {
    if (answer === target) {
      setResult("ok");
      if (showHuman && target >= base) {
        speak(base === 6 ? slothAnswer(target) : computerAnswer(target));
      } else speak(PRACTICE_LINES.correct);
    } else { setResult("no"); speak(PRACTICE_LINES.tryAgain); }
  };
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ display: "flex", justifyContent: "center", marginBottom: 14 }}>
        <button onClick={toggle} aria-label="switch direction" style={{ display: "flex", alignItems: "center", gap: 8, background: theme.bg, border: `2px solid ${theme.soft}55`, borderRadius: 999, padding: "7px 14px", cursor: "pointer", fontFamily: DISPLAY, fontWeight: 800, fontSize: 18, color: theme.ink, touchAction: "manipulation" }}>
          {mode === "toPebbles" ? <><span>🔢</span><span>→</span><span>🪨</span></> : <><span>🪨</span><span>→</span><span>🔢</span></>}<span style={{ fontSize: 15, color: theme.soft, marginLeft: 4 }}>⇄</span>
        </button>
      </div>
      <div style={{ background: theme.bg, borderRadius: 18, padding: "14px 12px", margin: "0 0 14px" }}>
        {mode === "toPebbles"
          ? <Numeral value={target} base={base} theme={theme} reduced={reduced} size={48} />
          : <div style={{ display: "flex", justifyContent: "center" }}><Pile n={target} theme={theme} size={20} justify="center" /></div>}
      </div>
      <div style={{ minHeight: 74, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 10 }}>
        {mode === "toPebbles"
          ? <Pile n={answer} theme={theme} size={22} justify="center" />
          : <Numeral value={answer} base={base} theme={theme} reduced={reduced} size={48} />}
      </div>
      <div style={{ display: "flex", gap: 18, justifyContent: "center", marginBottom: 12 }}>
        <RoundBtn label="−" theme={theme} disabled={answer === 0} onClick={() => change(answer - 1)} />
        <RoundBtn label="+" theme={theme} primary disabled={answer === maxVal} onClick={() => change(answer + 1)} />
      </div>
      {result === "ok"
        ? <div>
            <div style={{ fontSize: 42 }}>✅</div>
            {showHuman && <div style={{ marginTop: 4, fontFamily: DISPLAY, fontWeight: 800, fontSize: 22, color: humanColor }}>🧑 = {target}</div>}
            <div style={{ marginTop: 10 }}><NavBtn theme={theme} primary onClick={() => newRound(mode)}>Another →</NavBtn></div>
          </div>
        : <div><NavBtn theme={theme} primary onClick={submit}>Check ✓</NavBtn>{result === "no" && <div style={{ fontSize: 34, marginTop: 8 }}>🔁</div>}</div>}
    </div>
  );
}

// ===================================================================
export default function App() {
  const [started, setStarted] = useState(false);
  const [step, setStep] = useState(0);
  const [reduced, setReduced] = useState(false);
  const [humanRev, setHumanRev] = useState(0);
  const [slothRev, setSlothRev] = useState(0);
  const [bin, setBin] = useState(0);
  const [showFingers, setShowFingers] = useState(false);
  const [showSloth, setShowSloth] = useState(false);
  const [showChip, setShowChip] = useState(false);
  const [oneFinger, setOneFinger] = useState(false);
  const [guessRevealed, setGuessRevealed] = useState(false);
  const [muted, setMutedState] = useState(false);

  useEffect(() => { try { setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches); } catch (e) {} }, []);
  useEffect(() => { primeSpeech(); setMutedState(isMuted()); }, []);

  const PHASES = ["human", "human", "sloth", "sloth", "sloth", "sloth", "computer", "computer", "computer", "computer", "computer", "computer", "computer"];
  const theme = THEMES[PHASES[step]];
  const last = PHASES.length - 1;
  const MAX = MAX_COUNT;

  const SPEAK = STEP_INTROS;
  const spokenStep = useRef(-1);
  useEffect(() => { if (!started) return; if (spokenStep.current === step) return; spokenStep.current = step; speak(SPEAK[step]); }, [step, started]);
  const go = (s) => setStep(Math.max(0, Math.min(last, s)));
  useEffect(() => {
    if (!started) return;
    const onKey = (e) => {
      if (e.key === "ArrowRight") go(step + 1);
      else if (e.key === "ArrowLeft") go(step - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [started, step]);
  const toggleMute = () => {
    const m = !muted;
    setMutedState(m); setMuted(m);
    if (!m) speak(SPEAK[step]);
  };

  const Title = ({ children }) => (
    <h1 style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 23, lineHeight: 1.15, color: theme.ink, margin: "0 0 6px", textAlign: "center" }}>{children}</h1>
  );
  const Big = ({ children, color }) => (
    <div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 38, color: color || theme.accent, marginTop: 6 }}>{children}</div>
  );

  function content() {
    switch (step) {
      case 0:
        return <RevealChart base={10} max={MAX} revealed={humanRev} theme={theme} onPlus={() => { const k = Math.min(MAX, humanRev + 1); setHumanRev(k); speak(englishWords(k)); }} />;
      case 1:
        return (
          <div style={{ textAlign: "center" }}>
            <Title>{SCREENS[1].title}</Title>
            <div style={{ margin: "24px 0" }}>
              {!showFingers
                ? <QMark theme={theme} onClick={() => { setShowFingers(true); speak(REVEAL_LINES.tenFingers); }} />
                : <div><div style={{ fontSize: 76, animation: reduced ? "none" : "wave 1.1s ease infinite" }}>✋🤚</div><Big>{SCREENS[1].displays?.tenFingers}</Big></div>}
            </div>
          </div>
        );
      case 2:
        return (
          <div style={{ textAlign: "center" }}>
            <Title>{SCREENS[2].title}</Title>
            <div style={{ margin: "18px 0" }}>
              {!showSloth
                ? <QMark theme={theme} onClick={() => { setShowSloth(true); speak(REVEAL_LINES.slothFingers); }} />
                : <div>
                    <div style={{ fontSize: 60 }}>🦥</div>
                    <div style={{ display: "flex", gap: 14, justifyContent: "center", alignItems: "flex-end", marginTop: 2 }}><SlothHand /><SlothHand flip /></div>
                    <div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 22, color: theme.accent, marginTop: 12, lineHeight: 1.3 }} dangerouslySetInnerHTML={{ __html: SCREENS[2].displays?.slothFingers }} />
                  </div>}
            </div>
          </div>
        );
      case 3:
        return <RevealChart base={6} max={MAX} revealed={slothRev} sloth theme={theme} onPlus={() => { const k = Math.min(MAX, slothRev + 1); setSlothRev(k); speak(digitWords(k, 6)); }} />;
      case 4:
        return (
          <div>
            <Title>{SCREENS[4].title}</Title>
            <ComparisonChart theme={theme} />
          </div>
        );
      case 5:
        return <Converter base={6} maxVal={SLOTH_MAX} theme={theme} reduced={reduced} showHuman />;
      case 6:
        return (
          <div style={{ textAlign: "center" }}>
            <Title>{SCREENS[6].title}</Title>
            <div style={{ margin: "24px 0" }}>
              {!guessRevealed
                ? <QMark theme={theme} onClick={() => { setGuessRevealed(true); speak(REVEAL_LINES.oneFinger); }} />
                : <div><div style={{ fontSize: 88, animation: reduced ? "none" : "pop .5s ease" }}>☝️</div><Big>{SCREENS[6].displays?.oneFinger}</Big></div>}
            </div>
          </div>
        );
      case 7:
        return (
          <div style={{ textAlign: "center" }}>
            <Title>{SCREENS[7].title}</Title>
            {!oneFinger
              ? <div style={{ margin: "24px 0" }}><QMark theme={theme} onClick={() => { setOneFinger(true); speak(REVEAL_LINES.zeroOne); }} /></div>
              : <div style={{ display: "flex", gap: 34, justifyContent: "center", margin: "18px 0" }}>
                  <div><div style={{ fontSize: 60 }}>✊</div><div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 34, color: theme.soft }}>0</div></div>
                  <div><div style={{ fontSize: 60 }}>☝️</div><div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 34, color: theme.accent }}>1</div></div>
                </div>}
          </div>
        );
      case 8:
        return (
          <div style={{ textAlign: "center" }}>
            <Title>{SCREENS[8].title}</Title>
            <div style={{ display: "flex", gap: 18, justifyContent: "center", margin: "10px 0", fontSize: 44 }}><span>🔌</span><span>💡</span></div>
            {!showChip
              ? <NavBtn theme={theme} onClick={() => { setShowChip(true); speak(REVEAL_LINES.transistors); }}>{SCREENS[8].button}</NavBtn>
              : <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap", marginTop: 8 }}>
                  <div style={{ background: theme.bg, borderRadius: 14, padding: 10 }}><TransistorReal /></div>
                  <div style={{ background: theme.bg, borderRadius: 14, padding: 10 }}><TransistorMicro /></div>
                </div>}
          </div>
        );
      case 9:
        return (
          <div style={{ textAlign: "center" }}>
            <div style={{ margin: "2px 0 16px" }}><Switches value={bin} setValue={setBin} theme={theme} onChange={(nv) => speak(digitWords(nv, 2))} /></div>
            <PlaceValue value={bin} base={2} theme={theme} />
          </div>
        );
      case 10:
        return <Converter base={2} maxVal={COMPUTER_MAX} theme={theme} reduced={reduced} showHuman />;
      case 11:
        return (
          <div style={{ textAlign: "center" }}>
            <div style={{ display: "grid", gap: 10, margin: "6px 0 16px" }}>
              {[["🧑", "10 fingers", "base 10"], ["🦥", "6 fingers", "base 6"], ["💻", "1 finger, 2 states", "base 2"]].map(([ic, f, b]) => (
                <div key={b} style={{ display: "flex", alignItems: "center", gap: 14, background: theme.bg, borderRadius: 16, padding: "12px 16px" }}>
                  <span style={{ fontSize: 32 }}>{ic}</span>
                  <span style={{ fontFamily: BODY, fontSize: 15, color: theme.ink, flex: 1, textAlign: "left" }}>{f}</span>
                  <span style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 20, color: theme.accent }}>{b}</span>
                </div>
              ))}
            </div>
            <div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 22, color: theme.ink }}>{SCREENS[11].banner}</div>
          </div>
        );
      case 12:
        return (
          <div>
            <Title>{SCREENS[12].title}</Title>
            <FinalChart theme={theme} max={MAX} />
            <div style={{ textAlign: "center", marginTop: 14 }}>
              <NavBtn theme={theme} onClick={() => { setStep(0); setHumanRev(0); setSlothRev(0); setBin(0); setShowFingers(false); setShowSloth(false); setShowChip(false); setOneFinger(false); setGuessRevealed(false); spokenStep.current = -1; setTimeout(() => speak(SPEAK[0]), 60); }}>Start over</NavBtn>
            </div>
          </div>
        );
      default:
        return null;
    }
  }

  if (!started) {
    return (
      <div style={{ minHeight: "100vh", background: THEMES.human.bg, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: BODY, padding: 20 }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 60 }}>🧑 🦥 💻</div>
          <div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 26, color: THEMES.human.ink, margin: "10px 0 22px" }}>Counting Creatures</div>
          <button onClick={() => { primeSpeech(); spokenStep.current = step; speak(SPEAK[step]); setStarted(true); }} aria-label="start" style={{ width: 128, height: 128, borderRadius: 64, border: "none", background: THEMES.human.accent, color: "#fff", fontSize: 56, cursor: "pointer", boxShadow: `0 6px 0 ${THEMES.human.edge}`, touchAction: "manipulation" }}>▶</button>
          <div style={{ fontFamily: BODY, fontSize: 15, color: THEMES.human.soft, marginTop: 16 }}>🔊 Turn the volume up</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: theme.bg, transition: "background .5s ease", fontFamily: BODY, padding: "16px 14px 34px" }}>
      <style>{`
        @keyframes placeIn { from { transform: scale(.4) translateY(-8px); opacity: 0 } to { transform: none; opacity: 1 } }
        @keyframes wave { 0%,100%{ transform: rotate(-9deg) } 50%{ transform: rotate(9deg) } }
        @keyframes pop { 0%{ transform: scale(.3); opacity:0 } 60%{ transform: scale(1.15) } 100%{ transform: scale(1); opacity:1 } }
        @keyframes pulse { 0%,100%{ transform: scale(1) } 50%{ transform: scale(1.07) } }
        button:focus-visible { outline: 3px solid ${theme.accent2}; outline-offset: 3px; }
        button:active:not(:disabled) { transform: translateY(2px); }
        @media (prefers-reduced-motion: reduce){ *{ animation-duration:.001ms !important; transition-duration:.001ms !important } }
      `}</style>
      <div style={{ maxWidth: 540, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <button onClick={() => speak(SPEAK[step])} aria-label="repeat the instructions" title="Repeat the instructions" style={{ width: 44, height: 44, borderRadius: 22, border: `2px solid ${theme.soft}55`, background: theme.panel, fontSize: 19, cursor: "pointer", touchAction: "manipulation", display: "flex", alignItems: "center", justifyContent: "center" }}>💬</button>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            {["human", "sloth", "computer"].map((k) => (
              <span key={k} style={{ fontSize: 24, opacity: theme.key === k ? 1 : 0.35, transform: theme.key === k ? "scale(1.1)" : "none", transition: "all .3s ease" }}>{THEMES[k].icon}</span>
            ))}
          </div>
          <button onClick={toggleMute} aria-label={muted ? "turn sound on" : "turn sound off"} aria-pressed={muted} title={muted ? "Sound off — tap to unmute" : "Sound on — tap to mute"} style={{ width: 44, height: 44, borderRadius: 22, border: `2px solid ${theme.soft}55`, background: theme.panel, fontSize: 19, cursor: "pointer", touchAction: "manipulation", display: "flex", alignItems: "center", justifyContent: "center", opacity: muted ? 0.6 : 1 }}>{muted ? "🔇" : "🔊"}</button>
        </div>
        <div style={{ background: theme.panel, borderRadius: 26, padding: "18px 18px", boxShadow: "0 12px 34px rgba(0,0,0,.14)", minHeight: 340, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          {content()}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14 }}>
          <NavBtn theme={theme} onClick={() => go(step - 1)} disabled={step === 0}>←</NavBtn>
          <div style={{ display: "flex", gap: 1 }}>
            {PHASES.map((_, i) => (
              <button key={i} onClick={() => go(i)} aria-label={`go to step ${i + 1} of ${PHASES.length}`} aria-current={i === step ? "step" : undefined} style={{ width: 18, height: 26, padding: 0, border: "none", background: "transparent", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", touchAction: "manipulation" }}>
                <span style={{ width: i === step ? 10 : 7, height: i === step ? 10 : 7, borderRadius: 5, background: i === step ? theme.accent : theme.soft + "55", display: "block", transition: "all .2s ease" }} />
              </button>
            ))}
          </div>
          <NavBtn theme={theme} primary onClick={() => go(step + 1)} disabled={step === last}>→</NavBtn>
        </div>
      </div>
    </div>
  );
}
