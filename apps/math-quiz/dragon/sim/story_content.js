// Story content for the dragon fluency game. Pure data — the selection logic
// lives in story.js so both the browser game and the Node tests/sim consume the
// same beats. Text may contain {name}, replaced with the dragon's name (or a
// fallback before naming). Aimed at an eight-year-old: cozy, funny, encouraging.
//
// The arc: a storm separated Mama Dragon from her egg. The child feeds the egg
// with math (numbers are dragon food), hatches and names the baby, then helps it
// grow strong enough for the long way home to Mount Ember — visiting Story
// Stones that old dragons left along the route. The 100% reward (flying + the
// ride) is foreshadowed but never named.
export const STORY_PHASES = [
  {
    id: 'egg',
    title: 'The Egg in the Nest',
    beats: [
      { id: 'egg-letter-1', title: 'A Tiny Letter', text: 'Tucked in the straw under the egg is a tiny rolled-up letter. It says: "To the kind one who found my egg — the storm winds carried me far, far away. Please keep my little one warm, and feed it the best dragon food there is: NUMBERS. Every problem you solve makes my baby stronger. — Mama Dragon"' },
      { id: 'egg-hum', title: 'The Egg Hums', text: 'When you answer math problems, the egg hums a tiny song, like a kettle that learned to purr. Dragons dream in numbers, you know.' },
      { id: 'egg-scale', title: 'A Purple Sparkle', text: 'You spot something shiny in the straw — a little dragon scale, purple as a plum! So THAT is what color your dragon will be.' },
      { id: 'egg-letter-2', title: 'Mama’s Second Letter', text: 'Another letter, buried deeper in the straw: "My baby can hear you now! When you practice, count brave and loud. My favorite number is 7 — count the stripes on my baby’s tail one day. — Mama D."' },
      { id: 'egg-taps', title: 'Tap. Tap-tap.', text: 'You press your ear against the warm shell. TAP. Tap-tap. It taps when you get answers right — it is counting WITH you!' },
      { id: 'egg-dreams', title: 'Dragon Dreams', text: 'Tonight the egg glows softly, like a night-light. Baby dragons dream about flying before they ever open their eyes.' },
      { id: 'egg-letter-3', title: 'The Mountain Letter', text: '"Far past the meadow and the hills, dragons live on Mount Ember — you can see it smoking, way out there. One day my baby must find the way home. But first: grow STRONG. — Mama D."' },
      { id: 'egg-almost', title: 'It’s Almost Time', text: 'The egg wobbles and rocks and taps like a little drum. Whatever is inside is done waiting. Keep practicing — your next quizzes might be the ones!' },
    ],
    extras: [
      { id: 'egg-x-toast', title: 'Warm as Toast', text: 'The egg is warm as fresh toast today. You are doing a good job.' },
      { id: 'egg-x-bird', title: 'A Visitor', text: 'A little bird landed on the nest to keep the egg company. It chirped 3 times, then 4 more. That’s 7! Mama Dragon’s favorite.' },
      { id: 'egg-x-snore', title: 'The Tiniest Snore', text: 'You hear the tiniest snore in the world. The egg is napping. Even eggs need rest days.' },
      { id: 'egg-x-bigger', title: 'Growing?', text: 'Is it your imagination, or is the egg a little bigger than yesterday? You measure it with your hands. Definitely bigger.' },
      { id: 'egg-x-butterfly', title: 'Big Smooth Flower', text: 'Butterflies keep landing on the egg. They think it is a big smooth flower. The egg does not seem to mind.' },
    ],
  },
  {
    id: 'hatchling',
    title: 'The Hatchling',
    beats: [
      { id: 'hatch-name', kind: 'name', title: 'A Name!', text: 'The little dragon blinks up at you with big golden eyes and sneezes a tiny puff of glitter. It needs a name! What will you call it?' },
      { id: 'hatch-steps', title: 'First Steps', text: '{name} takes wobbly first steps… then trips over its own tail. It looks around, embarrassed. You pretend not to notice. {name} appreciates that.' },
      { id: 'hatch-letter-4', title: 'Mama Is Proud', text: 'A new letter drifts down from the sky: "You hatched my baby! I was so happy I did three loop-the-loops. Take {name} exploring — but remember, strong wings come from a strong mind. Keep practicing! — Mama D."' },
      { id: 'hatch-shadow', title: 'The Shadow', text: '{name} saw its own shadow and hid behind your legs. Then it growled at the shadow. The shadow did not growl back. {name} feels very brave now.' },
      { id: 'hatch-roar', title: 'The First Roar', text: '{name} stands very still, staring at Mount Ember far away… and lets out its first roar. It sounds like a squeaky toy. It’s a start.' },
      { id: 'hatch-tail', title: 'Seven Stripes', text: 'You count the stripes on {name}’s tail: one, two, three, four, five, six… SEVEN. Just like Mama Dragon said. {name} wags all seven at once.' },
    ],
    extras: [
      { id: 'hatch-x-nap', title: 'Nap Attack', text: '{name} fell asleep mid-zoomie, face-first in the straw. Baby dragons use a LOT of energy being adorable.' },
      { id: 'hatch-x-copy', title: 'Copycat', text: 'Everything you do, {name} does too. You hop. {name} hops. You wiggle. {name} wiggles. This could go on all day.' },
      { id: 'hatch-x-stick', title: 'The Best Stick', text: '{name} found a stick and has decided it is the best stick in the world. It sleeps next to the stick now.' },
      { id: 'hatch-x-sneeze', title: 'Glitter Sneeze', text: '{name} sneezed and three sparkles came out. One day those sparkles might be something much warmer…' },
    ],
  },
  {
    id: 'meadow',
    title: 'The Butterfly Meadow',
    beats: [
      { id: 'meadow-wings', title: 'Real Wings', text: '{name}’s new wings shimmer in the sun like stained glass. Too small to fly with — but PERFECT for extra-fast zoomies.' },
      { id: 'meadow-trail', title: 'The Sparkle Trail', text: 'A trail of sparkles appeared in the grass, leading east! Mama’s letter said dragons rested in the Butterfly Meadow on their way home. Walk the trail with {name} and find the Story Stone.' },
      { id: 'meadow-chase', title: 'The Butterfly Game', text: '{name} chased twelve butterflies and caught exactly zero. The butterflies think this is the best game ever invented. They come back every morning now.' },
      { id: 'meadow-letter-5', title: 'The Long Road Home', text: '"The meadow, then the hills, then the grove with the old beacon — that is the dragon road to Mount Ember. My baby’s wings will be ready when your practice is perfect. — Mama D."' },
    ],
    extras: [
      { id: 'meadow-x-flowercrown', title: 'Flower Crown', text: 'You make a flower crown. {name} wears it like royalty for one whole minute, then eats it. It was a delicious crown.' },
      { id: 'meadow-x-race', title: 'Zoomie Race', text: 'You race {name} across the meadow. {name} wins by using its wings to cheat. You both agree it still counts.' },
      { id: 'meadow-x-cloudwatch', title: 'Cloud Shapes', text: 'You and {name} watch clouds. You see a bunny. {name} sees a giant dragon. Everything looks like a giant dragon to {name}.' },
    ],
  },
  {
    id: 'hills',
    title: 'The Whispering Hills',
    beats: [
      { id: 'hills-jump', title: 'Boing!', text: '{name} discovered jumping and is now approximately 60% kangaroo. Every jump gets a little higher. Those wings are doing something…' },
      { id: 'hills-trail', title: 'Up the Hills', text: 'The sparkle trail climbs south, up the Whispering Hills! Hop the stepping stones with {name} and find the next Story Stone at the top.' },
      { id: 'hills-view', title: 'Halfway Home', text: 'From the hilltop you can see Mount Ember’s smoke curling into the sky. {name} stares for a long, quiet moment. Then it jumps three times, as if to say: getting closer.' },
      { id: 'hills-letter-6', title: 'Mama Sees You', text: '"Some nights I fly to a high cloud and look for the little light of your campfire. I can see how strong you two are getting. Almost there, brave ones. — Mama D."' },
    ],
    extras: [
      { id: 'hills-x-echo', title: 'Echo!', text: '{name} roars at the hills and the hills roar back. {name} is now convinced there is a hill dragon. You do not correct {name}.' },
      { id: 'hills-x-rock', title: 'Pet Rock', text: '{name} tried to hatch a round rock by sitting on it very patiently. The rock is not an egg. But it IS a very loved rock now.' },
      { id: 'hills-x-stars', title: 'Counting Stars', text: 'You and {name} count stars from the hilltop until you both lose count and start over. Losing count is half the fun.' },
    ],
  },
  {
    id: 'grove',
    title: 'The Firefly Grove',
    beats: [
      { id: 'grove-fire', title: 'A Real Flame!', text: '{name} hiccupped and a REAL flame came out — small and warm, like a birthday candle. {name} is extremely proud and keeps looking at you to make sure you saw.' },
      { id: 'grove-trail', title: 'Into the Grove', text: 'The sparkle trail winds west into the Firefly Grove, where the moon pool glows. There is an old stone beacon there that has been cold for a hundred years. Bring {name} — and {name}’s new flame.' },
      { id: 'grove-beacon', title: 'The Beacon', text: 'The old beacon is covered in carvings of flying dragons. Legend says: when a young dragon lights it, the mountain answers. {name}’s flame is almost strong enough. Almost.' },
      { id: 'grove-letter-7', title: 'The Last Letter?', text: '"When the beacon burns, every dragon on Mount Ember will see it. Practice until your very best — something wonderful is waiting at the end, my dears. I promise. — Mama D."' },
    ],
    extras: [
      { id: 'grove-x-fireflies', title: 'Tiny Lanterns', text: 'The fireflies fly in circles around {name}, like tiny floating lanterns. {name} tries to be a firefly too. {name} is too big to be a firefly.' },
      { id: 'grove-x-marshmallow', title: 'Toasted Perfect', text: 'You hold a marshmallow on a stick and {name} toasts it perfectly golden on the first try. A dragon of many talents.' },
      { id: 'grove-x-moonpool', title: 'The Moon Pool', text: 'In the moon pool’s still water, {name} sees its reflection — and for a second, it looks big. Grown. Ready. Then it splashes the reflection and giggles.' },
    ],
  },
  {
    id: 'summit',
    title: 'The Sky',
    beats: [
      { id: 'summit-beacon-lit', title: 'The Beacon Burns!', text: '{name} takes the deepest breath a little dragon has ever taken… and the old beacon ROARS to life! The flame leaps toward the sky. Far, far away, on Mount Ember… a light glows back.' },
      { id: 'summit-answer', title: 'Someone Saw', text: 'The mountain answered. Someone is waiting there. {name} spreads its wings wide — wider than ever before — and looks back at you with those big golden eyes. {name} does not want to go alone.' },
    ],
    extras: [
      { id: 'summit-x-together', title: 'Sky Friends', text: 'The world looks tiny from up high — the nest, the meadow, the hills, the grove. You and {name} did all of that, one quiz at a time.' },
      { id: 'summit-x-home', title: 'The Way Home', text: 'Mount Ember glows warm on the horizon. Whenever you are ready, {name} knows the way. Mama is watching for two little lights in the sky.' },
    ],
  },
];
// Post-quiz reaction lines, picked by performance tier. {score} = "17 of 20".
export const QUIZ_REACTIONS = {
  perfect: [
    'PERFECT! {score}! The whole forest heard you cheering. (It was {name} cheering.)',
    'Every single one right — {score}! {name} is doing a happy dance with all four feet.',
    '{score} — flawless! Somewhere far away, Mama Dragon just did a loop-the-loop.',
    'A perfect {score}! The Story Stones will sing about this one.',
  ],
  great: [
    '{score} — amazing work! {name} puffs out its chest, extremely impressed.',
    'Wow, {score}! The egg-warm feeling in your chest? That’s called being GOOD at this.',
    '{score}! Strong mind, strong wings — that’s how the dragon road gets shorter.',
  ],
  good: [
    '{score} — solid practice! Every answer is one more scale of armor for {name}.',
    'You got {score}. Keep feeding those numbers — dragons grow on practice, not on perfect.',
    '{score}! The tricky ones today become the easy ones tomorrow. Dragon rule.',
  ],
  tough: [
    'That was a tough batch — but you stayed and finished it, and THAT is what dragon keepers do. {name} noticed.',
    'Some quizzes bite back. You showed up anyway — {score}. Mama Dragon calls that brave.',
    'Phew — a tricky one! Rest a moment. The nest is warm and tomorrow’s numbers will be softer.',
  ],
};
// Story Stones on the dragon road — played when the child walks the sparkle
// trail to the stone and clicks it (world/journey.js), not at burst end.
export const STONE_BEATS = {
  meadow: { id: 'stone-meadow', title: 'The Meadow Stone', text: 'The Story Stone hums as {name} sniffs it: "Dragons rested in this meadow on their long flights home to Mount Ember. The butterflies still remember them." The butterflies land all over {name}, as if to say: we will remember you, too.' },
  hills: { id: 'stone-hills', title: 'The Hilltop Stone', text: 'The hilltop Stone whispers: "Halfway home is halfway grown." From up here, Mount Ember looks closer than it ever has. {name} puffs out its chest at the mountain, very seriously.' },
  grove: { id: 'stone-grove', title: 'The Beacon Stone', text: 'The Stone beside the old beacon glows: "When a young dragon’s flame burns true, light me — and the mountain will see you." {name} looks at the beacon… then at you. Not yet. But soon.' },
};
// Fallback before the dragon is named (and during the egg phase).
export const UNNAMED = 'your dragon';
