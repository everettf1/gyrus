"""QA pass 1 (no browser): integrity of everything embedded in dist/index.html.
python -X utf8 -I tools/qa_data.py [--doi]     writes shots/qa_data.json and prints a summary
Checks: every region has its text fields, a way to be drawn, valid links to other regions, evidence items with all
fields, figure files on disk and in the published files map; text hygiene (dashes, doubled spaces, stray tokens);
name and alias collisions; the tours; the receptor maps. --doi also asks doi.org whether each DOI exists."""
import collections
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'dist', 'index.html'), encoding='utf-8').read()


def embedded(i):
    m = re.search(r'<script id="%s" type="application/json">(.*?)</script>' % i, html, re.S)
    return json.loads(m.group(1)) if m else None


D = embedded('atlas-data')
CH = embedded('atlas-chem')
TP = embedded('atlas-topics')
EXTRA = embedded('atlas-extra')
REG = D['regions']
GEO = D['geometry']
issues = collections.defaultdict(list)


def add(kind, msg):
    issues[kind].append(msg)


ids = {r['id'] for r in REG}
deep = GEO['deep']
dlab, hlab, nlab = set(GEO['destrieux_labels']), set(GEO['hcp_labels']), set(GEO['net_labels'])
TEXT = ('hint', 'summary', 'where', 'does', 'connects', 'clinical', 'remember', 'how_we_know')
BAD = re.compile(r'[—–]|\bTODO\b|\bTBD\b|lorem|undefined|\bNaN\b|\[citation|\?\?\?|\bXXX\b')


def hygiene(where, s):
    if not isinstance(s, str):
        return
    if BAD.search(s):
        add('text: dash or stray token', '%s: %s' % (where, BAD.search(s).group(0)))
    if '  ' in s.strip():
        add('text: doubled space', where)
    if re.search(r'\s[,.;:](\s|$)', s):
        add('text: space before punctuation', '%s: ...%s' % (where, re.search(r'.{0,20}\s[,.;:](\s|$)', s).group(0)))
    if s.count('(') != s.count(')'):
        add('text: unbalanced parentheses', where)
    if s.strip() and s.strip()[-1] not in '.?!)"”' and where.split('.')[-1] in ('summary', 'where', 'does', 'connects', 'clinical', 'remember', 'how_we_know', 'finding', 'x', 'limit'):
        add('text: no final period', '%s: ...%s' % (where, s.strip()[-30:]))


figs_on_disk = set(os.listdir(os.path.join(ROOT, 'dist', 'fig'))) if os.path.isdir(os.path.join(ROOT, 'dist', 'fig')) else set()
fmap = json.load(open(os.path.join(ROOT, 'data', 'figures', 'files_map.json'), encoding='utf-8'))
fig_used = set()
dois, pm_seen = {}, collections.Counter()


def check_ev(where, it, stim=False):
    need = ('effect', 'method', 'cite', 'pmid', 'quote') if stim else ('kind', 'claim', 'finding', 'quote', 'pmid', 'cite', 'year')
    for f in need:
        if not it.get(f):
            add('evidence: missing field', '%s lacks %s' % (where, f))
    if not stim and len(it.get('claim', '')) > 110:
        add('evidence: claim over 110 chars', '%s (%d)' % (where, len(it['claim'])))
    for f in ('claim', 'finding', 'effect', 'cite'):
        hygiene('%s.%s' % (where, f), it.get(f))
    if it.get('doi'):
        dois.setdefault(it['doi'], where)
    elif not stim:
        add('evidence: no DOI', where)
    pm_seen[str(it.get('pmid'))] += 1
    d = it.get('data')
    if d:
        if not d.get('items') or len(d['items']) < 2:
            add('chart: fewer than 2 bars', where)
        for row in d.get('items', []):
            if not isinstance(row[1], (int, float)):
                add('chart: non-numeric value', where)
            if len(str(row[0])) > 28:
                add('chart: label over 28 chars', '%s: %s' % (where, row[0]))
    fg = it.get('fig')
    if fg:
        fn = fg.get('src', '').split('/')[-1]
        fig_used.add(fn)
        if fn not in figs_on_disk:
            add('figure: file missing on disk', '%s -> %s' % (where, fn))
        if 'fig/' + fn not in fmap:
            add('figure: not in the published files map', fn)
        for f in ('caption', 'short'):
            if not fg.get(f):
                add('figure: missing ' + f, where)
        hygiene(where + '.fig.caption', fg.get('caption'))
        hygiene(where + '.fig.notice', fg.get('notice'))


names = collections.defaultdict(list)
norm = lambda s: re.sub(r'[^a-z0-9]', '', str(s).lower())
per_deck = collections.Counter()
for r in REG:
    rid = r['id']
    per_deck[r.get('deck')] += 1
    for f in TEXT:
        if not r.get(f):
            add('region: missing ' + f, rid)
        else:
            hygiene('%s.%s' % (rid, f), r[f])
    if not r.get('facts'):
        add('region: no facts', rid)
    for x in r.get('facts', []):
        hygiene(rid + '.facts', x)
    if not r.get('quiz'):
        add('region: no quiz questions', rid)
    for q in r.get('quiz', []):
        hygiene(rid + '.quiz', q.get('q'))
        if norm(r['name']) and norm(r['name']) in norm(q.get('q', '')):
            add('quiz: question contains the answer', '%s: %s' % (rid, q.get('q', '')[:90]))
    if not r.get('refs'):
        add('region: no textbook refs', rid)
    if not r.get('evidence'):
        add('region: no evidence cards', rid)
    for k, it in enumerate(r.get('evidence', [])):
        check_ev('%s.ev%d' % (rid, k + 1), it)
    kinds = {it.get('kind') for it in r.get('evidence', [])}
    if r.get('stimulation'):
        check_ev(rid + '.stim', r['stimulation'], True)
    for x in r.get('see_also', []):
        if x not in ids:
            add('region: see_also points nowhere', '%s -> %s' % (rid, x))
    # can it be drawn?
    drawn = False
    for lab in r.get('cortex', []) or []:
        drawn = True
        if lab not in dlab:
            add('geometry: unknown cortex label', '%s: %s' % (rid, lab))
    for lab in r.get('hcp', []) or []:
        drawn = True
        if lab not in hlab:
            add('geometry: unknown HCP area', '%s: %s' % (rid, lab))
    if r.get('net'):
        drawn = True
        for lab in (r['net'] if isinstance(r['net'], list) else [r['net']]):
            if lab not in nlab:
                add('geometry: unknown network', '%s: %s' % (rid, lab))
    for b in r.get('deep', []) or []:
        drawn = True
        if not any(k == b or k == b + '_l' or k == b + '_r' for k in deep):
            add('geometry: deep mesh missing', '%s: %s' % (rid, b))
    if not drawn:
        add('geometry: region has nothing to draw', rid)
    for a in [r['name']] + list(r.get('aliases', [])):
        names[norm(a)].append(rid)
    if len(r.get('hint', '')) > 120:
        add('region: hint over 120 chars', '%s (%d)' % (rid, len(r['hint'])))
for k, v in names.items():
    if len(set(v)) > 1:
        add('names: same accepted answer for two regions', '%s -> %s' % (k, sorted(set(v))))

# tours
for T in TP or []:
    for k, s in enumerate(T['steps']):
        w = '%s.step%d' % (T['id'], k + 1)
        for f in ('n', 'x', 'limit'):
            hygiene('%s.%s' % (w, f), s.get(f))
        if not s.get('ev'):
            add('tour: step without evidence', w)
        for rid in s.get('rs', []):
            if rid not in ids:
                add('tour: unknown region', '%s: %s' % (w, rid))
        for j, it in enumerate(s.get('ev', [])):
            check_ev('%s.ev%d' % (w, j + 1), it)
# receptor maps
for m in (CH or {}).get('maps', []):
    for f in ('lh', 'rh', 'deep', 'bars', 'nets', 'top_deep', 'top_cortex', 'tracer', 'study'):
        if not m.get(f):
            add('receptor map: missing ' + f, m['id'])
    for x in m.get('top_deep', []) + m.get('top_cortex', []):
        if x not in ids:
            add('receptor map: unknown region in top list', '%s: %s' % (m['id'], x))
# figures on disk that nothing uses, and map entries without files
for fn in sorted(figs_on_disk - fig_used):
    add('figure: on disk but unused', fn)
for k, v in fmap.items():
    if not os.path.exists(os.path.join(ROOT, v)):
        add('figure: files map entry without a file', k)

if '--doi' in sys.argv:
    bad = 0
    for i, (doi, where) in enumerate(sorted(dois.items())):
        try:
            req = urllib.request.Request('https://doi.org/api/handles/' + urllib.parse.quote(doi, safe='/'), headers={'User-Agent': 'atlas-qa/1.0'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                js = json.loads(resp.read())
            if js.get('responseCode') != 1:
                add('DOI: not found at doi.org', '%s (%s)' % (doi, where))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                add('DOI: not found at doi.org', '%s (%s)' % (doi, where))
            else:
                add('DOI: could not check', '%s HTTP %s' % (doi, e.code))
        except Exception as e:
            add('DOI: could not check', '%s %s' % (doi, type(e).__name__))
        time.sleep(0.08)

out = {k: v for k, v in sorted(issues.items())}
json.dump(out, open(os.path.join(ROOT, 'shots', 'qa_data.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('regions %d %s' % (len(REG), dict(per_deck)))
print('evidence items on regions %d, stimulation %d, tour items %d, figures used %d, DOIs %d' % (
    sum(len(r.get('evidence', [])) for r in REG), sum(1 for r in REG if r.get('stimulation')), sum(len(s.get('ev', [])) for T in TP for s in T['steps']), len(fig_used), len(dois)))
for k, v in out.items():
    print('%4d  %s' % (len(v), k))
    for x in v[:6]:
        print('        ', str(x)[:170])
