<h1 align="center">EasyFighter</h1>

<p align="center">
  <b>Make fighting game characters for IKEMEN GO without writing code.</b><br>
  Put your drawings in slots, choose what each attack does, and the editor builds the rest.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="PyQt6" src="https://img.shields.io/badge/PyQt6-GUI-41CD52?logo=qt&logoColor=white">
  <img alt="IKEMEN GO" src="https://img.shields.io/badge/IKEMEN%20GO-characters-FF6B35">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="Made with AI" src="https://img.shields.io/badge/made%20with-AI%20(Claude)-8A2BE2">
</p>

<p align="center"><sub>An independent, fan-made tool. Not affiliated with or endorsed by the IKEMEN GO or MUGEN projects.</sub></p>

<p align="center"><i>Español: <a href="README.es.md">README.es.md</a></i></p>

<p align="center"><img src="docs/img/juego_especial.png" width="760" alt="Kaito, the example character, throwing his special in IKEMEN GO"></p>

> 🤖 **Made with artificial intelligence.** The code, the two example characters (Kaito and Saya, drawn with
> code) and the documentation were written by **Claude**, by Anthropic, in conversation with **Pollito001**, who came
> up with the ideas, decided how it should work, tested it and asked for the changes. It's a personal project:
> it was tested in IKEMEN GO, but it may have bugs.

## What is it?

**EasyFighter** is a character editor for **IKEMEN GO** (it also opens MUGEN characters), in the spirit of
Fighter Factory, but designed so that **anyone** can make a character:

- 🧸 **Simple mode:** a slot for each animation (standing, walking, attacks, specials…). Add your images or a
  sprite sheet and the editor builds the animations, the hitboxes and all the code.
- 🔥 **Specials and supers** with commands (↓↘→, →↓↘, charge…): projectiles, uppercuts, rushes, throws,
  counters and enders.
- 🔗 **Combos** in the style of Street Fighter, Marvel, Guilty Gear or **Killer Instinct** (auto-doubles,
  enders and combo breakers).
- 🎨 **Alternate colors** with one click per part (skin, clothes, hair…), 🔊 **voices** in WAV, OGG or MP3, and
  🧩 a **sprite sheet cutter**.
- 🤖 **CPU AI**, 📊 **frame data**, ✅ a **check** before sharing, 🕘 **version history** and 📦 a **.zip ready to
  share**.
- ▶ **Test in IKEMEN GO** with one button, and 🛠 advanced tools (sprites, animations and code by hand) for
  those who need them.
- 🌎 In English, Español, Português, Français, Deutsch and Italiano.

**📖 To get started, see the [step-by-step guide](docs/GUIDE.md).**

## Screenshots

| | |
|---|---|
| ![Attacks](docs/img/04_golpes_en.png) **Attacks:** one slot per attack | ![Specials](docs/img/05_especiales_en.png) **Specials:** command, animation and what it does |
| ![Combos](docs/img/06_combos_en.png) **Combos:** pick a style | ![Colors](docs/img/07_colores_en.png) **Colors:** click a part and pick its color |
| ![Moving](docs/img/03_moverse_en.png) **Moving and jumping** | ![Cutter](docs/img/09_cortador_en.png) **Sprite sheet cutter** |

<p align="center"><img src="docs/img/juego_colores.png" width="760" alt="Kaito with five color palettes"></p>

## Install and run

You need Python 3.10 or newer.

- **Manjaro / Arch:** `sudo pacman -S python-pyqt6 python-numpy`
- **Any system:** `pip install -r requirements.txt`

Then: double-click `main.py`, or run `python3 main.py` (or `python3 main.py path/to/character.def`).

Tested on Linux (Manjaro) with IKEMEN GO. Since it's Python it should also work on Windows and macOS.

## Example character

On the start screen (**🥋 Example character**) or in **File → «🥋 Example characters»** you pick one and
give it any name you like (or keep its own); the editor copies it wherever you say under that name —the
folder and every file— and opens it, so you can use it as a base. Both are complete and made only with simple mode (all
their animations, 18 attacks, a throw, 3 specials and a super), with original free drawings:

- **Kaito** (`ejemplos/Kaito`): Killer Instinct-style combos (auto-doubles, ender, combo breaker).
- **Saya** (`ejemplos/Saya`): Street Fighter-style combos, with a more detailed drawing.

Each one's move list is in its `LEEME.txt` (Spanish).

## Taking another character's sprites

**File → New character → «With another character's sprites»**, or double-click
`extraer_sprites.py` (or `./extraer_sprites.py source.def new_folder [name]`): it creates a new character
with the template's code, copies the other one's sprites, palettes and sounds, and puts its animations into
the simple-mode slots (standing, walking, jumping, getting hit, victory poses, normal attacks, throw,
specials and supers with their command). When it opens in the editor everything is built: check each slot,
align if needed and save.

Every simple-mode slot has **↔ Mirror** (for images facing left) and the **speed as a number** (ticks per
frame); the sheet cutter has «↔ Mirror» too.

**Hit boxes on what hits:** simple mode puts the red box (the one that does damage) only on the tip of what
attacks —the fist, the foot, the knee—, comparing with the standing pose. On each attack or
special, **🟥 Damage box** picks between **Automatic** and **By hand**: **✏ Draw…** lets you move it, stretch it
or draw more frame by frame, and when you save the animation switches to "By hand" (only what you drew hits;
you see the same in "✋ Align and show boxes"). If you go back to "Automatic", your drawing is kept in case you
switch back.

**Body boxes (the blue ones, where it can be hit):** the editor adds them to every drawing. In «👤 Character»
you choose **2 boxes** (body and head) or **1 box** (whole body). And every slot has **🟦 Body**: **Automatic**
or **By hand**, with **✏ Draw…** to move them, stretch them, draw as many as you like, or leave a frame with a
single box or none (it can't be hit there).

**Attacks that step and change when repeated:** every normal attack has «Moves:» (a step forward or back
while hitting) and «🔁 When pressed again» (up to 3 more animations when pressing the same button in a row,
or alternating between two).

## What it does

Dark theme with a sidebar and a start screen with your recent characters (with their portraits; to take one off the list, ✕ or right-click, or “🧹 Clear the list”).
Bottom left: **💾 Save all** and **▶ Test in IKEMEN GO** (opens a quick match with your character: pick
opponent, stage, CPU level, palette, no time limit, full power and **nobody dies**: the fight runs in training
mode, life refills by itself and nobody gets KO'd; for that the editor adds a tiny file,
`external/mods/chareditor_test.lua`, which only does anything when the editor opens the game).

### 🧸 Simple mode and 🛠 advanced mode

The editor always opens in **simple mode**. The advanced tools are tucked away in **File → 🛠 Advanced tools…**
(it asks for confirmation; to go back, use the "🧸 Back to simple mode" button at the bottom left):

- **🧸 Simple mode** — make a character without touching code. Everything is a slot: put your images in
  each one (📂, in name order) or pick sprites it already has (🖼), choose the speed and watch it animate.
  The editor builds the animations, hitboxes and code for you.
  - **👤 Character**: name, author, life, attack, defense, air jumps, **time lying on the ground** before getting up, **size** (with a preview) and **🔍 enlarge the sprites to that size** (really enlarges them,
    with their animations and boxes, and sets the size back to 100 %), body width,
    height, power bars, shadow and bounce when falling; if it's inside IKEMEN GO/chars, add it to the select
    screen and set its **music** (stage music, victory music and low-life music, in `data/select.def`).
  - In **🚶 Moving and jumping**, **👊 Attacks** and **🤕 Getting hit** every slot starts **closed** (▸): the
    row shows a thumbnail and what's missing (**⚠ Sprites missing** in orange, **✅** ready, **ℹ** uses what
    it already had), and each group says how many are ready ("3 of 7 ready"). Click to open, or use
    "⊞ Expand all / ⊟ Collapse all".
  - Moves not every character has come with a **Has it** tick: running (→→), back hop (←←), turning, jump
    start, forward flip, air guard, trip, air recovery, dizzy, intro, win, time-over loss, draw, crouching and
    air attacks, and the throw. Untick it and the slot says **⭘ Doesn't have it** (it counts as ready) and the
    game uses another animation instead (turn → first frame of "Standing", trip → "Goes flying", win →
    "Standing"…). Running and the back hop are also switched off in the .cmd, and unticked attacks aren't
    generated. The essentials (standing, walking, crouching, jumping, standing attacks, getting hit…) have no
    tick.
  - **Downloaded characters**: simple mode reads the character's .cmd and states and shows what it already
    has. Its moves **are edited in its own code**, so its combos, cancels and effects keep working:
    - In **👊 Attacks**, the slots of existing attacks and the throw say **ℹ Already has it: "name"** (they
      count as ready). Adding images, sprites or a sheet, or changing the speed, changes its animation (same
      action number); **Damage** is changed in its HitDef. **📋 Redo in simple mode** replaces it with a
      simple-mode attack (losing what's special in its code; it comes back if you clear the slot).
    - In **🔥 Specials and super**, the **🎮 The ones the character already has** section shows each one with
      its versions (light / strong…). Opened, you can change its animation, each version's damage and the
      command (**🎮 Change command…**, each version keeps its button), all in its code. The **Has it** tick
      switches it off.
    - **📋 Move to simple mode** / **📋 Move all to simple mode** bring it into simple mode **without losing
      anything**: each controller in its code becomes an editable **event** (hits, projectiles, sounds,
      movement, effects…; anything not recognized stays as "Custom code", as is). It keeps its state numbers,
      and its .cmd entries stay in the same place (order matters for combos), just using the simple-mode
      command. The original [Statedef] is kept renamed, and **↩ Original** / **↩ Restore the originals** put
      everything back as it was.
  - **🚶 Moving and jumping**: standing, walking (leave "back" empty to use "forward" in reverse), running,
    back hop, crouching, turning, jumps, intro, win, lose, draw and the pose when chosen. The slots that move
    the character have their **speed** (or height and distance for jumps) with **🦶 To its steps** (walk and
    run: measures the steps so the feet don't slide), **📏 To its size** (jumps and back hop: height and
    distance based on how big it is) and **▶ Test** (watch it move over a marked floor).
  - **👊 Attacks**: light / medium / heavy punch and kick (x y z, a b c) standing, crouching and in the air,
    plus the **throw** (→ + button close to the opponent). The hitting frame is picked for you (the one that
    reaches furthest, red border) and you can change it, and the damage. The crouching heavy kick is a sweep.
  - **🔥 Specials and super**: each one is a row that opens and closes (▸ / ▾, or "Open / Close all") with
    **Data**, **Animation**, **Projectile** and **⚙ Settings** tabs (how many hits and every how many ticks,
    pause, push, chip damage, knockdown / launch (no, **with the last hit** —the earlier hits keep them stunned on their feet— or with every hit), how it's blocked, juggle, invincibility, dash speed, whether it **stops on hit** (instead of carrying on and
    pushing the opponent), uppercut forward
    distance and height, power gained or bars spent, super pause and darkening, cancel from normals). Also: command (↓↘→, →↓↘, charge…), punch or kick button, light / medium / heavy
    versions, and what it does: **throw a projectile** (with its animation and its hit animation), hit in
    place, dash or rising uppercut. The super uses one power bar and darkens the screen.
    **🎮 Create…** opens the command creator: tap the arrows in order (and "charge" the first one if you
    want, or pick **Press the button while walking** → / ← for a move that comes out while walking,
    alone or after the arrows) and it's saved to your list for any special. For projectiles you choose **where they come out**
    (forward / height, or automatic from the hand) and their **speed**, and **▶ Test** shows the special
    against a test opponent with **all its events** (impulses, take-off, teleport, projectiles and effects,
    trail, flashes, shakes, pause) and the hitbox in red on the frames that hit (you can also tap the spawn
    point there). The tests have **speed** (100% to 10%), **⏸ pause** and **⏮ ⏭ tick by tick** to watch them
    closely.
    In **🎞 Animation**, **💥 Frames that hit** shows each frame as a button: mark every frame that has a
    hitbox. Each group of consecutive frames is one hit and the damage is split between them (with none marked
    it hits on the "Hits / launches on frame" frame, as before).
    More options: **command grab** (close range, unblockable), **counter** (catches the opponent's attack) and
    **no hit** (movement or effects only) types; an **EX** version (two buttons together, costs half a bar,
    glows and hits harder); usable **on the ground, in the air or both**; supers can **cancel a special**; the
    projectile can rise, accelerate or **drop like a grenade**. **"What it does" is built from events**: when you
    pick the type, its movement shows up in **⏱ Events** marked "from the type" and you change it there (the
    uppercut brings a "Move / impulse" that **flies up** on the frame you choose, with its forward and upward
    force, its **speed (%)** and whether it **changes with the version**; the dash brings "advance" and
    "brake"; the projectile one brings the "🔥 Projectile" event, which is the same as the "Projectile" tab —
    edit it in either; the super brings its "flash pause", during which the character holds that frame while the flash
    happens and then continues). The **⏱ Events** tab adds things that happen on
    an animation frame (▲▼ to reorder, ⧉ to duplicate): **move / impulse**, **instant move**, **teleport**
    (behind or in front of the opponent), **turn**, **stay still** (float), **extra hit** (with its damage and
    hit count), **extra projectile** (with its animation, speed, acceleration and spawn point), **effect** (a
    separate animation — fire, aura, sparks… — from the character, the opponent or the screen), **sound**,
    **invincible**, **counter**, **screen shake**, **color flash**, **after-image trail**, **flash pause** (the spark can be turned off),
    **character pause** (only he freezes, with or without a glow; the opponent and projectiles keep going), **screen
    color** (a flash), **transparent / invisible**,
    **power**, **life**, **follow up with another special** (on hit, on a button press or at the end — for
    chains and combos) and **custom code** (for anything not on the list).
  - **🤕 Getting hit**: guarding (standing, crouching, air), hit in the face, in the stomach, crouching,
    knocked into the air, falling, hitting the ground, lying down, getting up, tripping, recovering, dizzy.
  - **🔗 Combos**: pick a style — **Basic**, **Street Fighter** (links, repeating lights, canceling into
    specials), **Marvel / Darkstalkers** (light → medium → heavy chains, launcher and air combos), **Guilty
    Gear** (gatling, jump after any hit and a meter «Roman cancel») or **Killer Instinct** (opener →
    auto-double → linker → auto-double → **ender**: auto-doubles after a special connects, each hit with its
    own animation and without pushing the opponent; a **button rule**, free like KI 2013 or classic like KI
    1994 — heavy → medium, medium → light, light → heavy —; the heavy version of a special after an
    auto-double is the **ender**, with extra damage, a knockdown and the end of the combo; a hit limit; and a
    **strength combo breaker**: punch + kick of the same strength as the hit that just landed, with a
    **lockout** of a few seconds if you fail) — and change whatever you want: how attacks chain, which attacks
    cancel into specials, the launcher, jumping with ↑ to continue the combo, each auto-double (which special
    starts it, which animation each hit uses and its speed in %, picked from the attacks, specials and supers the character
    already has — «doesn't hit» flags the ones without a red box), **▶ Test combo** (build the whole combo,
    special → auto-double → special…, and watch it animated with the hit count and speed control), the buttons and cost of the combo breaker and the meter cancel, less damage in long combos and
    extra stun ticks so combos connect.
    Auto-doubles are a **list** (➕ as many as you want, light, medium or heavy, with the button and the
    special that opens them, even the super or a dash), they come out **after the special's last hit**
    without cutting it, and you can also build them in the **🎨 visual maker** (animation gallery, hit strip
    with speed and an animated preview). The tab's cards **minimize** by clicking their title. «Specials and
    super» has **💥 Add ender** to make your own enders; with «Ender of» an ender uses a special's same command (with the
    heavy button, like KI) and only comes out after an auto-double, which is no longer interrupted.
    Like Killer Instinct 2: a max of **auto-doubles per combo** (4; the last one knocks down), a **jump-in air
    attack** opens auto-doubles, the **ender closes the combo** and the **KI2 combo breaker** (one button of
    the hit's strength: punch if it was high, kick if it was low). An auto-double only comes out with the
    opponent **close** (it's part of the combo: the character doesn't run to them), and every special or super has an
    **Opens auto-doubles** box in its ⚙ Settings (ticked on specials, unticked on supers: without it they end the
    combo and knock down).
  - **Extra poses**: «Intro and ending» has optional slots for **more victory and defeat poses**; when
    winning (or losing on time) one is picked at random. Moves with «Has it» unticked (run, back hop, air
    recovery or the character's own moves) **no longer respond** to their command.
  - **🎨 Colors**: alternate colors (palettes 1 to 12, the ones you get by picking it with another button). The
    colors are grouped into **parts** on their own (skin, clothes, hair…): tap one (in the list or by clicking the
    character) and choose its color, and its shadows and highlights adjust automatically. Also **🎲 New random**
    (colors that go together; skin and outlines stay), colors one by one, duplicate, delete and compare with the
    original in different poses. They're saved in the SFF (1,n) or in the `.act` if the `.def` uses one. Since in
    IKEMEN GO palettes don't change 32-bit sprites, a button **moves the sprites to the character palette** (up to
    255 shared colors, almost identical; portraits stay; it can be undone).
  - **🔊 Voices**: when attacking, throwing, special, super, ender, getting hit, KO, winning and intro (WAV, OGG, MP3, FLAC…), in
    sections that open and close. **Each special, super or ender can have its own voice** (on that page or on the
    move's "📋 Data" tab); without one it uses the general one for its type, and it can also be set to none.
  - **🎴 Select screen**: slot face, big portrait, victory portrait and the animated character,
    with a preview (set an image or crop it from a sprite; it's resized for you).

  In every slot, **✋ Align and show boxes** opens the frames large: drag them into place (with the previous
  frame as a guide, the floor and the axis), "🦶 Feet on the ground" lines them up for you, and you see the
  hitboxes (blue: where it gets hit · red: where it hits). With "Show hitboxes" they also appear on the slots.

  **🎯 Align to the standing one** (in that same window) and **🎯 Align all to the standing one** (at the top
  of Move and jump, Attacks, Specials and Getting hit) recognize the **body** (torso and head, without arms and
  legs) and the **feet** in each frame, compare each frame with the previous one so the animation doesn't jump
  around, and anchor everything to the standing animation. Each animation has its own mode, picked
  automatically and changeable: *Ground: planted foot* (attacks, blocking, getting hit), *Ground: steady body*
  (standing, walking, running, throws, specials), *Air: attacks*, *Air: flips and falls* and *Lying down*.
  «Align all» shows before and after with the standing pose as a guide, and Ctrl+Z undoes it.

  What you set in simple mode is saved in `<character>.simple.json`; the code goes in
  `<character>_simple.st` and two marked blocks of the `.cmd`, rebuilt every time (nothing gets
  duplicated). "Colors when adding images" picks exact colors (recommended) or the character palette.
- **🛠 Advanced mode** — everything below, by hand, like Fighter Factory. If you open something simple mode builds
  (the `_simple.st`, what's between the "SIMPLE-MODE" marks in the `.cmd`, or one of its animations) a yellow
  notice shows up, and your first change reminds you it gets rebuilt and hand edits are lost.

### 🆕 More moves, AI and finishing the character

- **More moves** (all optional: leave the slot empty and it doesn't have it): a **taunt** with the Start button
  (in «Intro and ending»), an **air dash** with → → or ← ← (in «Jumping»), an **air throw** (in «👊 Attacks») and,
  in each special's ⚙ Settings, **wall bounce**: the opponent is shot back, bounces off the edge of the screen and
  falls so you can keep the combo going.
- **New specials:** **calls a helper** (a new type: it appears in front, moves forward and hits; its animation goes
  in the «🧍 Helper» tab), **several projectiles at once** in a fan, and a **beam** (on specials and supers): it
  comes out of the hand, **stretches** to its length and hits several times. It has optional parts in the
  «🔥 Projectile» tab (a **charge** before the beam, a **muzzle** stuck to the hand and a **tip** that moves forward,
  all with the beam's effect) and, in ⚙ Settings (in its own **🔦 Beam** section), a ready-made **beam type** (classic, fast laser, electric, fire
  stream, short or super beam) you can customize: its length (or to the edge of the screen), how fast it
  stretches, whether it hits **non-stop** (every few ticks until it fades) or a set number of times, an **effect**
  (blink, electric pulse or wobble) and **how it ends**: it shrinks toward its axis, **closes toward the center**
  (from top and bottom), only fades out or vanishes at once.
- **Beams that fall from the sky or come out of the ground, and in chains:** the **beam direction** can be
  forward, **falls from the sky** (a column coming down to the ground) or **comes out of the ground** (a column
  going up). You draw it as always (lying down, facing right) and the editor rotates it, hitboxes included; if
  you already drew it standing (vertical), **«How it's drawn»** keeps it as is (on «Automatic» it notices on its
  own because the drawing is taller than wide). It
  can fall **in front of the character** or **on the rival**, and there can be **several beams one after
  another** (how many, the gap and the time between them); the damage is split among them. Ready-made types:
  **Thunder on the rival**, **Rain of beams**, **Columns from the ground** and **Storm on the rival**. All of
  it shows in ▶ Test just like in the game.
- **Versions on supers and enders:** like specials, the super and the ender can have light, medium and heavy
  versions (each with its button; stronger = more damage and faster). An ender «of a special» still only comes
  out with the heavy button.
- **🔊 Combo voices:** in «🔊 Voices → 🔗 Combos» you add one slot per hit count (➕): at 3 hits one plays, at 5
  another… If one hit skips several, the highest plays.
- **🏆 Victory quotes** in «👤 Character» (one per line; the game picks one at random).
- **🤖 AI (CPU):** how it fights when the computer controls it: aggressiveness, whether it does combos, whether it
  uses the super and when it uses each special (up close, mid range, far away, against a jumping opponent or
  never; «Automatic» picks based on what it does). It only changes the CPU (`AILevel > 0`), never the player.
- **🏁 Check and share:**
  - **✅ Check the character**: empty animations, unfinished specials, repeated commands, voices using sounds that
    are gone, missing portraits and code errors. Double-click one to go fix it.
  - **📊 Frame data**: for each attack and special, how many ticks until it hits, how long it stays active, how
    long it takes to recover and the advantage on hit and on block (approximate).
  - **🕘 Version history**: snapshots of the character's folder in `_editor_history` (automatically when saving, at
    most every 15 minutes, or by hand). «↩ Go back to this one» saves another snapshot first, so it can be undone.
  - **📦 Share**: a clean `.zip` (without `_editor_backups` or `_editor_history`) with a `COMANDOS.txt` listing its
    moves.

### 🧩 Sprite sheet cutter

In every simple-mode slot (**🧩 From a sheet**), in 🎴 Select screen (**🧩 Take from a sheet…**, for the face,
portrait and victory portrait) and in the Sprites tab (**🧩 Cut sheet…**). Open a sprite
sheet and it cuts it for you:
- **Automatic background**: uses transparency or the border color; it also recognizes a second fill color
  and drawn **grid lines**. Pick more colors with 🎯; the **tolerance** (set automatically for JPG) also
  cleans the background-tinted edge.
- **Precise cuts**: each frame keeps only **its own** pixels (even if boxes overlap, nothing from the
  neighbor leaks in); loose bits (hair, sparks, drops) stick to their sprite; tiny specks are ignored; two
  sprites that ended up touching are split.
- **In order**: by rows, left to right, with a number on each picked frame.
- **Easy picking**: click a frame, double-click for the whole row, drag for several; merge or remove boxes,
  or draw one by hand with Shift + drag. There is also a **grid** mode (fixed-size cells).
- **✋ Cutting by hand**: for sheets where automatic cutting doesn't work. Draw each box by dragging and
  adjust it like the hitboxes: drag inside to move it, drag its edges and corners to stretch it, use the
  arrows to move it 1 px at a time (Shift: 10) and Ctrl + arrows to resize it. You can also type its exact
  position and size. **➡ Another one next to it** adds a same-size box to the right (to cut a row fast),
  **✂ Fit to the drawing** shrinks it to what's drawn and **📐 This size for the picked ones** makes them all
  match. It has **↶ Undo** (Ctrl+Z), and the boxes are saved for that sheet: next time you open it they're
  still there. If you switch to "by hand" after an automatic cut, its boxes are the starting point.
- **Repeat frames**: **Ctrl+click** a frame to add it again at the end (or right-click → **⧉ Add it again**),
  so you can build 1-2-3-2-1 with a frame that appears only once on the sheet. Each frame shows the
  positions it's used in (e.g. «2,5»). Under the preview there's the **order strip**: drag to change it, or
  use ⧉ Repeat, ◀ ▶ and ✖ Remove. A repeated frame is stored only once as a sprite.
- **Automatic axis**: common ground of each row (jump frames stay in the air), each frame's feet, the
  center, or **the center with the feet on the floor** (centered side to side but not buried in the floor); centered on the feet, so it doesn't "jump" when an arm or leg stretches out.
- **Enlarge frames** while cutting (without blurring), for small sheets.
- **Frames already used**: the ones you already cut for this character show up marked in purple with the
  name of the slot they're in (hover to see it in full). Hide them with their checkbox, or right-click →
  **✖ Forget that I used it**. If you cut a slot again, its marks are replaced by the new ones.
  **🔍 Find the ones I used** compares the sheet's drawings with your slots' sprites and marks the ones
  already there (for what you cut before); it runs by itself the first time you open a sheet with no marks.
- **Animated preview** before adding them. It remembers the last sheet and its settings, so you can fill
  slot after slot.
- In advanced mode: starting group, one group per row, one animation per row and color type.

### Advanced mode

**File → ✨ New character**
- From the **template**: a character you can play in IKEMEN GO right away, with a placeholder figure,
  every animation the game needs and a sample punch (button *a*). Pick the resolution: 320×240 (classic
  MUGEN), 640×480 or 1280×720 (HD); sizes and speeds are scaled for you.
- By **copying** another character to use as a base (it gets the new name).

**Backgrounds**: the Sprites, Animations and Simulator views have a background with the floor at the
character's feet. Pick one of 12 (dojo, sunset, night city, forest, beach, temple, snowy mountain,
training, green screen, black, gray and the usual checkerboard) or use **your own image**; 🌓 darkens it
so the boxes stand out. The choice is remembered and shared by the three views.

**📝 Data** — the `.def`: name, author, versions, resolution, default palettes, files (✅ / ❌ whether
they exist), `pal1…pal12` palettes and storyboards. It can also be edited as text.

**🖼 Sprites**
- Fast list even with thousands of sprites (only visible ones are drawn).
- Move the **axis** by dragging the sprite (or arrow keys; Shift = 10 px). Semi-transparent reference
  sprite (0,0 or the previous one) for alignment.
- **Add images** (PNG, BMP, GIF, PCX…): group and number from the file name (`200-3.png`), colors mapped
  to the character palette, own palette or 32-bit; axis at bottom-center, center or 0,0.
- **🖌 Pixel editor** (Ctrl+E or double-click): pencil, eraser, fill, eyedropper, line, rectangle,
  select and move, copy/paste, flip, rotate, replace a color, canvas size, crop, set the axis; with undo.
- **🧰 Batch**: axis, palette, renumber or export many sprites at once.
- Replace, export one or all (with `axes.txt`, which keeps the axes for re-importing), duplicate, delete,
  trim transparent borders and sort.
- **Palettes**: view sprites with any character palette, edit colors (double-click), open/save `.act`,
  create palettes, change a sprite's palette.
- Opens SFF v1 and v2; always saves **SFF v2** (unchanged sprites are copied as-is, so saving is fast).
  SFF v1 files are converted with the right palette.

**🎞 Animations**
- **Frame panel** (like Fighter Factory): group, number, offset with nudge arrows, time, flip (none /
  horizontal / vertical / both), transparency (none / add / soft add / subtract / blend with source and
  dest), loop start, scale and angle; each with “⇶” to use it on every frame.
- **💻 Animation code**: view and hand-edit the text (.air) of the selected action.
- Named actions, frame table (group, number, X, Y, time, flip, transparency, IKEMEN scale and angle),
  60 fps playback with speed control, onion skin and face-left view.
- **Hitboxes**: draw Clsn2 (body) and Clsn1 (attack), move and resize them with the mouse, nudge with
  arrows, Delete removes; copy from the previous frame or apply to every frame.
- **🪄 Automatic hitboxes** from the visible part of the sprite (one box or head + body), for one frame
  or the whole action.
- **🎬 Export to animated GIF**.
- Add all sprites of a group as frames in one go.
- Only the actions you change are rewritten: comments and formatting elsewhere stay the same.

**💻 Code** (`.cns`, `.cmd`, `.st`, `.zss`, `.ai`…)
- Syntax colors, line numbers, **autocomplete** with every IKEMEN GO state controller and trigger
  (Ctrl+Space), outline to jump to each `[Statedef]`, `[State]` or `[Command]`.
- **Hover help** on controllers and triggers: what they do and their parameters.
- Find / replace (Ctrl+F, F3), go to line (Ctrl+G).
- **🔍 Check for errors** (F7): `[State]` without `type` or `trigger1`, unknown controllers, unclosed
  parentheses or quotes, duplicated `[Statedef]`, and warnings when a `ChangeState`, `ChangeAnim` or
  `PlaySnd` points to something the character doesn't have.

**🧪 Simulator** — pick a `[Statedef]` and watch it move: physics (S/C/A), gravity, VelSet, PosAdd,
ChangeState, ChangeAnim, variables, when the hit is active (HitDef), sounds, trajectory and boxes. Mark
buttons as held and see tick by tick which controllers ran (double-click jumps to that code line). The
game's common states aren't simulated: the simulation ends there.

**🥊 Moves** — a wizard for a complete move: command (↓↘→, →↓↘, charge, etc.), special / super /
normal, standing / crouching / air, the animation from a sprite group with its boxes, the hit (damage,
height, strength, push, knockdown) or a **projectile**, forward or jump impulse and sound. It shows the
code before adding it, then puts it in the .cmd (before the normals), the states file and the .air.

**🔊 Sounds** — play, add sounds (group and number from the file name), replace, export, delete and
renumber. Inside the `.snd` IKEMEN GO only plays WAV (music can be OGG, MP3…), so when you add an **OGG, MP3,
FLAC, OPUS, M4A…** the editor converts it to 16-bit PCM WAV on its own (an odd WAV too, like 32-bit or
compressed). It uses `ffmpeg` if you have it installed; otherwise the decoder that comes with PyQt6.

**Everywhere**
- Undo / redo (Ctrl+Z / Ctrl+Shift+Z) for sprites, animations and sounds.
- **File → 💾 Save all** (Ctrl+S). The title shows ● when there are unsaved changes.
- Before a file is overwritten, a copy is kept in `_editor_backups/<date>/` inside the character folder.
- Languages: Español, English, Português, Français, Deutsch, Italiano (**Language** menu; applies on
  restart). To add one, copy `lang/en.json`, set `_name` and translate the values.
- Themes: Dark (orange), Light, Midnight (blue), Arcade (purple and pink), Forest (green) and High contrast
  (**Theme** menu; changes right away and is remembered).

## Building executables (Windows, macOS, Linux)

So people can use the editor without installing Python, you build an executable. Each system builds its own
(PyInstaller can't make the Windows one from Linux), so there are two ways:

**On your computer (for your system):**
```bash
pip install -r requirements.txt pyinstaller pillow
python3 packaging/build.py                 # folder + .tar.gz (Linux) or .zip (Windows / macOS)
python3 packaging/build.py --appimage      # Linux: also an .AppImage (needs appimagetool)
python3 packaging/build.py --onefile       # a single file (starts slower)
python3 packaging/build.py --version 1.0   # version in the file names
```
Everything ends up in `dist/`.

**All three at once with GitHub:** the repo includes `.github/workflows/build.yml`. In the **Actions** tab →
**Ejecutables** → **Run workflow**, GitHub builds the Windows, macOS (Apple Silicon) and Linux (.tar.gz and
.AppImage) ones and leaves them under "Artifacts". If you push a version tag it also creates a **Release**
with the files ready to download:
```bash
git tag v1.0
git push origin v1.0
```
On macOS, since it isn't signed, the first time you open it with right-click → Open.

## Project layout

```
main.py            entry point
core/              formats: sff.py, air.py, snd.py, deffile.py, codeinfo.py, template.py, project.py,
                   simple_gen.py (simple mode code), selectdef.py (select.def and music), sheetcut.py (sheet cutter)
ui/                window and tabs
lang/              translations
ejemplos/          the example characters (Kaito and Saya)
packaging/         build.py: builds the executable · .github/workflows: builds it on GitHub
docs/              the guide and screenshots
```

## License

[MIT](LICENSE): you can use, change and share it freely, as long as you keep the license notice. The example
characters (Kaito and Saya) are original and come under the same license.

IKEMEN GO is a separate project by its own authors: <https://ikemen-engine.github.io/>.

### Notices

- **Dependencies:** PyQt6 (GPL v3 or Riverbank Computing's commercial license) and numpy (BSD). This
  project's code is MIT, which is GPL-compatible. If you ever distribute **executables** that bundle PyQt6
  (PyInstaller, AppImage…), that bundle falls under the GPL v3: include PyQt6's license and make the source
  code available (this repository).
- **Game screenshots:** taken in IKEMEN GO (MIT) with its default screenpack: lifebars by Ohmga Shironeko
  ([CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)) and Elecbyte's MUGEN fonts
  ([CC BY-NC 3.0](https://creativecommons.org/licenses/by-nc/3.0/)). Kaito and Saya are from this project.
- **Trademarks:** IKEMEN GO, MUGEN, Fighter Factory, Street Fighter, Killer Instinct, Marvel, Darkstalkers and
  Guilty Gear belong to their owners. They're only named here to describe gameplay styles; this project isn't
  affiliated with any of them.
- **Other characters' sprites:** the editor can take another character's sprites. Use it with your own
  characters or with their authors' permission, and don't publish characters made with someone else's
  sprites without that permission.
