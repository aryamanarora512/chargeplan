---
version: alpha
name: ChargePlan
description: A one-screen planner a fleet supervisor uses in the evening to see whether every van will be charged by morning, and at what cost. It should feel like a well-kept dispatch board, quiet and exact.
colors:
  ground: "#F5F6F7"   # page
  paper: "#FFFFFF"    # the board and input fields
  ink: "#121820"      # text, primary button
  muted: "#566069"    # secondary text, 5.9:1 on ground
  rule: "#D3D8DD"     # table rows, input borders
  shade: "#E6EAEE"    # higher-priced hours on the board
  charge: "#B8730C"   # energy going into a van, the only accent
  short: "#B42318"    # a van that won't be ready (always with a label)
typography:
  display:
    fontFamily: Barlow Semi Condensed
    fontSize: 36px
    fontWeight: 600
    letterSpacing: 0
  heading:
    fontFamily: Barlow Semi Condensed
    fontSize: 18px
    fontWeight: 600
  body:
    fontFamily: Barlow
    fontSize: 16px
    lineHeight: 1.5
  small:
    fontFamily: Barlow
    fontSize: 13px
    lineHeight: 1.4
rounded:
  sm: 3px
  board: 0px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.sm}"
    padding: 10px 18px
  button-text:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    padding: 10px 0
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    borderColor: "{colors.rule}"
    rounded: "{rounded.sm}"
---

## Overview

ChargePlan is for the person at a small depot who plugs in 3–10 vans each evening and needs them charged by their
morning departures without going over the site's power limit. The look comes from that world. The night runs
left to right like a dispatch board, prices change by the hour like a utility tariff table, and charging is lit like
a sodium yard lamp. It's a working tool, so it stays calm. The plan itself is the only loud thing on the screen.

**Status:** adopted 2026-11-15 and built in Milestone 2 (`frontend/`). Changes made while building are listed under
"Built so far" at the end.

## First screen

The app opens with two lines of intro, then an example plan **already solved**. A new user sees what a result
looks like before typing anything. No modal, no tour.

> **ChargePlan**
> Plan tonight's charging for a small EV fleet. Enter your vans, power limit and electricity rates.
> ChargePlan finds the cheapest schedule that gets every van out on time.

## Colors

- **Ground (#F5F6F7):** a cool off-white, like a whiteboard under depot lights. Deliberately not cream.
- **Paper (#FFFFFF):** the board and the input fields. This is the only raised surface.
- **Ink (#121820):** all text and the primary button; 16.5:1 on ground.
- **Muted (#566069):** labels and secondary lines; 5.9:1 on ground.
- **Rule (#D3D8DD):** table rows and input borders only. Never a box around a section.
- **Shade (#E6EAEE):** marks the higher-priced hours behind the board, so price is visible exactly where charging is decided.
- **Charge (#B8730C):** sodium-lamp amber, with one job: energy going into a van. It's never used for buttons or decoration.
  At 3.2:1 on shade it meets the 3:1 contrast floor for graphics.
- **Short (#B42318):** only for a van that won't be ready. Always paired with the word "short" and the shortfall.

A ready van uses ink and a check mark, not green. Red is the only status color.

## Typography

Barlow takes its shapes from California highway signs and license plates, the printed world of vans on roads.
Body and inputs are in Barlow. Headings, the verdict, and the board's time labels are in Barlow Semi Condensed, which
fits a night of half-hour columns. Numbers in tables use tabular figures. The one large moment is the verdict line (36px).
Fonts ship with the app (self-hosted from the `@fontsource` packages), so every visitor sees them and no font host is called.

## Layout

One screen. On desktop, the inputs sit in a narrow left column (400px) and the results take the rest. On a
phone, the order is intro, result, then inputs. Sections are separated by space and a heading, not by boxes.

**Signature: the night board.** Each van is a row and each half-hour is a column. The higher-priced hours are shaded
behind all the rows, charging is drawn as amber blocks, and the board ends each van's row at its departure. A final
"Site" row shows total power against the limit. A table of the same numbers sits underneath.

## Elevation & Depth

Flat. No shadows. The board and inputs sit on paper white over the ground; that is the only layering.

## Shapes

3px corners on inputs and buttons. The board is square-cornered, like a printed sheet. Charging blocks are square.

## Components

- **Primary button:** ink fill, paper text, labeled with the action ("Plan tonight"). One per screen.
- **Text buttons:** "Add van", "Add rate", "Reset example", "Export CSV". Ink, underlined on hover.
- **Inputs:** a paper fill with a rule border, the label above, and the unit in the label ("Limit (kW)"). An error shows
  under its field in short red text.
- **Verdict:** one large line ("Both vans ready for $8.40.") and one muted line (the comparison, or why it failed).
- **Details:** the engine's full explanation, collapsed under "Why this plan".
- **States:** working ("Planning…", button disabled), out of date ("Out of date. Press Plan tonight."), impossible,
  invalid input, and solver failure. Each one is a single sentence.
- **Focus:** a 2px ink outline on every control. Visible on keyboard focus.

## Copy

- No word that doesn't help a decision. Labels are nouns with units, and buttons say what happens.
- Sentence case everywhere. No taglines, superlatives, exclamation marks, or arrows on buttons.
- Say "van" (the user's word), "power limit" (not "allowance"), and "rates" (not "tariff").
- Every number has its unit. Money is shown to cents, and kWh to one decimal.
- One footnote, always visible under the results: "Energy cost at the rates entered. Doesn't control chargers."

## Do's and Don'ts

- Do reuse these tokens on every future view (saved plans, comparison) and in the report charts. The current
  matplotlib charts use an earlier palette and move onto these tokens in Milestone 3.
- Do add a token here before any view uses it.
- Don't use dark mode unless someone asks for it (C7).
- Don't use: purple/indigo gradients (C1); EV-green or teal as the accent (SD8); lightning-bolt or leaf icons;
  cream with terracotta (SD1); near-black with a neon accent (SD2); all-caps eyebrow labels, middle-dot meta strings,
  mono labels, or arrows on buttons (SD4, CP3); one colored word in a headline (SD5); decorative 01/02/03 (SD6);
  a row of KPI stat cards (L4); rounded, shadowed, bordered cards around every section (K2); colored left-border
  cards (K4); icons in tinted chips (K6); cards inside cards (K11).

Method: [avoid-ai-design](https://github.com/funboy322/avoid-ai-design), whose catalog IDs are cited above.

## Built so far (Milestone 2)

Everything above is built, with these adjustments found while testing it in a browser:

- The left column is 400px, not 360px, so a van's two times fit side by side.
- Only the first price label on the board says "/kWh". Later labels show just the price, so the last one fits on a phone.
- The van columns are labeled "kWh" and "kW", with a fuller description on hover and for screen readers.
- On screens narrower than 520px, the table drops "Needs" and "Cost". The total cost is in the verdict, and "Status" shows any shortfall.
- "Export CSV" is not shown yet. It arrives with the feature in Milestone 3, rather than as a dead control.
- The default example is `early_departure`: one van leaves before the cheap hours.
