"""Check every evidence item in data/topics/topics.json against PubMed (same rules as the region evidence), and check
that every region id a step names exists.   python -X utf8 -I tools/check_topics.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from verify_evidence import check_item  # noqa: E402

T = json.load(open(os.path.join(ROOT, 'data', 'topics', 'topics.json'), encoding='utf-8'))
RID = {r['id'] for r in json.load(open(os.path.join(ROOT, 'data', 'regions_index.json'), encoding='utf-8'))}
bad = n = 0
for t in T:
    for k, s in enumerate(t['steps']):
        for rid in s.get('rs', []):
            if rid not in RID:
                bad += 1
                print('unknown region', t['id'], k, rid)
        for j, it in enumerate(s.get('ev', [])):
            n += 1
            for rid in it.get('also', []):
                if rid not in RID:
                    bad += 1
                    print('unknown also-region', rid)
            if len(it.get('claim', '')) > 110:
                print('long claim (%d): %s' % (len(it['claim']), it['claim']))
            errs = check_item(it, '%s step %d item %d' % (t['id'], k + 1, j + 1))
            for e in errs:
                bad += 1
                print(e)
        txt = json.dumps(s, ensure_ascii=False)
        if '—' in txt or '–' in txt:
            bad += 1
            print('dash in', t['id'], k)
print('%d items checked, %d problems' % (n, bad))
