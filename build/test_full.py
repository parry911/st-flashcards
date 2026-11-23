import asyncio, json, re, time
from playwright.async_api import async_playwright

URL = 'http://localhost:8765/index.html'
D = json.load(open('/home/claude/st/deck.json'))
NCARDS = sum(len(t['cards']) for t in D['topics'])
results = []
def check(name, ok, info=''):
    results.append((name, bool(ok), info)); print(('PASS ' if ok else 'FAIL ') + name + (f'  [{info}]' if info else ''))

GS3_STATE = {"v": 2, "type": "all", "line": "GS3.1", "part": "all", "mode": "order", "missed": False, "queue": ["x"], "pos": 0, "st": {"tl01-planning:define0": {"seen": 3, "miss": 1, "s": "k", "t": 1}}, "back": False}
GS3_SYNC = {"token": "ghp_TESTTOKEN", "gist": "g123", "dev": "gs3dev"}

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await b.new_context(viewport={'width': 1478, 'height': 900})
        # ---- mocked GitHub gist API ----
        gist = {"id": "g123", "description": "GS3 flashcards progress (used by the flashcard site; do not delete)",
                "files": {"v3-dev-gs3dev.json": {"content": json.dumps({"v": 2, "st": {"tl01-planning:define0": ["k", 3, 1, 1, ""]}})}}}
        calls = []
        async def gh(route):
            req = route.request; calls.append((req.method, req.url))
            if req.method == 'GET' and re.search(r'/gists\?', req.url):
                await route.fulfill(json=[{"id": gist["id"], "description": gist["description"]}]); return
            if req.method == 'GET' and req.url.endswith('/gists/g123'):
                await route.fulfill(json=gist); return
            if req.method == 'PATCH':
                body = json.loads(req.post_data)
                for k, v in body['files'].items(): gist['files'][k] = {"content": v['content']}
                await route.fulfill(json=gist); return
            await route.fulfill(status=404, json={})
        await ctx.route('https://api.github.com/**', gh)
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'favicon' not in m.text and '404' not in m.text else None)
        # seed GS3 deck data on the same site before first open
        await pg.goto('http://localhost:8765/blank.html')
        await pg.evaluate("""([a,b])=>{localStorage.setItem('gs3deck.v3',a); localStorage.setItem('gs3sync.v3',b);}""", [json.dumps(GS3_STATE), json.dumps(GS3_SYNC)])
        await pg.goto(URL); await pg.wait_for_timeout(800)
        check('loads without errors', not errs, '; '.join(errs))
        txt = await pg.inner_text('.legend')
        check('all cards counted', f'{NCARDS} new' in txt, txt)
        kick = await pg.inner_text('.kicker')
        check('card counter shows total', f'/ {NCARDS}' in kick, kick)
        # token copied from GS3 settings
        sy = json.loads(await pg.evaluate("localStorage.getItem('stsync.v1')"))
        check('sync key copied from GS3 deck', sy and sy['token'] == 'ghp_TESTTOKEN' and sy['dev'] != 'gs3dev', str(sy))
        # pinned box visible on wide screen, beside the card
        box = await pg.locator('#pin').bounding_box(); card = await pg.locator('.card').bounding_box()
        vis = await pg.locator('#pin .lead').is_visible()
        check('pinned box beside card (wide)', vis and box['x'] > card['x'] + card['width'], f"pin x={box['x']:.0f} card right={card['x']+card['width']:.0f}")
        await pg.mouse.wheel(0, 2000); await pg.wait_for_timeout(200)
        box2 = await pg.locator('#pin').bounding_box()
        check('pinned box stays put when scrolling', abs(box2['y'] - box['y']) < 2, f"{box['y']:.0f}->{box2['y']:.0f}")
        pintext = await pg.inner_text('#pin')
        for w in ['any new tech would have these problems', 'Adaptability', 'digital divide', 'tech savvy', 'interoperability', 'risk (social, privacy, power etc.)', 'if tech is really niche then ethical concerns especially if biotech related', 'Vigyan Dhara']:
            if w not in pintext: check('pin text ' + w, False)
        check('pin holds every issue head + Vigyan Dhara', all(w in pintext for w in ['Adaptability', 'interoperability', 'biotech related', 'Vigyan Dhara']))

        # ---- walk every card in page order: flip, open every row one by one, grade ----
        bad = []; t0 = time.time()
        for n in range(NCARDS):
            cid = await pg.evaluate("JSON.parse(localStorage.getItem('stdeck.v1')).queue[JSON.parse(localStorage.getItem('stdeck.v1')).pos]")
            await pg.keyboard.press('Space'); await pg.wait_for_timeout(260)
            rows = await pg.locator('.rw').count()
            card = next(c for t in D['topics'] for c in t['cards'] if c['id'] == cid)
            exp = sum(1 for r in card['rows'] if 't' in r)
            if rows != exp: bad.append(f'{cid}: {rows} rows shown, {exp} expected')
            for k in range(exp):
                await pg.keyboard.press('Space')
            opened = await pg.locator('.rw.s2').count()
            if opened != exp: bad.append(f'{cid}: opened {opened}/{exp}')
            secs = await pg.locator('.sec').count(); exps = sum(1 for r in card['rows'] if 'sec' in r)
            if secs != exps: bad.append(f'{cid}: {secs} headings shown, {exps} expected')
            vids = await pg.locator('a.vid').count(); expv = sum(1 for r in card['rows'] if 'video' in r)
            if vids != expv: bad.append(f'{cid}: videos {vids}/{expv}')
            await pg.keyboard.press('2' if n % 5 else '1')
        check(f'every card opens with all its points ({NCARDS} cards, {time.time()-t0:.0f}s)', not bad, '; '.join(bad[:5]))
        check('no errors during the walk', not errs, '; '.join(errs[:3]))
        done = await pg.inner_text('#stage')
        check('end-of-round screen', 'round 1 complete' in done.lower() and 'still missed' in done, done[:80])
        st = json.loads(await pg.evaluate("localStorage.getItem('stdeck.v1')"))
        nk = sum(1 for v in st['st'].values() if v.get('s') == 'k'); nm = sum(1 for v in st['st'].values() if v.get('s') == 'm')
        check('grades saved', nk + nm == NCARDS and nm == len(range(0, NCARDS, 5)), f'known {nk} missed {nm}')
        # review missed
        await pg.click('#revMiss'); await pg.wait_for_timeout(200)
        q = json.loads(await pg.evaluate("localStorage.getItem('stdeck.v1')"))['queue']
        check('review missed = only missed cards', len(q) == nm and all(st['st'][i]['s'] == 'm' for i in q), str(len(q)))
        # red mark blocks Got it
        await pg.keyboard.press('Space'); await pg.wait_for_timeout(150)
        await pg.keyboard.press('a'); await pg.wait_for_timeout(100)
        if await pg.locator('.rw.s2').count():
            await pg.locator('.rw.s2').first.click(); await pg.wait_for_timeout(100)
            dis = await pg.locator('#actions [data-a="got"]').is_disabled()
            check('red point blocks Got it', dis and await pg.locator('.rw.fg').count() == 1)
            await pg.locator('.rw.fg').first.click(); await pg.wait_for_timeout(100)
            check('tap again undoes red', await pg.locator('.rw.fg').count() == 0)
        # ---- sync: wrote own file only, GS3 file untouched ----
        await pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        await pg.wait_for_timeout(3500)
        stf = [k for k in gist['files'] if k.startswith('st-dev-')]
        check('sync writes its own st-dev file', len(stf) == 1, str(list(gist['files'])))
        check("GS3 gist file untouched", json.loads(gist['files']['v3-dev-gs3dev.json']['content'])['st'] == {"tl01-planning:define0": ["k", 3, 1, 1, ""]})
        if stf:
            doc = json.loads(gist['files'][stf[0]]['content'])
            check('synced progress has every graded card', len(doc['st']) == NCARDS, str(len(doc['st'])))
        gs3 = json.loads(await pg.evaluate("localStorage.getItem('gs3deck.v3')"))
        check('GS3 progress on this device untouched', gs3 == GS3_STATE)
        check('GS3 sync settings untouched', json.loads(await pg.evaluate("localStorage.getItem('gs3sync.v3')")) == GS3_SYNC)
        # ---- second device merges from the gist ----
        ctx2 = await b.new_context(viewport={'width': 390, 'height': 844})
        await ctx2.route('https://api.github.com/**', gh)
        p2 = await ctx2.new_page(); e2 = []; p2.on('pageerror', lambda e: e2.append(str(e)))
        await p2.goto('http://localhost:8765/blank.html')
        await p2.evaluate("""(b)=>localStorage.setItem('gs3sync.v3',b)""", json.dumps({"token": "ghp_TESTTOKEN", "gist": "g123", "dev": "phone1"}))
        await p2.goto(URL); await p2.wait_for_timeout(3500)
        st2 = json.loads(await p2.evaluate("localStorage.getItem('stdeck.v1')"))
        check('second device picks up progress through sync', sum(1 for v in st2['st'].values() if v.get('s')) == NCARDS, str(len(st2['st'])))
        # phone: pinned box collapsed to one line, opens on tap
        op = await p2.locator('#pin').get_attribute('open')
        one = await p2.inner_text('#pinOne')
        await p2.click('#pin summary'); await p2.wait_for_timeout(150)
        op2 = await p2.locator('#pin').get_attribute('open')
        check('phone: issue heads bar collapsed, opens on tap', op is None and op2 is not None and 'Adaptability' in one, one[:60])
        await p2.screenshot(path='/home/claude/st/shot_phone_pin_open.png')
        check('phone: no errors', not e2, '; '.join(e2))
        await ctx2.close()

        # ---- dropdowns, modes, missed only, progress sheet, reset ----
        await pg.select_option('#subjSel', 's05'); await pg.wait_for_timeout(150)
        opts = await pg.locator('#topicSel option').all_inner_texts()
        exp_topics = [t['name'] for t in D['topics'] if t['subj'] == 's05']
        check('subject menu fills topic menu', opts[1:] == [re.sub(r'<[^>]+>', '', x) for x in exp_topics], str(opts[:4]))
        q = json.loads(await pg.evaluate("localStorage.getItem('stdeck.v1')"))['queue']
        exp_ids = [c['id'] for t in D['topics'] if t['subj'] == 's05' for c in t['cards']]
        check('subject limits the deck, page order', q == exp_ids, f'{len(q)} vs {len(exp_ids)}')
        tid = [t for t in D['topics'] if t['subj'] == 's05'][1]['id']
        await pg.select_option('#topicSel', tid); await pg.wait_for_timeout(150)
        q = json.loads(await pg.evaluate("localStorage.getItem('stdeck.v1')"))['queue']
        check('topic limits the deck', q == [c['id'] for t in D['topics'] if t['id'] == tid for c in t['cards']], str(q[:2]))
        await pg.select_option('#subjSel', 'all'); await pg.wait_for_timeout(150)
        for mode in ['topics', 'all', 'smart', 'order']:
            await pg.click(f'#modeSeg button[data-v="{mode}"]'); await pg.wait_for_timeout(150)
            q = json.loads(await pg.evaluate("localStorage.getItem('stdeck.v1')"))['queue']
            ok = sorted(q) == sorted(c['id'] for t in D['topics'] for c in t['cards'])
            if mode == 'order': ok = ok and q == [c['id'] for t in D['topics'] for c in t['cards']]
            if mode == 'topics':
                # each topic's cards stay together; missed topics first
                order = []; [order.append(i.split(':')[0]) for i in q if not order or order[-1] != i.split(':')[0]]
                ok = ok and len(order) == len(set(order))
            check(f'mode {mode}', ok, str(len(q)))
        await pg.click('#missTgl'); await pg.wait_for_timeout(150)
        q = json.loads(await pg.evaluate("localStorage.getItem('stdeck.v1')"))['queue']
        st = json.loads(await pg.evaluate("localStorage.getItem('stdeck.v1')"))['st']
        check('Missed only', q and all(st[i]['s'] == 'm' for i in q), str(len(q)))
        await pg.click('#missTgl'); await pg.wait_for_timeout(100)
        await pg.click('#progBtn'); await pg.wait_for_timeout(150)
        pls = await pg.locator('#pbox .pl').count()
        check('progress sheet lists 13 subjects + all', pls == 14, str(pls))
        await pg.screenshot(path='/home/claude/st/shot_progress.png')
        await pg.locator('#pbox .pl').nth(9).click(); await pg.wait_for_timeout(150)
        check('progress sheet jumps to a subject', await pg.input_value('#subjSel') == 's09')
        await pg.select_option('#subjSel', 'all'); await pg.wait_for_timeout(100)
        # keep place on reload
        await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(100)
        before = await pg.inner_text('.kicker')
        await pg.reload(); await pg.wait_for_timeout(600)
        check('reopens on the same card', await pg.inner_text('.kicker') == before, before)
        await pg.click('#resetBtn'); await pg.click('#mOk'); await pg.wait_for_timeout(200)
        st = json.loads(await pg.evaluate("localStorage.getItem('stdeck.v1')"))
        check('reset clears S&T progress only', st['st'] == {} and json.loads(await pg.evaluate("localStorage.getItem('gs3deck.v3')")) == GS3_STATE)
        check('no errors overall', not errs, '; '.join(errs[:3]))
        await b.close()
    print('\n%d passed, %d failed' % (sum(r[1] for r in results), sum(not r[1] for r in results)))

asyncio.run(main())
