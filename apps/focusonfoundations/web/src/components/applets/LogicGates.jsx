import React, { useState, useEffect, useRef } from "react";
import {
  GATES, gateOutput, gateCombos, comboKey,
  halfAdd, fullAdd, rippleAdd,
  GATE_QUIZ_ROUNDS, MYSTERY_ROUNDS, HALF_ADDER_QUIZ_ROUNDS, FULL_ADDER_QUIZ_ROUNDS, SUM_TARGETS, RIPPLE_MAX_INPUT,
  GATE_STEPS, QUIZ_STEPS, STEP_TITLES,
  STEP_INTROS, REVEAL_LINES, TABLE_DONE_LINES, QUIZ_LINES,
  SCREENS, screenTitle, screenCaption, fmt,
  mysteryCorrect, halfAddLine, fullAddLine, sumTargetLine, sumSuccessLine,
} from "../../lib/logic-gates.js";
import { createAppletSpeech } from "../../lib/applet-speech.js";
import { AUDIO_CLIP_IDS } from "../../lib/logic-gates-audio-manifest.js";
import {
  startTelemetrySession,
  logEvent,
  logQuizRound,
  logQuizAttempt,
  attachClickCapture,
  flushTelemetry,
} from "../../lib/applet-telemetry.js";

const { speak, primeSpeech, isMuted, setMuted } = createAppletSpeech({
  audioBase: "/audio/logic-gates/",
  clipIds: AUDIO_CLIP_IDS,
  muteKey: "logic-gates-muted",
});

const DISPLAY = 'ui-rounded, "SF Pro Rounded", "Baloo 2", Nunito, system-ui, sans-serif';
const BODY = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
const GLOW = "#FFD75E";

const THEMES = {
  switch: { key: "switch", icon: "💡", bg: "#FFF6DE", panel: "#FFFFFF", ink: "#3D3626", soft: "#9A8E74", accent: "#F0A32F", accent2: "#5A9E6F", edge: "#C27E14", gateFill: "#FFF1CC" },
  gates: { key: "gates", icon: "🚦", bg: "#EAEEFC", panel: "#FFFFFF", ink: "#2D3352", soft: "#7E86AC", accent: "#5A6BE0", accent2: "#E05A9B", edge: "#3D4CC0", gateFill: "#E3E8FD" },
  combine: { key: "combine", icon: "🧮", bg: "#E4F3EA", panel: "#FAFEFB", ink: "#26402E", soft: "#6B8A76", accent: "#2E9E5B", accent2: "#E9922E", edge: "#1F7A42", gateFill: "#DCEFE2" },
  adder: { key: "adder", icon: "🤖", bg: "#0E1524", panel: "#17223B", ink: "#E7EEF9", soft: "#8DA0BE", accent: "#37E0C8", accent2: "#4D9BFF", edge: "#1E9B89", gateFill: "#1E2C4A" },
};
const PHASES = ["switch", "switch", "gates", "gates", "gates", "gates", "gates", "gates", "gates", "gates", "gates", "gates", "gates", "gates", "combine", "combine", "adder", "adder", "adder", "adder", "adder"];

// ---------- SVG circuit parts ----------
function Wire({ d, on, theme, dashed }) {
  return (
    <path d={d} fill="none" stroke={dashed ? theme.soft + "66" : on ? theme.accent : theme.soft + "55"}
      strokeWidth={on && !dashed ? 5 : 3.5} strokeLinecap="round" strokeDasharray={dashed ? "5 7" : "none"}
      style={{ transition: "stroke .2s, stroke-width .2s" }} />
  );
}
const Dot = ({ x, y, on, theme }) => <circle cx={x} cy={y} r="4.5" fill={on ? theme.accent : theme.soft + "88"} style={{ transition: "fill .2s" }} />;

function SwitchG({ x, y, on, onToggle, label, theme, locked }) {
  const interactive = !locked && onToggle;
  return (
    <g transform={`translate(${x},${y})`} onClick={interactive ? onToggle : undefined}
      role={interactive ? "button" : undefined} tabIndex={interactive ? 0 : undefined}
      aria-pressed={interactive ? !!on : undefined} aria-label={interactive ? `switch ${label || ""}`.trim() : undefined}
      onKeyDown={interactive ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onToggle(); } } : undefined}
      style={{ cursor: interactive ? "pointer" : "default", outline: "none" }}>
      {label && <text x="22" y="-7" textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="16" fill={theme.soft}>{label}</text>}
      <rect x="-6" y="-24" width="56" height="102" fill="transparent" />
      <rect x="0" y="0" width="44" height="72" rx="13" fill={theme.bg} stroke={theme.soft + "66"} strokeWidth="2" />
      <rect x="5" y={on ? 37 : 5} width="34" height="30" rx="9" fill={on ? theme.accent : theme.soft + "55"} style={{ transition: "y .25s cubic-bezier(.2,.85,.25,1), fill .2s", filter: on ? `drop-shadow(0 0 6px ${theme.accent})` : "none" }} />
      <text x="22" y={on ? 58 : 26} textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="19" fill={on ? (theme.key === "adder" ? "#08121f" : "#fff") : theme.soft} style={{ pointerEvents: "none" }}>{on ? "1" : "0"}</text>
    </g>
  );
}

function BulbG({ x, y, on, theme, label, mystery, guess, onGuess }) {
  // mystery: show "?" instead of a state. guess: null | 0 | 1 shown as the bulb, tappable via onGuess.
  const guessing = onGuess !== undefined;
  const shown = guessing ? guess : on;
  const lit = shown === 1 || shown === true;
  const unknown = mystery || (guessing && (guess === null || guess === undefined));
  return (
    <g transform={`translate(${x},${y})`} onClick={guessing ? onGuess : undefined}
      role={guessing ? "button" : undefined} tabIndex={guessing ? 0 : undefined}
      aria-label={guessing ? `${label || "light"} guess: ${unknown ? "not set" : lit ? "on" : "off"}. Tap to change.` : undefined}
      onKeyDown={guessing ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onGuess(); } } : undefined}
      style={{ cursor: guessing ? "pointer" : "default", outline: "none" }}>
      {guessing && <circle r="30" fill="transparent" />}
      {lit && !unknown && <circle r="29" fill={GLOW} opacity="0.33" />}
      <circle r="17" fill={unknown ? theme.bg : lit ? "#FFE066" : theme.bg} stroke={unknown ? theme.soft + "88" : lit ? "#E0A800" : theme.soft + "88"} strokeWidth="2.5" strokeDasharray={unknown ? "4 4" : "none"} />
      {lit && !unknown && <circle cx="-5" cy="-6" r="4" fill="#FFF6C9" />}
      {unknown && <text y="6" textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="18" fill={theme.soft}>?</text>}
      <rect x="-7" y="16" width="14" height="8" rx="3" fill={theme.soft + "AA"} />
      <text y="42" textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="16" fill={unknown ? theme.soft : lit ? theme.accent : theme.soft}>{unknown ? "" : lit ? "1" : "0"}</text>
      {label && <text y="-28" textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="14" fill={theme.soft}>{label}</text>}
    </g>
  );
}

// Gate bodies drawn in a local 0..~86 x 0..64 box; input pins at x≈0 (y 16/48, or 32 for NOT), output at outX, y 32.
const GATE_DRAW = {
  NOT: { outX: 66, labelX: 17, labelSize: 11, shape: (t) => (<>
    <path d="M0,2 L54,32 L0,62 Z" fill={t.gateFill} stroke={t.ink} strokeWidth="2.5" strokeLinejoin="round" />
    <circle cx="60" cy="32" r="6" fill={t.gateFill} stroke={t.ink} strokeWidth="2.5" />
  </>) },
  AND: { outX: 74, labelX: 27, labelSize: 14, shape: (t) => (
    <path d="M0,2 L42,2 A30,30 0 0 1 42,62 L0,62 Z" fill={t.gateFill} stroke={t.ink} strokeWidth="2.5" strokeLinejoin="round" />
  ) },
  OR: { outX: 78, labelX: 30, labelSize: 14, shape: (t) => (
    <path d="M0,2 Q16,32 0,62 Q46,64 78,32 Q46,0 0,2 Z" fill={t.gateFill} stroke={t.ink} strokeWidth="2.5" strokeLinejoin="round" />
  ) },
  XOR: { outX: 86, labelX: 38, labelSize: 13, shape: (t) => (<>
    <path d="M8,2 Q24,32 8,62 Q54,64 86,32 Q54,0 8,2 Z" fill={t.gateFill} stroke={t.ink} strokeWidth="2.5" strokeLinejoin="round" />
    <path d="M0,2 Q16,32 0,62" fill="none" stroke={t.ink} strokeWidth="2.5" strokeLinecap="round" />
  </>) },
  NAND: { outX: 86, labelX: 25, labelSize: 12, shape: (t) => (<>
    <path d="M0,2 L42,2 A30,30 0 0 1 42,62 L0,62 Z" fill={t.gateFill} stroke={t.ink} strokeWidth="2.5" strokeLinejoin="round" />
    <circle cx="80" cy="32" r="6" fill={t.gateFill} stroke={t.ink} strokeWidth="2.5" />
  </>) },
};
const MYSTERY_BOX_OUT_X = 78;
function GateG({ x, y, type, theme, hideName }) {
  // hideName: mystery mode — a featureless box so the gate's shape gives nothing away.
  if (hideName) {
    return (
      <g transform={`translate(${x},${y})`}>
        <rect x="0" y="2" width={MYSTERY_BOX_OUT_X} height="60" rx="12" fill={theme.gateFill} stroke={theme.ink} strokeWidth="2.5" />
        <text x={MYSTERY_BOX_OUT_X / 2} y="42" textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="26" fill={theme.ink}>?</text>
      </g>
    );
  }
  const d = GATE_DRAW[type];
  return (
    <g transform={`translate(${x},${y})`}>
      {d.shape(theme)}
      <text x={d.labelX} y="38" textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize={d.labelSize} fill={theme.ink}>{type}</text>
    </g>
  );
}

// ---------- circuits ----------
// Wall outlet -> knife switch -> bulb. mode "no" (down closes the wire) or
// "nc" (wired the other way: resting up is closed, pulling down breaks it).
function KnifeSwitchCircuit({ mode, down, onToggle, theme }) {
  const closed = mode === "nc" ? !down : down;
  const angle = down ? 0 : -42;
  const Post = ({ x, y }) => <rect x={x} y={y} width="12" height="14" rx="2" fill={theme.soft} />;
  return (
    <svg viewBox="0 0 340 160" width="100%" style={{ maxWidth: 350, display: "block", margin: "0 auto" }}>
      {/* wall outlet + plug */}
      <rect x="10" y="36" width="38" height="56" rx="7" fill={theme.panel === "#FFFFFF" ? theme.bg : theme.gateFill} stroke={theme.soft + "88"} strokeWidth="2" />
      <rect x="21" y="50" width="4" height="12" rx="1.5" fill={theme.ink} />
      <rect x="33" y="50" width="4" height="12" rx="1.5" fill={theme.ink} />
      <circle cx="29" cy="76" r="3.4" fill={theme.ink} />
      <path d="M48,64 C62,64 58,112 72,112" fill="none" stroke={theme.accent} strokeWidth="4.5" strokeLinecap="round" />
      {/* wire from the wall is always live */}
      <Wire d="M72,112 H140" on={1} theme={theme} />
      {mode === "no"
        ? <Wire d="M220,112 H272" on={closed ? 1 : 0} theme={theme} />
        : <Wire d="M198,52 V34 H252 V112 H272" on={closed ? 1 : 0} theme={theme} />}
      {/* posts: pivot + the contact this switch is wired to */}
      <Post x={140} y={104} />
      {mode === "no" ? <Post x={208} y={104} /> : <Post x={192} y={52} />}
      {/* knife blade + handle, rotating around the pivot */}
      <g style={{ transform: `rotate(${angle}deg)`, transformOrigin: "146px 108px", transition: "transform .3s cubic-bezier(.2,.85,.25,1)" }}>
        <rect x="146" y="104" width="68" height="6" rx="3" fill={theme.ink} />
        <rect x="200" y="94" width="16" height="11" rx="4" fill={theme.accent} stroke={theme.edge} strokeWidth="1.5" />
      </g>
      {/* tap target over the whole switch */}
      <rect x="126" y="34" width="106" height="96" fill="transparent" rx="14" style={{ cursor: "pointer", outline: "none" }}
        role="button" tabIndex={0} aria-pressed={down} aria-label="switch"
        onClick={onToggle}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onToggle(); } }} />
      <BulbG x={294} y={112} on={closed} theme={theme} />
    </svg>
  );
}

function GateCircuit({ gate, inputs, onToggle, theme, locked, hideOutput, hideName }) {
  const two = GATES[gate].inputs === 2;
  const out = gateOutput(gate, inputs);
  const outX = 170 + (hideName ? MYSTERY_BOX_OUT_X : GATE_DRAW[gate].outX);
  return (
    <svg viewBox="0 -10 360 202" width="100%" style={{ maxWidth: 380, display: "block", margin: "0 auto" }}>
      {two ? (<>
        <Wire d="M62,50 H110 V80 H176" on={inputs[0]} theme={theme} />
        <Wire d="M62,142 H130 V112 H176" on={inputs[1]} theme={theme} />
      </>) : <Wire d="M62,96 H176" on={inputs[0]} theme={theme} />}
      <Wire d={`M${outX},96 H288`} on={hideOutput ? 0 : out} theme={theme} dashed={hideOutput} />
      <GateG x={170} y={64} type={gate} theme={theme} hideName={hideName} />
      {two ? (<>
        <SwitchG x={18} y={14} on={inputs[0]} onToggle={onToggle && (() => onToggle(0))} label="A" theme={theme} locked={locked} />
        <SwitchG x={18} y={106} on={inputs[1]} onToggle={onToggle && (() => onToggle(1))} label="B" theme={theme} locked={locked} />
      </>) : <SwitchG x={18} y={60} on={inputs[0]} onToggle={onToggle && (() => onToggle(0))} label="A" theme={theme} locked={locked} />}
      <BulbG x={310} y={96} on={out} theme={theme} mystery={hideOutput} />
    </svg>
  );
}

function HalfAdderCircuit({ a, b, theme, revealed, locked, onToggle, guessS, guessC, onGuessS, onGuessC, hideOutputs }) {
  const { sum, carry } = halfAdd(a, b);
  const guessing = onGuessS !== undefined;
  return (
    <svg viewBox="0 -8 384 240" width="100%" style={{ maxWidth: 400, display: "block", margin: "0 auto" }}>
      <Wire d="M62,56 H96 V36 H184" on={a} theme={theme} />
      <Wire d="M96,56 V148 H184" on={a} theme={theme} />
      <Wire d="M62,160 H112 V68 H184" on={b} theme={theme} />
      <Wire d="M112,160 H140 V180 H184" on={b} theme={theme} />
      <Dot x={96} y={56} on={a} theme={theme} />
      <Dot x={112} y={160} on={b} theme={theme} />
      <Wire d="M266,52 H300" on={guessing || hideOutputs ? 0 : sum} theme={theme} dashed={guessing || hideOutputs} />
      <Wire d="M254,164 H300" on={guessing || hideOutputs ? 0 : carry} theme={theme} dashed={guessing || hideOutputs} />
      <GateG x={180} y={20} type="XOR" theme={theme} />
      <GateG x={180} y={132} type="AND" theme={theme} />
      <SwitchG x={18} y={20} on={a} onToggle={onToggle && (() => onToggle(0))} label="A" theme={theme} locked={locked} />
      <SwitchG x={18} y={124} on={b} onToggle={onToggle && (() => onToggle(1))} label="B" theme={theme} locked={locked} />
      <BulbG x={324} y={52} on={sum} theme={theme} label={revealed ? "S · ones" : ""} guess={guessS} onGuess={onGuessS} mystery={hideOutputs} />
      <BulbG x={324} y={164} on={carry} theme={theme} label={revealed ? "C · carry" : ""} guess={guessC} onGuess={onGuessC} mystery={hideOutputs} />
    </svg>
  );
}

function FullAdderCircuit({ a, b, cin, theme, onToggle }) {
  const s1 = a ^ b, c1 = a & b, c2 = s1 & cin;
  const { sum, cout } = fullAdd(a, b, cin);
  return (
    <svg viewBox="0 -10 490 306" width="100%" style={{ maxWidth: 500, display: "block", margin: "0 auto" }}>
      {/* A */}
      <Wire d="M54,52 H80 V46 H114" on={a} theme={theme} />
      <Wire d="M80,52 V156 H114" on={a} theme={theme} />
      <Dot x={80} y={52} on={a} theme={theme} />
      {/* B */}
      <Wire d="M54,148 H92 V78 H114" on={b} theme={theme} />
      <Wire d="M92,148 V188 H114" on={b} theme={theme} />
      <Dot x={92} y={148} on={b} theme={theme} />
      {/* Cin */}
      <Wire d="M54,244 H236 V56 H258" on={cin} theme={theme} />
      <Wire d="M236,180 H254" on={cin} theme={theme} />
      <Dot x={236} y={180} on={cin} theme={theme} />
      {/* s1 = A xor B */}
      <Wire d="M196,62 H216 V24 H258" on={s1} theme={theme} />
      <Wire d="M216,62 V148 H254" on={s1} theme={theme} />
      <Dot x={216} y={62} on={s1} theme={theme} />
      {/* carries into OR */}
      <Wire d="M184,172 H210 V212 H362" on={c1} theme={theme} />
      <Wire d="M324,164 H336 V244 H362" on={c2} theme={theme} />
      {/* outputs */}
      <Wire d="M336,40 H398" on={sum} theme={theme} />
      <Wire d="M434,228 H443" on={cout} theme={theme} />
      <GateG x={110} y={30} type="XOR" theme={theme} />
      <GateG x={250} y={8} type="XOR" theme={theme} />
      <GateG x={110} y={140} type="AND" theme={theme} />
      <GateG x={250} y={132} type="AND" theme={theme} />
      <GateG x={356} y={196} type="OR" theme={theme} />
      <SwitchG x={10} y={16} on={a} onToggle={() => onToggle(0)} label="A" theme={theme} />
      <SwitchG x={10} y={112} on={b} onToggle={() => onToggle(1)} label="B" theme={theme} />
      <SwitchG x={10} y={208} on={cin} onToggle={() => onToggle(2)} label="Cin" theme={theme} />
      <BulbG x={420} y={40} on={sum} theme={theme} label="S" />
      <BulbG x={464} y={228} on={cout} theme={theme} label="Cout" />
    </svg>
  );
}

function RippleCircuit({ a, b, theme, onToggleBit }) {
  const r = rippleAdd(a, b);
  const a1 = a & 1, a2 = (a >> 1) & 1, b1 = b & 1, b2 = (b >> 1) & 1;
  const AdderBox = ({ x }) => (
    <g transform={`translate(${x},254)`}>
      <rect width="100" height="58" rx="14" fill={theme.gateFill} stroke={theme.ink} strokeWidth="2.5" />
      <text x="50" y="26" textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="20" fill={theme.ink}>＋</text>
      <text x="50" y="46" textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="11" fill={theme.soft}>full adder</text>
    </g>
  );
  const PlaceHead = ({ x, label }) => (
    <text x={x} y="12" textAnchor="middle" fontFamily={BODY} fontSize="13" fontWeight="700" fill={theme.accent2}>{label}</text>
  );
  const RowLabel = ({ y, label }) => (
    <text x="30" y={y} textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="22" fill={theme.soft}>{label}</text>
  );
  return (
    <svg viewBox="0 0 384 402" width="100%" style={{ maxWidth: 400, display: "block", margin: "0 auto" }}>
      <PlaceHead x={130} label="twos place" />
      <PlaceHead x={294} label="ones place" />
      <RowLabel y={80} label="A" />
      <RowLabel y={180} label="B" />
      <Wire d="M110,106 V254" on={a2} theme={theme} />
      <Wire d="M150,206 V254" on={b2} theme={theme} />
      <Wire d="M274,106 V254" on={a1} theme={theme} />
      <Wire d="M314,206 V254" on={b1} theme={theme} />
      {/* carry: ones-place adder feeds the twos-place adder, right to left like written addition */}
      <Wire d="M249,283 H193" on={r.carry0} theme={theme} />
      <text x="221" y="275" textAnchor="middle" fontFamily={BODY} fontSize="11" fontWeight="700" fill={r.carry0 ? theme.accent : theme.soft}>carry</text>
      <path d="M201,277 L193,283 L201,289 Z" fill={r.carry0 ? theme.accent : theme.soft + "88"} />
      {/* carry out of the twos place lands in the fours place */}
      <Wire d="M85,283 H48 V320" on={r.carry1} theme={theme} />
      <Wire d="M135,312 V320" on={r.bits[1]} theme={theme} />
      <Wire d="M299,312 V320" on={r.bits[2]} theme={theme} />
      <AdderBox x={85} />
      <AdderBox x={249} />
      <SwitchG x={88} y={34} on={a2} onToggle={() => onToggleBit("a", 1)} label="A₂" theme={theme} />
      <SwitchG x={128} y={134} on={b2} onToggle={() => onToggleBit("b", 1)} label="B₂" theme={theme} />
      <SwitchG x={252} y={34} on={a1} onToggle={() => onToggleBit("a", 0)} label="A₁" theme={theme} />
      <SwitchG x={292} y={134} on={b1} onToggle={() => onToggleBit("b", 0)} label="B₁" theme={theme} />
      <BulbG x={48} y={338} on={r.bits[0]} theme={theme} />
      <BulbG x={135} y={338} on={r.bits[1]} theme={theme} />
      <BulbG x={299} y={338} on={r.bits[2]} theme={theme} />
      {[[48, "fours"], [135, "twos"], [299, "ones"]].map(([x, place]) => (
        <text key={place} x={x} y="398" textAnchor="middle" fontFamily={BODY} fontSize="12" fontWeight="700" fill={theme.accent2}>{place}</text>
      ))}
    </svg>
  );
}

// Box-level full adder for the predict-the-outputs quiz: three locked switches
// in, sum + carry-out bulbs out (tappable guesses until revealed).
function FullAdderBoxCircuit({ a, b, cin, theme, revealed, guessS, guessC, onGuessS, onGuessC }) {
  const { sum, cout } = fullAdd(a, b, cin);
  const guessing = !revealed;
  return (
    <svg viewBox="0 0 384 268" width="100%" style={{ maxWidth: 400, display: "block", margin: "0 auto" }}>
      <Wire d="M152,88 V120" on={a} theme={theme} />
      <Wire d="M212,88 V120" on={b} theme={theme} />
      <Wire d="M322,136 H240" on={cin} theme={theme} />
      <Wire d="M200,184 V210" on={revealed ? sum : 0} theme={theme} dashed={guessing} />
      <Wire d="M120,152 H74" on={revealed ? cout : 0} theme={theme} dashed={guessing} />
      <rect x="120" y="120" width="120" height="64" rx="14" fill={theme.gateFill} stroke={theme.ink} strokeWidth="2.5" />
      <text x="180" y="147" textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="20" fill={theme.ink}>＋</text>
      <text x="180" y="169" textAnchor="middle" fontFamily={DISPLAY} fontWeight="800" fontSize="11" fill={theme.soft}>full adder</text>
      <SwitchG x={130} y={16} on={a} label="A" theme={theme} locked />
      <SwitchG x={190} y={16} on={b} label="B" theme={theme} locked />
      <SwitchG x={322} y={100} on={cin} label="Cin" theme={theme} locked />
      {revealed
        ? <>
            <BulbG x={56} y={152} on={cout} theme={theme} label="Cout · twos" />
            <BulbG x={200} y={228} on={sum} theme={theme} label="" />
          </>
        : <>
            <BulbG x={56} y={152} theme={theme} label="Cout · twos" guess={guessC} onGuess={onGuessC} />
            <BulbG x={200} y={228} theme={theme} label="" guess={guessS} onGuess={onGuessS} />
          </>}
      <text x="230" y="232" textAnchor="start" fontFamily={DISPLAY} fontWeight="800" fontSize="14" fill={theme.soft}>S · ones</text>
    </svg>
  );
}

// ---------- HTML parts ----------
function NavBtn({ children, onClick, disabled, theme, primary }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      fontFamily: DISPLAY, fontWeight: 800, fontSize: 18, padding: "12px 20px", borderRadius: 16, cursor: disabled ? "default" : "pointer", touchAction: "manipulation",
      background: primary ? theme.accent : "transparent", color: primary ? (theme.key === "adder" ? "#08121f" : "#fff") : theme.ink,
      border: primary ? "none" : `2.5px solid ${theme.soft}55`, opacity: disabled ? 0.35 : 1, boxShadow: primary && !disabled ? `0 4px 0 ${theme.edge}` : "none",
    }}>{children}</button>
  );
}
function QMark({ onClick, theme }) {
  return (
    <button onClick={onClick} aria-label="show the answer" style={{
      width: 104, height: 104, borderRadius: 52, fontSize: 56, fontFamily: DISPLAY, fontWeight: 800, border: "none",
      background: theme.accent, color: theme.key === "adder" ? "#08121f" : "#fff", boxShadow: `0 6px 0 ${theme.edge}`,
      cursor: "pointer", touchAction: "manipulation", animation: "pulse 1.4s ease-in-out infinite",
    }}>?</button>
  );
}
function BitChip({ v, theme, size = 30 }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: size + 10, height: size + 12, borderRadius: 9, background: theme.bg, fontFamily: DISPLAY, fontWeight: 800, fontSize: size * 0.72, color: v ? theme.accent : theme.soft, boxShadow: "inset 0 2px 5px rgba(0,0,0,.14)" }}>{v}</span>
  );
}

function TruthTable({ gate, visited, current, theme }) {
  const combos = gateCombos(gate);
  const two = GATES[gate].inputs === 2;
  const cell = { width: 40, textAlign: "center", fontFamily: DISPLAY, fontWeight: 800, fontSize: 17, padding: "4px 0" };
  const allDone = combos.every((c) => visited[comboKey(c)]);
  return (
    <div style={{ maxWidth: 250, margin: "12px auto 0" }}>
      <div style={{ display: "flex", justifyContent: "center", borderBottom: `2px solid ${theme.soft}44`, paddingBottom: 2, marginBottom: 2 }}>
        <span style={{ ...cell, color: theme.soft, fontSize: 14 }}>A</span>
        {two && <span style={{ ...cell, color: theme.soft, fontSize: 14 }}>B</span>}
        <span style={{ ...cell, color: theme.soft, fontSize: 14 }}>→</span>
        <span style={{ ...cell, color: theme.soft, fontSize: 14 }}>💡</span>
        <span style={{ ...cell, width: 30 }} />
      </div>
      {combos.map((c) => {
        const k = comboKey(c);
        const seen = !!visited[k];
        const isCur = k === comboKey(current);
        const out = gateOutput(gate, c);
        return (
          <div key={k} style={{ display: "flex", justifyContent: "center", borderRadius: 10, background: isCur ? theme.accent + "22" : "transparent", transition: "background .25s" }}>
            <span style={{ ...cell, color: c[0] ? theme.accent : theme.soft }}>{c[0]}</span>
            {two && <span style={{ ...cell, color: c[1] ? theme.accent : theme.soft }}>{c[1]}</span>}
            <span style={{ ...cell, color: theme.soft }}>→</span>
            <span style={{ ...cell, color: seen ? (out ? theme.accent : theme.soft) : theme.soft + "88" }}>{seen ? out : "?"}</span>
            <span style={{ ...cell, width: 30, fontSize: 14 }}>{seen ? "✓" : ""}</span>
          </div>
        );
      })}
      {allDone && <div style={{ textAlign: "center", marginTop: 8, fontFamily: DISPLAY, fontWeight: 800, fontSize: 16, color: theme.accent, animation: "pop .5s ease" }}>⭐ Truth table complete!</div>}
    </div>
  );
}

function AnswerButtons({ onAnswer, theme, disabled }) {
  const base = { fontFamily: DISPLAY, fontWeight: 800, fontSize: 20, padding: "14px 26px", borderRadius: 18, border: `3px solid ${theme.soft}55`, background: theme.bg, color: theme.ink, cursor: disabled ? "default" : "pointer", touchAction: "manipulation", opacity: disabled ? 0.4 : 1 };
  return (
    <div style={{ display: "flex", gap: 16, justifyContent: "center" }}>
      <button disabled={disabled} onClick={() => onAnswer(0)} style={base} aria-label="light off">⚫ Off</button>
      <button disabled={disabled} onClick={() => onAnswer(1)} style={base} aria-label="light on">💡 On</button>
    </div>
  );
}

const Stars = ({ n, total, theme }) => (
  <div style={{ display: "flex", gap: 5, justifyContent: "center", margin: "6px 0" }}>
    {Array.from({ length: total }).map((_, i) => <span key={i} style={{ fontSize: 20, opacity: i < n ? 1 : 0.25 }}>⭐</span>)}
  </div>
);

// ===================================================================
export default function App() {
  const [started, setStarted] = useState(false);
  const [step, setStep] = useState(0);
  const [reduced, setReduced] = useState(false);
  const [muted, setMutedState] = useState(false);
  // step-local state
  const [knife0, setKnife0] = useState(false);
  const [knife1, setKnife1] = useState(false);
  const [combineRevealed, setCombineRevealed] = useState(false);
  const [explore, setExplore] = useState({});
  const [quiz, setQuiz] = useState({});
  const [mystery, setMystery] = useState({ round: 0, inputs: [0, 0], solved: false, solvedCount: 0 });
  const [half, setHalf] = useState({ inputs: [0, 0], seenBoth: false, revealed: false });
  const [haq, setHaq] = useState({ round: 0, guess: [null, null], revealed: false, finished: false });
  const [fa, setFa] = useState([0, 0, 0]);
  const [faq, setFaq] = useState({ round: 0, guess: [null, null], revealed: false, finished: false });
  const [ripple, setRipple] = useState({ targetIdx: 0, a: 0, b: 0, result: null, wins: 0 });
  const appletRootRef = useRef(null);
  const previousTelemetryStep = useRef(null);

  useEffect(() => { try { setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches); } catch (e) {} }, []);
  useEffect(() => { primeSpeech(); setMutedState(isMuted()); }, []);

  const theme = THEMES[PHASES[step]];
  const last = PHASES.length - 1;
  const SPEAK = STEP_INTROS;
  const spokenStep = useRef(-1);
  function predictPrompt(inputs) {
    return inputs.join("");
  }
  function halfPrompt(inputs) {
    return `a=${inputs[0]},b=${inputs[1]}`;
  }
  function ripplePrompt(target) {
    return `target=${target}`;
  }
  function faPrompt(inputs) {
    return `a=${inputs[0]},b=${inputs[1]},cin=${inputs[2]}`;
  }
  function logPresentedRoundForStep(stepIdx) {
    const gate = QUIZ_STEPS[stepIdx];
    if (gate) {
      const st = quizFor(stepIdx);
      if (st.finished) return;
      const rounds = GATE_QUIZ_ROUNDS[gate];
      const round = Math.min(st.round, rounds.length - 1);
      logQuizRound(gate, round, predictPrompt(rounds[round]), stepIdx);
      return;
    }
    if (stepIdx === 12 && !mystery.solved) {
      const gateName = MYSTERY_ROUNDS[mystery.round % MYSTERY_ROUNDS.length];
      logQuizRound("mystery", mystery.round, gateName, stepIdx);
      return;
    }
    if (stepIdx === 15 && !haq.finished) {
      const rounds = HALF_ADDER_QUIZ_ROUNDS;
      const round = Math.min(haq.round, rounds.length - 1);
      logQuizRound("half-adder", round, halfPrompt(rounds[round]), stepIdx);
      return;
    }
    if (stepIdx === 18 && !faq.finished) {
      const rounds = FULL_ADDER_QUIZ_ROUNDS;
      const round = Math.min(faq.round, rounds.length - 1);
      logQuizRound("full-adder", round, faPrompt(rounds[round]), stepIdx);
      return;
    }
    if (stepIdx === 19) {
      const target = SUM_TARGETS[ripple.targetIdx % SUM_TARGETS.length];
      logQuizRound("ripple", ripple.targetIdx, ripplePrompt(target), stepIdx);
    }
  }
  useEffect(() => { if (!started) return; if (spokenStep.current === step) return; spokenStep.current = step; speak(SPEAK[step]); }, [step, started]);
  const go = (s) => setStep(Math.max(0, Math.min(last, s)));
  useEffect(() => {
    if (!started) return;
    return attachClickCapture(appletRootRef.current);
  }, [started]);
  useEffect(() => {
    if (!started) {
      previousTelemetryStep.current = null;
      return;
    }
    const previous = previousTelemetryStep.current;
    if (previous === null) {
      logEvent("step-enter", { step, detail: { title: STEP_TITLES[step], phase: PHASES[step] } });
      logPresentedRoundForStep(step);
      flushTelemetry();
      previousTelemetryStep.current = step;
      return;
    }
    if (previous !== step) {
      logEvent("step-leave", { step: previous, detail: { nextStep: step } });
      logEvent("step-enter", { step, detail: { title: STEP_TITLES[step], previousStep: previous, phase: PHASES[step] } });
      logPresentedRoundForStep(step);
      flushTelemetry();
      previousTelemetryStep.current = step;
    }
  }, [started, step]);
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
    logEvent("mute", { step, target: "sound", detail: { muted: m } });
    if (!m) speak(SPEAK[step]);
  };
  const startApplet = () => {
    startTelemetrySession({ applet: "logic-gates" });
    logEvent("applet-start", { step, target: "start", detail: { step, steps: STEP_TITLES } });
    primeSpeech(); spokenStep.current = step; speak(SPEAK[step]); setStarted(true);
  };

  const Title = ({ children }) => (
    <h1 style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 22, lineHeight: 1.2, color: theme.ink, margin: "0 0 8px", textAlign: "center" }}>{children}</h1>
  );
  const Caption = ({ children }) => (
    <div style={{ textAlign: "center", fontFamily: BODY, fontSize: 14.5, color: theme.soft, marginTop: 4, lineHeight: 1.4 }}>{children}</div>
  );

  // ----- gate explore step -----
  function exploreFor(stepIdx, gate) {
    if (explore[stepIdx]) return explore[stepIdx];
    const zeros = Array(GATES[gate].inputs).fill(0);
    return { inputs: zeros, visited: { [comboKey(zeros)]: true }, done: false };
  }
  function GateExploreStep({ stepIdx, gate }) {
    const st = exploreFor(stepIdx, gate);
    const toggle = (i) => {
      const inputs = st.inputs.slice(); inputs[i] = inputs[i] ? 0 : 1;
      const visited = { ...st.visited, [comboKey(inputs)]: true };
      const done = gateCombos(gate).every((c) => visited[comboKey(c)]);
      setExplore({ ...explore, [stepIdx]: { inputs, visited, done } });
      logEvent("toggle", { step: stepIdx, target: `${gate} ${i === 0 ? "A" : "B"}`, detail: { gate, inputs, out: gateOutput(gate, inputs), tableDone: done } });
      if (done && !st.done) speak(TABLE_DONE_LINES[gate]);
    };
    return (
      <div>
        <Title>{screenTitle(stepIdx, { gate })}</Title>
        <GateCircuit gate={gate} inputs={st.inputs} onToggle={toggle} theme={theme} />
        {screenCaption(stepIdx, gate) && <Caption>{screenCaption(stepIdx, gate)}</Caption>}
        <TruthTable gate={gate} visited={st.visited} current={st.inputs} theme={theme} />
      </div>
    );
  }

  // ----- predict quiz step -----
  function quizFor(stepIdx) {
    return quiz[stepIdx] || { round: 0, revealed: false, wrong: false, finished: false };
  }
  function PredictQuizStep({ stepIdx, gate }) {
    const st = quizFor(stepIdx);
    const rounds = GATE_QUIZ_ROUNDS[gate];
    const inputs = rounds[Math.min(st.round, rounds.length - 1)];
    const out = gateOutput(gate, inputs);
    const set = (patch) => setQuiz({ ...quiz, [stepIdx]: { ...st, ...patch } });
    const answer = (v) => {
      if (st.revealed) return;
      logQuizAttempt(gate, st.round, predictPrompt(inputs), String(v), v === out, stepIdx);
      if (v === out) { set({ revealed: true, wrong: false }); speak(QUIZ_LINES.correct); }
      else { set({ wrong: true }); speak(QUIZ_LINES.tryAgain); }
    };
    const next = () => {
      if (st.round + 1 >= rounds.length) { set({ finished: true }); speak(gate === "NOT" ? QUIZ_LINES.gotIt : QUIZ_LINES.quizDone); }
      else {
        const nextRound = st.round + 1;
        set({ round: nextRound, revealed: false, wrong: false });
        logQuizRound(gate, nextRound, predictPrompt(rounds[nextRound]), stepIdx);
      }
    };
    if (st.finished) {
      const scr = SCREENS[stepIdx];
      return (
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 56, animation: reduced ? "none" : "pop .5s ease" }}>{gate === "NOT" ? "🎉" : "🏆"}</div>
          <Title>{gate === "NOT" ? scr.titleQuizDoneNot : fmt(scr.titleQuizDone, { gate })}</Title>
          {gate !== "NOT" && <Stars n={rounds.length} total={rounds.length} theme={theme} />}
          <NavBtn theme={theme} onClick={() => { set({ round: 0, revealed: false, wrong: false, finished: false }); logQuizRound(gate, 0, predictPrompt(rounds[0]), stepIdx); }}>Play again</NavBtn>
        </div>
      );
    }
    return (
      <div>
        <Title>{fmt(SCREENS[stepIdx].titleQuiz, { gate })}</Title>
        <Stars n={st.round + (st.revealed ? 1 : 0)} total={rounds.length} theme={theme} />
        <GateCircuit gate={gate} inputs={inputs} theme={theme} locked hideOutput={!st.revealed} />
        <div style={{ marginTop: 14, minHeight: 64 }}>
          {st.revealed
            ? <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 38 }}>✅</div>
                <div style={{ marginTop: 8 }}><NavBtn theme={theme} primary onClick={next}>{st.round + 1 >= rounds.length ? "Finish 🏆" : "Next →"}</NavBtn></div>
              </div>
            : <>
                <AnswerButtons onAnswer={answer} theme={theme} />
                {st.wrong && <div style={{ textAlign: "center", fontSize: 30, marginTop: 8 }}>🔁</div>}
              </>}
        </div>
      </div>
    );
  }

  // ----- mystery gate step -----
  function MysteryStep() {
    const gate = MYSTERY_ROUNDS[mystery.round % MYSTERY_ROUNDS.length];
    const toggle = (i) => {
      const inputs = mystery.inputs.slice(); inputs[i] = inputs[i] ? 0 : 1;
      setMystery({ ...mystery, inputs });
    };
    const guess = (g) => {
      if (mystery.solved) return;
      logQuizAttempt("mystery", mystery.round, gate, g, g === gate, 12);
      if (g === gate) { setMystery({ ...mystery, solved: true, solvedCount: mystery.solvedCount + 1 }); speak(mysteryCorrect(gate)); }
      else speak(QUIZ_LINES.tryAgain);
    };
    const nextRound = () => {
      const next = mystery.round + 1;
      const nextGate = MYSTERY_ROUNDS[next % MYSTERY_ROUNDS.length];
      setMystery({ ...mystery, round: next, inputs: [0, 0], solved: false });
      logQuizRound("mystery", next, nextGate, 12);
    };
    const choiceStyle = (g) => ({
      fontFamily: DISPLAY, fontWeight: 800, fontSize: 17, padding: "10px 16px", borderRadius: 14, cursor: "pointer", touchAction: "manipulation",
      border: `3px solid ${mystery.solved && g === gate ? theme.accent : theme.soft + "55"}`,
      background: mystery.solved && g === gate ? theme.accent + "22" : theme.bg, color: theme.ink,
    });
    return (
      <div>
        <Title>{SCREENS[12].title}</Title>
        <Stars n={Math.min(mystery.solvedCount, MYSTERY_ROUNDS.length)} total={MYSTERY_ROUNDS.length} theme={theme} />
        <GateCircuit gate={gate} inputs={mystery.inputs} onToggle={toggle} theme={theme} hideName={!mystery.solved} />
        <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap", marginTop: 14 }}>
          {["OR", "AND", "XOR", "NAND"].map((g) => (
            <button key={g} onClick={() => guess(g)} style={choiceStyle(g)}>{g}</button>
          ))}
        </div>
        {mystery.solved && (
          <div style={{ textAlign: "center", marginTop: 12 }}>
            <span style={{ fontSize: 30 }}>🎉</span>
            <div style={{ marginTop: 8 }}><NavBtn theme={theme} primary onClick={nextRound}>Another mystery →</NavBtn></div>
          </div>
        )}
      </div>
    );
  }

  // ----- half adder steps -----
  function HalfAdderStep() {
    const [a, b] = half.inputs;
    const toggle = (i) => {
      const inputs = half.inputs.slice(); inputs[i] = inputs[i] ? 0 : 1;
      const seenBoth = half.seenBoth || (inputs[0] === 1 && inputs[1] === 1);
      setHalf({ ...half, inputs, seenBoth });
      const nextAdd = halfAdd(inputs[0], inputs[1]);
      logEvent("toggle", { step: 14, target: `half-adder ${i === 0 ? "A" : "B"}`, detail: { inputs, sum: nextAdd.sum, carry: nextAdd.carry } });
      if (half.revealed) speak(halfAddLine(inputs[0], inputs[1]));
    };
    const { sum, carry } = halfAdd(a, b);
    const scr = SCREENS[14];
    return (
      <div>
        <Title>{scr.title}</Title>
        <HalfAdderCircuit a={a} b={b} theme={theme} revealed={half.revealed} onToggle={toggle} />
        {!half.revealed
          ? (half.seenBoth
              ? <div style={{ textAlign: "center", marginTop: 10 }}>
                  <Caption>{scr.captions?.bothOn}</Caption>
                  <div style={{ marginTop: 10 }}><QMark theme={theme} onClick={() => { setHalf({ ...half, revealed: true }); logEvent("reveal", { step: 14, target: "half-adder", detail: { item: "half-adder" } }); speak(REVEAL_LINES.halfAdder); }} /></div>
                </div>
              : <Caption>{scr.caption}</Caption>)
          : <div style={{ textAlign: "center", marginTop: 8 }}>
              <div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 24, color: theme.ink }}>
                {a} + {b} = <BitChip v={carry} theme={theme} /> <BitChip v={sum} theme={theme} />
                <span style={{ color: theme.soft, fontSize: 18, marginLeft: 10 }}>binary</span>
                <span style={{ color: theme.accent, marginLeft: 10 }}>= {a + b}</span>
                <span style={{ color: theme.soft, fontSize: 16, marginLeft: 6 }}>(base 10)</span>
              </div>
              <Caption>{scr.captions?.revealed}</Caption>
            </div>}
      </div>
    );
  }
  function HalfAdderQuizStep() {
    const rounds = HALF_ADDER_QUIZ_ROUNDS;
    const [a, b] = rounds[Math.min(haq.round, rounds.length - 1)];
    const { sum, carry } = halfAdd(a, b);
    const cycle = (v) => (v === null ? 1 : v === 1 ? 0 : 1);
    const setGuess = (i) => {
      if (haq.revealed) return;
      const guess = haq.guess.slice(); guess[i] = cycle(guess[i]);
      setHaq({ ...haq, guess });
    };
    const check = () => {
      const ok = haq.guess[0] === sum && haq.guess[1] === carry;
      logQuizAttempt("half-adder", haq.round, halfPrompt([a, b]), `s=${haq.guess[0]},c=${haq.guess[1]}`, ok, 15);
      if (ok) { setHaq({ ...haq, revealed: true }); speak(halfAddLine(a, b)); }
      else speak(QUIZ_LINES.tryAgain);
    };
    const next = () => {
      if (haq.round + 1 >= rounds.length) { setHaq({ ...haq, finished: true }); speak(QUIZ_LINES.quizDone); }
      else {
        const nextRound = haq.round + 1;
        setHaq({ round: nextRound, guess: [null, null], revealed: false, finished: false });
        logQuizRound("half-adder", nextRound, halfPrompt(rounds[nextRound]), 15);
      }
    };
    if (haq.finished) {
      return (
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 56, animation: reduced ? "none" : "pop .5s ease" }}>🏆</div>
          <Title>{SCREENS[15].titleQuizDone}</Title>
          <Stars n={rounds.length} total={rounds.length} theme={theme} />
          <NavBtn theme={theme} onClick={() => { setHaq({ round: 0, guess: [null, null], revealed: false, finished: false }); logQuizRound("half-adder", 0, halfPrompt(rounds[0]), 15); }}>Play again</NavBtn>
        </div>
      );
    }
    return (
      <div>
        <Title>{SCREENS[15].title}</Title>
        <Stars n={haq.round + (haq.revealed ? 1 : 0)} total={rounds.length} theme={theme} />
        {haq.revealed
          ? <HalfAdderCircuit a={a} b={b} theme={theme} revealed locked />
          : <HalfAdderCircuit a={a} b={b} theme={theme} locked guessS={haq.guess[0]} guessC={haq.guess[1]} onGuessS={() => setGuess(0)} onGuessC={() => setGuess(1)} />}
        <div style={{ marginTop: 12, minHeight: 60, textAlign: "center" }}>
          {haq.revealed
            ? <>
                <div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 22, color: theme.ink }}>{a} + {b} = <BitChip v={carry} theme={theme} /> <BitChip v={sum} theme={theme} /> <span style={{ color: theme.accent }}>= {a + b}</span> <span style={{ color: theme.soft, fontSize: 15 }}>(base 10)</span> ✅</div>
                <div style={{ marginTop: 10 }}><NavBtn theme={theme} primary onClick={next}>{haq.round + 1 >= rounds.length ? "Finish 🏆" : "Next →"}</NavBtn></div>
              </>
            : <>
                <Caption>{SCREENS[15].caption}</Caption>
                <div style={{ marginTop: 8 }}><NavBtn theme={theme} primary onClick={check} disabled={haq.guess[0] === null || haq.guess[1] === null}>Check ✓</NavBtn></div>
              </>}
        </div>
      </div>
    );
  }

  // ----- full adder + finale -----
  function FullAdderStep() {
    const [a, b, cin] = fa;
    const total = a + b + cin;
    const { sum, cout } = fullAdd(a, b, cin);
    const toggle = (i) => {
      const next = fa.slice(); next[i] = next[i] ? 0 : 1;
      setFa(next);
      const result = fullAdd(next[0], next[1], next[2]);
      logEvent("toggle", { step: 16, target: `full-adder ${["A", "B", "Cin"][i]}`, detail: { inputs: next, sum: result.sum, cout: result.cout } });
      speak(fullAddLine(next[0], next[1], next[2]));
    };
    return (
      <div>
        <Title>{SCREENS[16].title}</Title>
        <FullAdderCircuit a={a} b={b} cin={cin} theme={theme} onToggle={toggle} />
        <div style={{ textAlign: "center", marginTop: 8, fontFamily: DISPLAY, fontWeight: 800, fontSize: 22, color: theme.ink }}>
          {a} + {b} + {cin} = <BitChip v={cout} theme={theme} /> <BitChip v={sum} theme={theme} />
          <span style={{ color: theme.accent, marginLeft: 10 }}>= {total}</span>
          <span style={{ color: theme.soft, fontSize: 16, marginLeft: 6 }}>(base 10)</span>
        </div>
        <Caption>{SCREENS[16].caption}</Caption>
      </div>
    );
  }
  function RippleStep() {
    const target = SUM_TARGETS[ripple.targetIdx % SUM_TARGETS.length];
    const solved = ripple.result === "ok";
    const toggleBit = (which, bit) => {
      const v = ripple[which] ^ (1 << bit);
      const a = which === "a" ? v : ripple.a;
      const b = which === "b" ? v : ripple.b;
      setRipple({ ...ripple, [which]: v, result: null });
      logEvent("toggle", { step: 19, target: `ripple ${which.toUpperCase()}${bit + 1}`, detail: { a, b } });
    };
    const check = () => {
      const ok = ripple.a + ripple.b === target;
      logQuizAttempt("ripple", ripple.targetIdx, ripplePrompt(target), `a=${ripple.a},b=${ripple.b}`, ok, 19);
      if (ok) { setRipple({ ...ripple, result: "ok", wins: ripple.wins + 1 }); speak(sumSuccessLine(ripple.a, ripple.b)); }
      else { setRipple({ ...ripple, result: "no" }); speak(QUIZ_LINES.tryAgain); }
    };
    const another = () => {
      let idx = ripple.targetIdx + 1;
      if (SUM_TARGETS[idx % SUM_TARGETS.length] === ripple.a + ripple.b) idx += 1;
      const t = SUM_TARGETS[idx % SUM_TARGETS.length];
      setRipple({ ...ripple, targetIdx: idx, result: null });
      logQuizRound("ripple", idx, ripplePrompt(t), 19);
      speak(sumTargetLine(t));
    };
    const Cell = ({ ch, color, w = 22 }) => (
      <span style={{ display: "inline-block", width: w, textAlign: "center", fontFamily: DISPLAY, fontWeight: 800, fontSize: 21, color }}>{ch}</span>
    );
    const bits = rippleAdd(ripple.a, ripple.b).bits;
    const aBin = ripple.a.toString(2).padStart(2, "0").split("");
    const bBin = ripple.b.toString(2).padStart(2, "0").split("");
    const colPanel = (label, rows, sumRow) => (
      <div style={{ background: theme.bg, borderRadius: 14, padding: "8px 14px 10px", textAlign: "center" }}>
        <div style={{ fontFamily: BODY, fontSize: 12, fontWeight: 700, color: theme.accent2, marginBottom: 2 }}>{label}</div>
        {rows.map((r, i) => <div key={i}>{r}</div>)}
        <div style={{ borderTop: `2.5px solid ${theme.soft}88`, margin: "2px 0" }} />
        <div>{sumRow}</div>
      </div>
    );
    return (
      <div>
        <Title>{SCREENS[19].title}</Title>
        <div style={{ textAlign: "center", marginBottom: 4 }}>
          <span style={{ display: "inline-block", fontFamily: DISPLAY, fontWeight: 800, fontSize: 22, color: theme.key === "adder" ? "#08121f" : "#fff", background: theme.accent, borderRadius: 999, padding: "6px 20px", boxShadow: `0 4px 0 ${theme.edge}` }}>🎯 Make {target}</span>
        </div>
        <RippleCircuit a={ripple.a} b={ripple.b} theme={theme} onToggleBit={toggleBit} />
        <div style={{ display: "flex", gap: 12, justifyContent: "center", alignItems: "flex-start", marginTop: 10 }}>
          {colPanel("base ten",
            [<><Cell ch="" /><Cell ch={String(ripple.a)} color={theme.ink} /></>,
             <><Cell ch="+" color={theme.soft} /><Cell ch={String(ripple.b)} color={theme.ink} /></>],
            <><Cell ch="" /><Cell ch={solved ? String(ripple.a + ripple.b) : "?"} color={solved ? theme.accent : theme.soft} /></>)}
          {colPanel("binary",
            [<><Cell ch="" w={18} /><Cell ch={aBin[0]} w={18} color={theme.ink} /><Cell ch={aBin[1]} w={18} color={theme.ink} /></>,
             <><Cell ch="+" w={18} color={theme.soft} /><Cell ch={bBin[0]} w={18} color={theme.ink} /><Cell ch={bBin[1]} w={18} color={theme.ink} /></>],
            <><Cell ch={bits[0] ? "1" : ""} w={18} color={theme.accent} /><Cell ch={String(bits[1])} w={18} color={theme.accent} /><Cell ch={String(bits[2])} w={18} color={theme.accent} /></>)}
        </div>
        <div style={{ textAlign: "center", marginTop: 10, minHeight: 62 }}>
          {solved
            ? <div>
                <div style={{ fontSize: 34, animation: reduced ? "none" : "pop .5s ease" }}>🎉</div>
                <div style={{ marginTop: 6 }}><NavBtn theme={theme} primary onClick={another}>Another →</NavBtn></div>
              </div>
            : <>
                <NavBtn theme={theme} primary onClick={check}>Check ✓</NavBtn>
                {ripple.result === "no" && <div style={{ fontSize: 30, marginTop: 6 }}>🔁</div>}
              </>}
        </div>
      </div>
    );
  }

  // ----- carry place-value lesson + full adder quiz -----
  function CarryLessonStep() {
    const rows = [0, 1, 2, 3];
    const cell = { fontFamily: DISPLAY, fontWeight: 800, fontSize: 17, textAlign: "center" };
    return (
      <div>
        <Title>{SCREENS[17].title}</Title>
        <div style={{ maxWidth: 330, margin: "10px auto 0" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr 1fr 1fr", gap: 4, alignItems: "center", paddingBottom: 4, borderBottom: `2px solid ${theme.soft}44` }}>
            <span style={{ ...cell, fontSize: 13, color: theme.soft }}>A + B + Cin</span>
            <span style={{ ...cell, fontSize: 13, color: theme.accent2 }}>twos place<br />Cout</span>
            <span style={{ ...cell, fontSize: 13, color: theme.accent2 }}>ones place<br />S</span>
            <span style={{ ...cell, fontSize: 13, color: theme.soft }}>base 10</span>
          </div>
          {rows.map((t) => (
            <div key={t} style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr 1fr 1fr", gap: 4, alignItems: "center", padding: "7px 0", borderBottom: `1px solid ${theme.soft}22`, background: t >= 2 ? theme.accent + "14" : "transparent", borderRadius: 8 }}>
            <span style={{ ...cell, color: theme.ink, fontSize: 15 }}>adds up to {t}</span>
              <span style={cell}><BitChip v={t >> 1} theme={theme} size={22} /></span>
              <span style={cell}><BitChip v={t & 1} theme={theme} size={22} /></span>
              <span style={{ ...cell, color: theme.accent }}>= {t}</span>
            </div>
          ))}
        </div>
        <Caption>{SCREENS[17].caption}</Caption>
      </div>
    );
  }
  function FullAdderQuizStep() {
    const rounds = FULL_ADDER_QUIZ_ROUNDS;
    const [a, b, cin] = rounds[Math.min(faq.round, rounds.length - 1)];
    const { sum, cout } = fullAdd(a, b, cin);
    const total = a + b + cin;
    const cycle = (v) => (v === null ? 1 : v === 1 ? 0 : 1);
    const setGuess = (i) => {
      if (faq.revealed) return;
      const guess = faq.guess.slice(); guess[i] = cycle(guess[i]);
      setFaq({ ...faq, guess });
    };
    const check = () => {
      const ok = faq.guess[0] === sum && faq.guess[1] === cout;
      logQuizAttempt("full-adder", faq.round, faPrompt([a, b, cin]), `s=${faq.guess[0]},c=${faq.guess[1]}`, ok, 18);
      if (ok) { setFaq({ ...faq, revealed: true }); speak(fullAddLine(a, b, cin)); }
      else speak(QUIZ_LINES.tryAgain);
    };
    const next = () => {
      if (faq.round + 1 >= rounds.length) { setFaq({ ...faq, finished: true }); speak(QUIZ_LINES.quizDone); }
      else {
        const nextRound = faq.round + 1;
        setFaq({ round: nextRound, guess: [null, null], revealed: false, finished: false });
        logQuizRound("full-adder", nextRound, faPrompt(rounds[nextRound]), 18);
      }
    };
    if (faq.finished) {
      return (
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 56, animation: reduced ? "none" : "pop .5s ease" }}>🏆</div>
          <Title>{SCREENS[18].titleQuizDone}</Title>
          <Stars n={rounds.length} total={rounds.length} theme={theme} />
          <NavBtn theme={theme} onClick={() => { setFaq({ round: 0, guess: [null, null], revealed: false, finished: false }); logQuizRound("full-adder", 0, faPrompt(rounds[0]), 18); }}>Play again</NavBtn>
        </div>
      );
    }
    return (
      <div>
        <Title>{SCREENS[18].title}</Title>
        <Stars n={faq.round + (faq.revealed ? 1 : 0)} total={rounds.length} theme={theme} />
        <FullAdderBoxCircuit a={a} b={b} cin={cin} theme={theme} revealed={faq.revealed}
          guessS={faq.guess[0]} guessC={faq.guess[1]} onGuessS={() => setGuess(0)} onGuessC={() => setGuess(1)} />
        <div style={{ marginTop: 10, minHeight: 60, textAlign: "center" }}>
          {faq.revealed
            ? <>
                <div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 22, color: theme.ink }}>
                  {a} + {b} + {cin} = <BitChip v={cout} theme={theme} /> <BitChip v={sum} theme={theme} />
                  <span style={{ color: theme.accent, marginLeft: 8 }}>= {total}</span>
                  <span style={{ color: theme.soft, fontSize: 15, marginLeft: 6 }}>(base 10)</span> ✅
                </div>
                <div style={{ marginTop: 10 }}><NavBtn theme={theme} primary onClick={next}>{faq.round + 1 >= rounds.length ? "Finish 🏆" : "Next →"}</NavBtn></div>
              </>
            : <>
                <Caption>{SCREENS[18].caption}</Caption>
                <div style={{ marginTop: 8 }}><NavBtn theme={theme} primary onClick={check} disabled={faq.guess[0] === null || faq.guess[1] === null}>Check ✓</NavBtn></div>
              </>}
        </div>
      </div>
    );
  }

  function FamilyStep() {
    const family = ["NOT", "OR", "AND", "XOR", "NAND"];
    return (
      <div>
        <Title>{SCREENS[13].title}</Title>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {family.map((g) => (
            <div key={g} style={{ background: theme.bg, borderRadius: 16, padding: "10px 8px", textAlign: "center" }}>
              <svg viewBox="-4 -2 100 68" width="86" style={{ display: "block", margin: "0 auto" }}><GateG x={0} y={0} type={g} theme={theme} /></svg>
              <div style={{ fontFamily: BODY, fontSize: 11.5, color: theme.soft, marginTop: 4, lineHeight: 1.5 }}>
                {gateCombos(g).map((c) => (
                  <div key={comboKey(c)}>
                    <span style={{ fontFamily: DISPLAY, fontWeight: 800 }}>{c.join(" ")}</span>
                    <span> → </span>
                    <span style={{ fontFamily: DISPLAY, fontWeight: 800, color: gateOutput(g, c) ? theme.accent : theme.soft }}>{gateOutput(g, c)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
          <div style={{ background: theme.bg, borderRadius: 16, padding: "10px 8px", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 6 }}>
            <div style={{ fontSize: 34 }}>🤖</div>
            <div style={{ fontFamily: BODY, fontSize: 12, color: theme.soft, lineHeight: 1.4 }}>{SCREENS[13].footer}</div>
          </div>
        </div>
      </div>
    );
  }

  function FinaleStep() {
    const journey = [["💡", "Switch"], ["🚦", "Gates"], ["🧮", "Half adder"], ["🤖", "Full adder"], ["➕", "Binary addition"]];
    return (
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 52, animation: reduced ? "none" : "pop .5s ease" }}>🎉</div>
        <Title>{SCREENS[20].title}</Title>
        <div style={{ display: "flex", gap: 6, justifyContent: "center", flexWrap: "wrap", alignItems: "center", margin: "12px 0" }}>
          {journey.map(([icon, label], i) => (
            <React.Fragment key={label}>
              {i > 0 && <span style={{ color: theme.soft, fontSize: 16 }}>→</span>}
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6, background: theme.bg, borderRadius: 999, padding: "7px 13px", fontFamily: DISPLAY, fontWeight: 800, fontSize: 14, color: theme.ink }}>
                <span style={{ fontSize: 18 }}>{icon}</span>{label}
              </span>
            </React.Fragment>
          ))}
        </div>
        <Caption>{SCREENS[20].footer}</Caption>
        <div style={{ marginTop: 16 }}>
          <NavBtn theme={theme} onClick={() => {
            setStep(0); setKnife0(false); setKnife1(false); setCombineRevealed(false); setExplore({}); setQuiz({});
            setMystery({ round: 0, inputs: [0, 0], solved: false, solvedCount: 0 });
            setHalf({ inputs: [0, 0], seenBoth: false, revealed: false });
            setHaq({ round: 0, guess: [null, null], revealed: false, finished: false });
            setFaq({ round: 0, guess: [null, null], revealed: false, finished: false });
            setFa([0, 0, 0]); setRipple({ targetIdx: 0, a: 0, b: 0, result: null, wins: 0 });
            logEvent("start-over", { step: 20 }); flushTelemetry();
            spokenStep.current = -1; setTimeout(() => speak(SPEAK[0]), 60);
          }}>Start over</NavBtn>
        </div>
      </div>
    );
  }

  // Step renderers are called as plain functions (not JSX components) so the
  // element tree keeps stable identity across renders and CSS transitions run.
  function content() {
    if (GATE_STEPS[step]) return GateExploreStep({ stepIdx: step, gate: GATE_STEPS[step] });
    if (QUIZ_STEPS[step]) return PredictQuizStep({ stepIdx: step, gate: QUIZ_STEPS[step] });
    switch (step) {
      case 0:
        return (
          <div>
            <Title>{SCREENS[0].title}</Title>
            <KnifeSwitchCircuit mode="no" down={knife0} onToggle={() => { const d = !knife0; setKnife0(d); logEvent("toggle", { step: 0, target: "knife-switch", detail: { down: d, lit: d } }); speak(d ? REVEAL_LINES.switchOn : REVEAL_LINES.switchOff); }} theme={theme} />
            <Caption>{SCREENS[0].caption}</Caption>
          </div>
        );
      case 1:
        return (
          <div>
            <Title>{SCREENS[1].title}</Title>
            <KnifeSwitchCircuit mode="nc" down={knife1} onToggle={() => { const d = !knife1; setKnife1(d); logEvent("toggle", { step: 1, target: "knife-switch-nc", detail: { down: d, lit: !d } }); speak(d ? REVEAL_LINES.ncDown : REVEAL_LINES.ncUp); }} theme={theme} />
            <Caption>{SCREENS[1].caption}</Caption>
          </div>
        );
      case 4:
        return (
          <div>
            <Title>{SCREENS[4].title}</Title>
            {!combineRevealed
              ? <div style={{ textAlign: "center", margin: "20px 0 8px" }}><QMark theme={theme} onClick={() => { setCombineRevealed(true); logEvent("reveal", { step: 4, target: "combine", detail: { item: "two-switch-wirings" } }); speak(REVEAL_LINES.combine); }} /></div>
              : <div style={{ animation: reduced ? "none" : "pop .5s ease" }}>
                  <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap", marginTop: 10 }}>
                    <div style={{ background: theme.bg, borderRadius: 16, padding: "10px 12px", textAlign: "center" }}>
                      <svg viewBox="0 0 150 56" width="170" style={{ display: "block" }}>
                        <path d="M8,40 H34 M62,40 H88 M116,40 H130" fill="none" stroke={theme.soft} strokeWidth="3.5" strokeLinecap="round" />
                        <path d="M34,40 L58,28 M88,40 L112,28" fill="none" stroke={theme.ink} strokeWidth="3.5" strokeLinecap="round" />
                        <circle cx="34" cy="40" r="3.5" fill={theme.ink} /><circle cx="62" cy="40" r="3.5" fill={theme.ink} />
                        <circle cx="88" cy="40" r="3.5" fill={theme.ink} /><circle cx="116" cy="40" r="3.5" fill={theme.ink} />
                        <circle cx="138" cy="40" r="8" fill="#FFE066" stroke="#E0A800" strokeWidth="2" />
                      </svg>
                      <div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 15, color: theme.ink, marginTop: 6 }}>in a row</div>
                      <div style={{ fontFamily: BODY, fontSize: 12.5, color: theme.soft }}>you need both</div>
                    </div>
                    <div style={{ background: theme.bg, borderRadius: 16, padding: "10px 12px", textAlign: "center" }}>
                      <svg viewBox="0 0 150 62" width="170" style={{ display: "block" }}>
                        <path d="M8,32 H24 M24,32 V14 H44 M24,32 V50 H44 M70,14 H104 M70,50 H104 M104,14 V50 M104,32 H122" fill="none" stroke={theme.soft} strokeWidth="3.5" strokeLinecap="round" />
                        <path d="M44,14 L66,4 M44,50 L66,40" fill="none" stroke={theme.ink} strokeWidth="3.5" strokeLinecap="round" />
                        <circle cx="44" cy="14" r="3.5" fill={theme.ink} /><circle cx="70" cy="14" r="3.5" fill={theme.ink} />
                        <circle cx="44" cy="50" r="3.5" fill={theme.ink} /><circle cx="70" cy="50" r="3.5" fill={theme.ink} />
                        <circle cx="132" cy="32" r="8" fill="#FFE066" stroke="#E0A800" strokeWidth="2" />
                      </svg>
                      <div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 15, color: theme.ink, marginTop: 6 }}>side by side</div>
                      <div style={{ fontFamily: BODY, fontSize: 12.5, color: theme.soft }}>one is enough</div>
                    </div>
                  </div>
                  <div style={{ textAlign: "center", fontFamily: DISPLAY, fontWeight: 800, fontSize: 19, color: theme.accent, marginTop: 12 }}>{SCREENS[4].banner}</div>
                </div>}
          </div>
        );
      case 12:
        return MysteryStep();
      case 13:
        return FamilyStep();
      case 14:
        return HalfAdderStep();
      case 15:
        return HalfAdderQuizStep();
      case 16:
        return FullAdderStep();
      case 17:
        return CarryLessonStep();
      case 18:
        return FullAdderQuizStep();
      case 19:
        return RippleStep();
      case 20:
        return FinaleStep();
      default:
        return null;
    }
  }

  if (!started) {
    return (
      <div style={{ minHeight: "100vh", background: THEMES.switch.bg, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: BODY, padding: 20 }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 56 }}>💡 🚦 🧮 🤖</div>
          <div style={{ fontFamily: DISPLAY, fontWeight: 800, fontSize: 26, color: THEMES.switch.ink, margin: "10px 0 22px" }}>Logic Gates</div>
          <button onClick={startApplet} aria-label="start" style={{ width: 128, height: 128, borderRadius: 64, border: "none", background: THEMES.switch.accent, color: "#fff", fontSize: 56, cursor: "pointer", boxShadow: `0 6px 0 ${THEMES.switch.edge}`, touchAction: "manipulation" }}>▶</button>
          <div style={{ fontFamily: BODY, fontSize: 15, color: THEMES.switch.soft, marginTop: 16 }}>🔊 Turn the volume up</div>
        </div>
      </div>
    );
  }

  return (
    <div ref={appletRootRef} data-telemetry-step={step} style={{ minHeight: "100vh", background: theme.bg, transition: "background .5s ease", fontFamily: BODY, padding: "16px 14px 34px" }}>
      <style>{`
        @keyframes pop { 0%{ transform: scale(.3); opacity:0 } 60%{ transform: scale(1.15) } 100%{ transform: scale(1); opacity:1 } }
        @keyframes pulse { 0%,100%{ transform: scale(1) } 50%{ transform: scale(1.07) } }
        button:focus-visible { outline: 3px solid ${theme.accent2}; outline-offset: 3px; }
        button:active:not(:disabled) { transform: translateY(2px); }
        svg [role="button"]:focus { outline: none; }
        g[role="button"]:focus-visible rect:first-of-type { stroke: ${theme.accent2}; }
        rect[role="button"]:focus-visible { stroke: ${theme.accent2}; stroke-width: 2.5; }
        @media (prefers-reduced-motion: reduce){ *{ animation-duration:.001ms !important; transition-duration:.001ms !important } }
      `}</style>
      <div style={{ maxWidth: 540, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <button onClick={() => speak(SPEAK[step])} aria-label="repeat the instructions" title="Repeat the instructions" style={{ width: 44, height: 44, borderRadius: 22, border: `2px solid ${theme.soft}55`, background: theme.panel, fontSize: 19, cursor: "pointer", touchAction: "manipulation", display: "flex", alignItems: "center", justifyContent: "center" }}>💬</button>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            {["switch", "gates", "combine", "adder"].map((k) => (
              <span key={k} style={{ fontSize: 24, opacity: theme.key === k ? 1 : 0.35, transform: theme.key === k ? "scale(1.1)" : "none", transition: "all .3s ease" }}>{THEMES[k].icon}</span>
            ))}
          </div>
          <button onClick={toggleMute} aria-label={muted ? "turn sound on" : "turn sound off"} aria-pressed={muted} title={muted ? "Sound off — tap to unmute" : "Sound on — tap to mute"} style={{ width: 44, height: 44, borderRadius: 22, border: `2px solid ${theme.soft}55`, background: theme.panel, fontSize: 19, cursor: "pointer", touchAction: "manipulation", display: "flex", alignItems: "center", justifyContent: "center", opacity: muted ? 0.6 : 1 }}>{muted ? "🔇" : "🔊"}</button>
        </div>
        <div style={{ background: theme.panel, borderRadius: 26, padding: "18px 16px", boxShadow: "0 12px 34px rgba(0,0,0,.14)", minHeight: 380, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          {content()}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14 }}>
          <NavBtn theme={theme} onClick={() => go(step - 1)} disabled={step === 0}>←</NavBtn>
          <div style={{ display: "flex", gap: 1 }}>
            {PHASES.map((_, i) => (
              <button key={i} onClick={() => go(i)} aria-label={`go to step ${i + 1} of ${PHASES.length}`} aria-current={i === step ? "step" : undefined} style={{ width: 16, height: 26, padding: 0, border: "none", background: "transparent", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", touchAction: "manipulation" }}>
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
