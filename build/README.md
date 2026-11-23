# How the S&T deck is built

1. Fetch the Notion page "SCIENCE AND TECH" and save its text as `page.md`.
2. `python3 units.py` gives every piece of text an id (u1, u2, ...) in page order.
3. `spec/*.txt` arranges those ids into cards (one job per card). `python3 arrange.py`
   builds `deck.json` and stops if any piece is missing or used twice.
4. `python3 coverage.py` checks every page line is on a card word for word.
5. `python3 make.py` writes the site (`index.html`); diagrams live in `img/`.

If the page changes, unit ids shift: re-run `units.py` and update the spec before building.
Card ids are `topic:role-title`; keep them stable so progress is kept.
