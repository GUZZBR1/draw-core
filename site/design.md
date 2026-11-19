# Draw — Design System

This file is the visual source of truth for the Draw website. Keep new pages and changes aligned with these decisions.

## Brand

Draw is a bridge from a person’s paper sketch to digital tools that can interpret, model, and test the idea. The site should feel thoughtful, precise, calm, and ambitious: editorial typography with a light studio interface.

## Color and surfaces

- Light canvas: warm off-white `#f7f7f4`.
- Ink: soft near-black `#22231f`.
- Muted text: `#777870`.
- Accent: pale paper yellow `#e7dfa1`, used sparingly for highlights and interaction feedback.
- Dark mode uses the existing CSS variables; components must inherit them instead of hard-coding light colors.
- Glass surfaces use a translucent paper tint, a fine ink border, restrained shadow, and backdrop blur. Keep enough tint for text behind a card to become unreadable.
- Prefer rounded pills for compact controls and softly rounded cards for content. Avoid boxed rules and decorative borders that interrupt the editorial page flow.

## Typography

- Sans: Manrope, with the existing system fallbacks. Use it for headlines, body copy, and interface labels where a clean reading voice is needed.
- Mono: DM Mono, with the existing system fallbacks. Use it for navigation, metadata, small status labels, and the Vision page's editorial text.
- Serif italics are reserved for the short editorial accent in the Product headline. Do not apply italics or bold to whole paragraphs.
- Definition card: a restrained medium-weight sans title; small mono part-of-speech label; readable, regular-weight sans definition; muted secondary line. Italicize only the part-of-speech word.
- Do not add a new font family without updating this system and getting an explicit design reason.

## Header and motion

- Keep `Draw` centered in the header as the page scrolls. It begins as the large home-page wordmark and settles into the compact header position without jumping.
- The navigation becomes a narrow, light glass surface while scrolling: subtle blur, fine border, soft shadow, and a shorter height.
- The header, centered wordmark, and definition card must remain legible and within the viewport at browser zoom and at 320 px CSS width.
- Hover feedback should be small and clear: a fine underline, slight color change, or a one-pixel lift. Avoid jitter, looping motion, and pointer-driven movement of content. The one exception is the webcam's red recording dot, which blinks only while the pointer or keyboard focus is on the webcam and stops (steady red under reduced motion) when it leaves.
- The definition opens from the Draw wordmark only. It stays open while the pointer moves from the wordmark onto the card and closes when moving to Product or another control.
- The custom page scrubber is a visible, compact glass capsule with a readable track and thumb. Keep pointer dragging and keyboard navigation; do not reduce it to a tiny line.
- Respect reduced-motion preferences.
- The Product construction illustration is rendered as colored ASCII symbols on a canvas, using the same glyph-ranking approach as the Vision portrait. On entry its symbols appear from the top down, scattered, slowly over about 4.6 s, then the artwork stays still. Do not animate or parallax it afterward. Reduced-motion users see it at once.

## Definition card

- The Draw definition appears only when hovering or keyboard-focusing the Draw mark in the shared header, on every route.
- Keep the glass card centered beneath the mark, readable at compact and large viewport sizes, with no scaling tied to the wordmark size.
- The card copy should describe the paper-to-digital idea in plain language and retain enough detail to communicate the vision. The card does not belong in the Vision page body.

## Page composition

- Home places a still archive of consequential human drawings around the centered Draw wordmark. Keep the artifacts static, make each one link to its primary or archival source, and preserve room around the wordmark. Add a small webcam SVG perched on the final “w”; fade it as the wordmark settles into the compact header. Hovering or focusing the webcam opens a matching glass card that explains its role in live capture. Place that card to the wordmark’s right on desktop and below it on narrow screens, clear of the page scrubber. Keep the webcam card separate from the Draw definition card. On narrow screens, move the archive below the first-screen mark. On load, trace each archive frame as a stroke in staggered order, then let the frame's paper, artwork, and caption fade in from a blur. Let the Draw wordmark emerge from depth on first load: it starts small, blurred, and pushed back, then settles forward to full size and sharpness over about 1.3 s. On hover or focus, an archive frame grows about 4.5% and gains a soft shadow beneath it (no growth under reduced motion). Reduced-motion users see everything at once.
- Below the home archive, provide a full-viewport, edge-to-edge drawing sheet. Keep a compact floating glass toolbar for pen, eraser, color, stroke width, and one clear-all action. The sheet must remain free of cards, inset margins, and secondary action rows. Store strokes in normalized coordinates so resize does not distort them, use coalesced pointer events, and cap canvas pixel ratio to keep memory use predictable. Offer four stroke sizes (fine, medium, thick, and a very large one). Show the area the pen or eraser will cover as a round highlighter-yellow (`--accent`) preview under the pointer, and flash it briefly at the sheet's center when the size or tool changes.
- Vision is an uninterrupted editorial page: a large centered Manrope headline (medium weight, tight tracking, matching the Product headline), readable centered mono paragraphs, and a quiet mono sign-off. A local canvas renders a Sailor Moon inspired portrait as ASCII above the headline; her eyes open on entry, blink, and wink while separate waves move through the twin tails. On entry the portrait is not drawn as a stroke: its symbols appear from the top down, scattered, over about three seconds, and only then do the eyes and hair begin to move. Taper the portrait's lower silhouette so it does not end in a rectangular crop. Type the headline and copy in one measured reading order, with the full copy immediately available to assistive technology and reduced-motion users. If the reader keeps scrolling down (about 260 px of wheel, touch, or key intent, which resets after a brief pause), stop typing and let the remaining copy emerge from a blur with a 640 ms fade, leaving typed text untouched. Reduced-motion users get the full copy immediately. Do not insert a dictionary card, eyebrow, or horizontal rules into the Vision copy.
- Product uses the shared pill style for its construction status, a centered ASCII illustration that settles still after its entry, a clear headline, and concise explanatory copy.
- Use whitespace for hierarchy. Keep the pages minimal and avoid adding sections or labels that were not requested.

## Interaction and responsive behavior

- Navigation links and controls need visible hover and keyboard-focus states.
- The location label is not a link. On hover or keyboard focus, “São Paulo, Brazil” lifts slightly and a hairline divider with “São José dos Campos” fades in beneath it.
- Keep the location label's response restrained on desktop. On narrow layouts, prioritize the centered wordmark and prevent overlap with the theme control.
- Theme changes must work on every route and preserve contrast.
- Test critical header/card layouts at desktop width, 640 px, and 320 px, including while the home wordmark is transitioning on scroll.
- Switching theme cuts the page diagonally: a thin hand-drawn line is written from the top-left corner to the bottom-right corner in the new theme, then opens out on both sides to reveal the whole new theme (about 1.1 s, View Transitions API). Reduced-motion and unsupported browsers switch instantly.
