file: copy/logic-gates.md
title: Logic Gates — screen copy

Edit this file, then run:

```bash
cd apps/focusonfoundations/web
npm run sync:copy
```

Each `## Screen N` section matches dot **N** along the bottom (screen 1 = first dot). **speak** is the narration when you land on that screen. **title** and **caption** are the on-screen text. Use `{gate}` in title/caption where the gate name is inserted (NOT, OR, AND, XOR, NAND).


## Screen 1

title: A switch and a light
caption: Power comes from the wall. Pull the switch down to close the circuit. Off is 0. On is 1.
speak: This is power from the wall, a switch, and a light. Tap the switch to close the circuit!
reveal-switchOn: One! The light is on.
reveal-switchOff: Zero. The light is off.

## Screen 2

title: Wired the other way
caption: Same switch, opposite wiring: resting up it's connected. Flip it down and the connection breaks.
speak: This switch is wired the other way. Resting up, the light is on. Tap it, and it breaks the connection!
reveal-ncUp: Up! The circuit is closed. The light is on.
reveal-ncDown: Flipped down! The connection is broken. The light is off.

## Screen 3

title: The {gate} gate
speak: Meet the NOT gate. It flips the signal. Try the switch both ways.
table-done: You tried both! In zero, out one. In one, out zero. NOT flips it.

## Screen 4

title-quiz: {gate} quiz · will the light be on?
title-quiz-done: You know {gate}!
title-quiz-done-not: You got it!
speak: Quiz time! Look at the switch. Will the light be on or off? Tap your answer.

## Screen 5

title: What if we have two switches?
speak: What if we have two switches? How could we combine them? Tap the question mark.
reveal-combine: Side by side, one switch is enough. In a row, you need both. Two switches make new rules!
banner: Each wiring makes a new rule. Let's explore them!

## Screen 6

title: The {gate} gate
caption-OR: OR is like two switches side by side — either path lights the light.
speak: This is the OR gate. Two switches now! The light turns on if A or B is on. Try all four ways.
table-done: All four tried! OR lights up when at least one switch is on.

## Screen 7

title-quiz: {gate} quiz · will the light be on?
title-quiz-done: You know {gate}!
title-quiz-done-not: You got it!
speak: Quiz! Think like an OR gate. Will the light be on or off?

## Screen 8

title: The {gate} gate
caption-AND: AND is like two switches in a row — the signal needs both.
speak: The AND gate lights up only when A and B are both on. Try all four ways.
table-done: All four! AND needs both switches on. No teamwork, no light.

## Screen 9

title-quiz: {gate} quiz · will the light be on?
title-quiz-done: You know {gate}!
title-quiz-done-not: You got it!
speak: Quiz! Think like an AND gate. Will the light be on or off?

## Screen 10

title: The {gate} gate
caption: Exclusive or: one switch or the other, but not both.
speak: The ex-or gate means exclusive or. One input or the other — but not both! Try all four ways.
table-done: All four tried! One on or the other on, but not both. That's exclusive or.

## Screen 11

title-quiz: {gate} quiz · will the light be on?
title-quiz-done: You know {gate}!
title-quiz-done-not: You got it!
speak: Quiz! Think like an ex-or gate. Will the light be on or off?

## Screen 12

title: The {gate} gate
caption-NAND: NAND = AND + NOT. The little bubble flips the answer.
speak: The NAND gate is an AND gate followed by a NOT. The little bubble means flip. Try all four ways.
table-done: All four! NAND is the opposite of AND. And NAND is universal: you can build every other gate from just NAND. Some entire computers are made only of NAND gates!

## Screen 13

title: Mystery gate · which one is it?
speak: Mystery gate! Flip the switches, watch the light, and guess which gate is hiding inside.

## Screen 14

title: The gate family
footer: Enough little gates and you can build a computer that adds anything!
speak: Here is the whole gate family, side by side. You know them all! Now let's put them to work.

## Screen 15

title: Two gates, same switches
caption: Try all the switch combinations. Watch both lights.
caption-bothOn: Both on… XOR went dark but AND lit up. What did you build?
caption-revealed: You built a half adder: XOR makes the ones digit, AND makes the carry.
speak: Now let's wire two gates to the same switches. Ex-or and AND, side by side. Turn both switches on and watch closely.
reveal-halfAdder: Surprise! You built an adding machine. The ex-or light is the ones digit. The AND light is the carry. One plus one is one zero. Two, in binary!

## Screen 16

title: Predict both lights
caption: Tap each bulb to set your guess, then check.
title-quiz-done: You can add in binary!
speak: Adding practice! Read the switches, then predict both lights. Tap the bulbs to set your guess, then check.

## Screen 17

title: The full adder
caption: Two half adders and an OR gate. It can even carry!
speak: The full adder! It adds three signals: A, B, and a carry in. Two half adders and an OR gate, all working together. Try it!

## Screen 18

title: Where does the carry go?
caption: The carry out is worth one step more — that's how two little lights can count to three.
speak: Look at the two answer lights. A, B, and the carry in all live in the ones place. The sum light stays in the ones place, but the carry out jumps up to the twos place. That is how two little lights can count all the way to three!

## Screen 19

title: Predict the sum and the carry
caption: Tap each bulb to set your guess, then check.
title-quiz-done: You mastered the full adder!
speak: Quiz! Read A, B, and the carry in. Then predict both lights: the sum, and the carry out. Tap the bulbs, then check.

## Screen 20

title: Full adders add big numbers
speak: Full adders can add big binary numbers! Each number has a ones place and a twos place, just like column addition. Flip the switches to make the target sum.

## Screen 21

title: You built a computer's heart!
footer: Billions of tiny switches, adding and deciding — that's all a computer is. And now you know how it works.
speak: You did it! From one little switch, to logic gates, to adders doing real binary addition. Real computers work just like this, with billions of tiny switches. You built the heart of a computer!


## Shared

quiz-correct: Yes! Correct!
quiz-tryAgain: Not yet. Try again.
quiz-done: You got them all! Amazing!
quiz-gotIt: You got it!


## Templates

mysteryCorrect: Yes! It is the {gateName} gate!
