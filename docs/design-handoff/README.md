# Handoff: Jobbsvep – "Svep först" (design 2b)

## Overview
Jobbsvep is a Swedish job-search web app for job seekers that works like a dating app: the user is shown one job at a time as a card and swipes right to apply, left to skip, or saves it for later. When an employer is interested (a "match"), a match screen opens and the user can start a chat. All UI copy is in Swedish.

This package covers direction **2b "Svep först"** (swipe-first): desktop landing page, desktop swipe view, mobile swipe view and mobile match screen.

## About the Design Files
The files in this bundle are **design references created in HTML** – prototypes showing intended look and behavior, not production code to copy directly. The task is to **recreate these designs in the target codebase's existing environment** (React, Vue, Next.js, SwiftUI, etc.) using its established patterns and libraries. If no codebase exists yet, choose an appropriate stack (suggestion: React + TypeScript, Vite or Next.js, CSS Modules or Tailwind) and implement the designs there.

- `Jobbsvep-2b-standalone.html` – open in any browser, works offline. Fully interactive (drag cards, buttons, match screen).
- `source/Jobbsvep 2b.dc.html` + `source/support.js` – the editable source. Markup is in the `<x-dc>` block with inline styles; behavior is in the `<script data-dc-script>` class at the bottom (`JOBS` data + swipe logic). Open via a local web server (e.g. `npx serve source`).

## Fidelity
**High-fidelity.** Final colors, typography, spacing, copy and interactions. Recreate pixel-accurately. Photos are placeholders (striped boxes) – replace with real images.

## Screens / Views

### 1. Landing page – desktop (1280×800 reference)
- **Purpose:** Explain the product and get the user to create an account.
- **Background:** full-bleed photo (placeholder: "helbildsfoto: person på sin arbetsplats") with overlay `rgba(20,16,24,.55)`. All text white.
- **Header** (padding 22px 56px, flex space-between):
  - Logo text "jobbsvep" – Onest 26px / 800, letter-spacing -0.02em.
  - Nav: "Så funkar det", "För arbetsgivare" – 15px / 500, gap 32px.
  - "Logga in" – outline pill (1.5px solid #fff, radius 999px, padding 9px 18px, 15px/600). "Skapa konto" – white pill, text #1d1715, padding 10px 18px.
- **Hero** (centered column, gap 26px):
  - H1 "Svep. Matcha. / Börja jobba." – 92px / 800, line-height .98, letter-spacing -0.035em, line break after "Matcha."
  - Paragraph "Jobbsvep visar jobb som passar din profil. Svep höger på det du gillar så skickas din ansökan direkt." – 20px, line-height 1.5, max-width 580px.
  - Primary CTA "Skapa konto gratis" – accent bg, white, radius 999px, padding 20px 40px, 19px/700.
  - Secondary search pill: bg `rgba(255,255,255,.14)`, border `1px solid rgba(255,255,255,.3)`, radius 999px, padding 6px 6px 6px 22px: "Eller sök direkt:" · **Yrke** · **Ort** + white "Sök" pill button.
- **Steps row** (3-column grid, gap 40px, padding 0 120px 56px, 15px/1.45):
  1. "1. Skapa din profil" – "Erfarenhet och vad du söker, på fem minuter."
  2. "2. Svep bland jobben" – "Höger för att ansöka, vänster för att gå vidare."
  3. "3. Matcha och prata" – "Vill arbetsgivaren träffa dig öppnas en chatt."
  Titles 17px/700; body at 85% opacity.

### 2. Swipe view – desktop (1280×800)
- **Layout:** CSS grid `320px 1fr`, bg `#fbf9f7`.
- **Left sidebar** (bg #fff, border-right 1px #ebe5e1):
  - Top bar (padding 20px 24px, bottom border): logo "jobbsvep" 24px/800 + avatar circle 34px (#ede8e4, initials "EL", 13px/700).
  - "Nya matchningar" (15px/700) + row of 60px circle avatars with 3px accent ring (unread) or 3px #ebe5e1 ring (read); label 12px below. Items: VE Vinga, KC Kvarn, BL Brygga.
  - "Meddelanden" list: 44px avatar, name 15px/700, time 12px #6e6460, preview 14px; rows padding 12px 0, divider 1px #ebe5e1.
    - Vinga Energi · 10:42 · "Hej Elin! Har du tid för ett samtal på torsdag?"
    - Kvarn & Co · Igår · "Tack för din ansökan! Vi återkommer."
- **Main column** (centered, gap 20px, padding-top 20px):
  - Search/filter pill: bg #fff, border 1px #ebe5e1, radius 999px: "Alla jobb · Stockholm · Heltid" (15px/600, dots #c4bbb5) + dark "Filter" pill (#1d1715, white text).
  - **Job card** 440×560, radius 24px, shadow `0 18px 44px rgba(29,23,21,.2)`, full-bleed workplace photo.
    - Top-left badge: white pill "{match} % matchning", 14px/700, accent-dark text, padding 7px 12px.
    - Bottom info area: gradient `linear-gradient(to top, rgba(29,23,21,.92) 60%, transparent)`, padding 80px 26px 26px, white text, gap 8px:
      - 32px white circle with company initials (12px/800) + company name 15px/600
      - Job title 40px/800, line-height 1, letter-spacing -0.02em
      - Salary 17px/600
      - "{ort} · {arbetsplats} · Start {start}" 15px at 85% opacity
    - Swipe stamps (appear while dragging): "JA" (left, accent bg, rotate -12°) and "NEJ" (right, #1d1715 bg, rotate 12°); 30px/800, 3px white border, radius 8px. Opacity = clamp(|dx| / 110, 0, 1).
  - **Action buttons** (gap 20px): ✕ skip (64px white circle, shadow `0 6px 18px rgba(29,23,21,.15)`), "Spara" (50px white circle, 12px/600), ✓ apply (64px accent circle, white glyph 24px).
  - **Toast** (top of main): dark pill #1d1715, white 14px/600, e.g. "Ansökan skickad till Norrsken Studio" or "{titel} sparad". Auto-hides after 2.2s.

### 3. Swipe view – mobile (390×844)
- Status bar, then header (padding 8px 20px 12px): logo 24px/800 + pill "Stockholm · Filter" (white, border 1px #ddd5d0, 14px/600).
- Card 354×540, radius 22px, same content as desktop at smaller sizes (title 32px, salary 15px, meta 14px, badge 13px).
- Action buttons overlap the card bottom by 30px: ✕ 62px, Spara 48px, ✓ 62px accent.
- Bottom tab bar (bg #fff, top border #ebe5e1, 12px/600, color #6e6460, active = accent-dark): **Svepa**, Sök, Matchningar, Profil.

### 4. Match screen – mobile (and desktop overlay)
- Full-screen accent background, white text, centered.
- "Det är en match!" – 46px/800 mobile (72px desktop), letter-spacing -0.03em.
- Two overlapping avatar circles 96px (120px desktop): user "EL" (white bg, dark text) and company initials (#1d1715 bg), 4px accent border, overlap -20px.
- Text: "{Företag} vill gärna prata med dig om rollen som {titel}." 17px (20px desktop), line-height 1.5.
- Mobile static screen also shows: "Snabbsvar" label, quick-reply chips ("Hej! Tack för matchningen.", "När passar en intervju?") on `rgba(255,255,255,.16)`, message input pill (white, placeholder "Skriv ett meddelande…", accent "Skicka" button), and a "Fortsätt svepa" text link.
- Interactive overlay version: buttons "Skicka ett meddelande" (white bg, accent text, 54–56px tall pill) and "Fortsätt svepa" (1.5px white outline pill).

## Interactions & Behavior
- **Drag to swipe:** pointer down on the card captures the pointer; on move, `dx = clientX - startX`, `dy = (clientY - startY) * 0.4`; transform `translate(dx, dy) rotate(dx/18 deg)`, no transition while dragging.
- **Release:** `dx > 110` → apply; `dx < -110` → skip; otherwise spring back (`transform .28s ease`).
- **Buttons:** ✕ = skip (fly left to -900px), ✓ = apply (fly right to +900px), Spara = fly up (-900px). Fly-out animation `transform .28s ease`; after 280ms advance to next job and reset the card with no transition.
- **Match:** when applying to a job with match ≥ 85 %, show the match overlay instead of a toast (in production this should come from the employer side / backend). Both overlay buttons close it in the prototype; "Skicka ett meddelande" should navigate to the chat.
- **Toast:** shown after apply/save, auto-hides after 2200ms.
- **Keyboard (recommended for production):** ← skip, → apply, ↑ save.
- **Responsive:** mobile layout below ~768px; desktop sidebar from ~1024px.
- Respect `prefers-reduced-motion` (skip the fly-out animation).

## State Management
- `currentIndex` – position in the job queue
- `drag: { dx, dy, active }` – card drag offset
- `animating: boolean` – whether transform transitions are on
- `toast: string | null`
- `match: Job | null` – opens match overlay
- Data: job queue (paged from API, filtered by search/filters), matches list, message threads.
- Actions to API: `applyToJob(id)`, `skipJob(id)`, `saveJob(id)`.

### Job data shape (from prototype)
```ts
type Job = {
  title: string; company: string; ini: string;   // logo initials fallback
  place: string; mode: 'Hybrid' | 'På plats' | 'Distans';
  type: 'Heltid' | 'Deltid'; salary: string; match: number;  // 0–100
  start: string; posted: string; desc: string;
  reqs: string[]; perks: string[]; size: string;
  logoUrl?: string; photoUrl?: string;
};
```
Sample jobs are in the `JOBS` array in `source/Jobbsvep 2b.dc.html`.

## Design Tokens
**Colors**
- Accent (indigo): `oklch(0.55 0.18 275)` ≈ `#5b4fd6`
- Accent dark (text on white): `oklch(0.48 0.18 275)` ≈ `#4a3ec2`; button text on white `oklch(0.45 0.18 275)`
- Ink: `#1d1715`
- Muted text: `#6e6460`; secondary text `#4a413c`
- Background: `#fbf9f7`; surface `#ffffff`; subtle `#ede8e4`
- Border/divider: `#ebe5e1`, `#ddd5d0`
- Landing overlay: `rgba(20,16,24,.55)`
- Card info gradient: `rgba(29,23,21,.92)` → transparent

**Typography:** Onest (Google Fonts), weights 400/500/600/700/800.
Scale: 92 / 72 / 46 / 40 / 32 / 26 / 24 / 20 / 17 / 15 / 14 / 13 / 12px. Display sizes use letter-spacing -0.02 to -0.035em and line-height ~1.

**Radius:** cards 22–24px; pills/buttons 999px; stamps 8px.
**Shadows:** card `0 18px 44px rgba(29,23,21,.2)` (mobile `0 14px 34px rgba(29,23,21,.18)`); round buttons `0 6px 18px rgba(29,23,21,.15)`.
**Spacing:** mostly 6 / 8 / 10 / 12 / 14 / 18 / 20 / 24 / 26 / 32 / 56px.

## Assets
- No icon set; glyphs ✕ and ✓ are text characters (swap for the codebase's icon library).
- All photos and logos are placeholders: workplace photo per job, company logo (initials fallback), landing hero photo.
- Font: Onest via Google Fonts.

## Files
- `Jobbsvep-2b-standalone.html` – self-contained interactive prototype
- `source/Jobbsvep 2b.dc.html` – source (markup + logic + sample data)
- `source/support.js` – runtime needed to open the source file

## Not yet designed
Job detail, chat thread, profile/CV, onboarding, filter sheet. Follow the same tokens and components when building them.
