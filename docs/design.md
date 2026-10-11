# CleanHour landing page: concept and directions

## Phase 1: Concept

**Core transformation:** *smog-choked morning → clean hour.* Today, PE and assembly sit in the
dirtiest hours of the day (8 AM PM2.5 ≈ 2× the 1 PM level in Delhi's smog season), and the only
policy tool is a blanket ban. CleanHour turns the same school day into one where every outdoor
period sits in the cleanest air, and nobody loses play. The hero shows this happening: PE tiles
caught in thick morning haze lift out of it and glide to the clear midday slots while the PM2.5
readout falls from 462 to 80 (measured at the CPCB Rohini station, 6 Nov 2025).

**Metaphor: the lifting sky.** This is the actual physics behind the product. On a smog morning a
cold inversion layer presses the pollution down onto the city. As the sun heats the ground, the
mixing layer *rises* and the smog dilutes. CleanHour is a bet on that rise. The metaphor is the
mechanism, so nothing in it is decoration.

**Visual language derived from it**
- *Shapes:* long soft horizontal bands (layers of air), a single hairline horizon (the school
  day as a timeline), small round particles. No hard boxes; cards are translucent "air panes".
- *Texture:* blur, grain-free gradients, light passing through haze.
- *Colour temperature:* warm and heavy at the top of the story (ember, dusty smog), cool and
  open as the air clears (sky, leaf green). The page itself "clears" as you scroll.
- *Type personality:* a calm, high-contrast editorial serif for authority and luxury, with a
  neutral grotesk for data (tabular figures), and a Devanagari serif so Hindi is first-class.

**Motion physics derived from it:** *buoyant.* Things rise from below and decelerate like warm
air (long `power3.out`), haze thins with opacity and drifts upward, particles disperse.
Nothing snaps, bounces or shakes. Smog doesn't bounce.

---

## Phase 2: Three directions

### A. "The Lifting Sky" (chosen)
- **Type:** Instrument Serif (display; editorial luxury, italic for the emotional word) +
  Inter (body/data; tabular numerals) + Noto Serif Devanagari (Hindi tagline).
- **Palette:** `--night #0b0d12` pre-dawn base · `--smog #2a1d1f` trapped air · `--ember #ff7a45`
  sun through smog / warning · `--haze #c9a27e` dust · `--sky #cfe9ff` clear midday ·
  `--leaf #8fe3b5` safe/clean · `--ivory #f4efe6` text. Warm → cool mirrors the air clearing.
- **Motion rules:** easing family `power3` (out for entrances, inOut for loops/scrubs).
  Timing: fast 0.35s (hover) / medium 0.9s (reveals) / slow 2.2s (haze). Character: **buoyant**.
- **Signature moment:** *Drag the sun.* A sun handle travels across the real school day; the haze
  ceiling lifts with the actual PM2.5 curve, and the Cedar rules re-decide PE, primary classes and
  asthma-watch kids live at that minute. Flip GRAP to Stage III and watch the rules override the sky.
- **Storyboard:**
  | Section | What moves | Trigger | What it shows |
  |---|---|---|---|
  | Hero | Headline lines rise out of a mask; haze lifts; PE tiles float from 8:05 to 1:05; PM2.5 counts 462→80; haze layers follow the cursor in depth | load, loop, cursor | The transformation itself |
  | Evidence marquee | Cited facts drift sideways; pauses on hover/offscreen | loop, hover | Why this matters (sourced, no fake logos) |
  | Before / after | PE tile travels across the day as you scroll; PM2.5 and band scrub with it | scrub | Same school, same day, about half the dose |
  | How it works (pinned) | Stage swaps 5:30 → 6:45 AM; clock hand and progress line scrub | pin + scrub | Forecast → optimizer → Cedar → agent → approve → WhatsApp |
  | Bento | Each card loops its own micro-animation (tile glide, rule stamp, breathing, waveform, bubbles, GRAP steps) | in-view loop, hover | Capabilities |
  | Playground | Sun slider, GRAP switch, haze, verdicts | drag / keys | The signature moment |
  | Stats | Count-ups | scroll in | Research numbers with sources |
  | FAQ | Answers rise in | click | Honest limits |
  | Closing CTA | Haze clears behind the headline | scroll | Open the live console |
  | Footer | Particles drift up along the horizon | loop | Credits, stack, sources |

### B. "Settling Water"
- Instrument Sans + Newsreader; deep teal → clear glass palette; `sine` easing, fluid and rippling.
- Signature: a glass of murky water whose particles settle as the day passes. Pretty, but the physics
  is wrong for air (pollution doesn't settle at midday, it disperses upward).

### C. "Split-flap Timetable"
- Space Grotesk + IBM Plex Mono; railway-board black/amber; `steps()` easing, snappy and mechanical.
- Signature: a departure board that flips PE from 08:05 to 13:05. It's memorable, but it reads as
  logistics rather than health, and it gives up the calm, premium feel.

**Pick: A.** It's the only one whose metaphor *is* the science the product depends on, which
makes the demo self-explaining for judges.
