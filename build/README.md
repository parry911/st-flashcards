# How the S&T deck is built

1. Fetch the Notion page "SCIENCE AND TECH" and save its text as `page.md`.
2. `python3 units.py` gives every piece of text an id (u1, u2, ...) in page order.
3. `spec/*.txt` arranges those ids into cards (one job per card). `python3 arrange.py`
   builds `deck.json` and stops if any piece is missing or used twice.
4. `python3 coverage.py` checks every page line is on a card word for word.
5. `python3 make.py` writes the site (`index.html`); diagrams live in `img/`.

If the page changes, unit ids shift: re-run `units.py` and update the spec before building.
Card ids are `topic:role-title`; keep them stable so progress is kept.

# Environment & DM deck (build/env/)

Same method, own folder. Fetch the Notion page "ENVIRONMENT NOTES" and save its text as `env/page_raw.md`, then in `env/`:
`python3 prep.py` (lifts PYQ toggles, pinned lines, EIA sub-heads) → `python3 units.py` → `python3 arrange.py` (spec/01–06.txt) →
`python3 coverage.py` → `python3 make_env.py` (writes the site page with both decks; S&T data is taken from the live page).
Extra spec syntax: `uN/+` turns Perry's "+" joins into line breaks (one point shown as a list), `uN/+1.3` only those joins,
`!N` makes join N start a new point, `uN/++` makes every join a new point,
`aN` / `!aN` = break at the Nth arrow '→' (line break / new point); a doubled '+ +' counts as one join.
No list may exceed 5 items: `arrange.py` prints any list it had to cut automatically (should be 0).
Helpers: `review.py s0N` (lines with numbered joins), `apply.py spec/0N.txt 'uN=/+…'`, `qa.py s0N W` (question + back),
`setq.py 'card-id=question'`. Question fronts live in `env/fronts/*.txt`; prose cards in `env/read_in_notion.txt`. `show.py` and `peek.py` help read units and cards.
A rebuild of the S&T deck with `make.py` keeps the Environment deck (it reads `env/site_deck.json`).
