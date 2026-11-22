"""Check every content entry: coverage, required fields, style rules, see_also ids and alias collisions.
python -X utf8 -I tools/check_content.py"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
idx = {r['id']: r for r in json.load(open(os.path.join(HERE, 'data', 'regions_index.json'), encoding='utf-8'))}
seen = {}
for f in glob.glob(os.path.join(HERE, 'data', 'content', '*.json')):
    for e in json.load(open(f, encoding='utf-8')):
        seen[e['id']] = (os.path.basename(f), e)
print('content entries', len(seen), '| missing', [i for i in idx if i not in seen], '| unknown ids', [i for i in seen if i not in idx])
bad = []
words = 0
for i, (f, e) in seen.items():
    words += len(' '.join(str(e.get(k, '')) for k in ('where', 'does', 'connects', 'clinical', 'remember')).split())
    blob = json.dumps(e, ensure_ascii=False)
    for pat in ['—', '–', r'\bcrucial\b', r'\bdelve', r'\bfascinating', r'it is important to note', r'\bkey\b', r'in essence', r'!']:
        if re.search(pat, blob, flags=re.I):
            bad.append((i, pat))
    for k in ('hint', 'where', 'does', 'connects', 'clinical', 'remember', 'facts', 'quiz'):
        if not e.get(k):
            bad.append((i, 'missing ' + k))
    for s in e.get('see_also', []):
        if s not in idx:
            bad.append((i, 'see_also ' + s))
owner = {}
for i, (f, e) in seen.items():
    for a in set([idx[i]['name']] + [x.lower() for x in e.get('aliases', [])] + [x.lower() for x in idx[i]['aliases']]):
        owner.setdefault(re.sub(r'[^a-z0-9]', '', a), set()).add(i)
coll = {a: sorted(s) for a, s in owner.items() if len(s) > 1}
print('style/field problems', len(bad), bad[:30])
print('alias collisions', json.dumps(coll, indent=0))
print('total teaching words', words)
