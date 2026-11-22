"""Check evidence files against PubMed. Every evidence item and stimulation entry must carry a PMID and a quote that
appears word for word in that PubMed record (title + abstract); every number in a `data` chart must appear in the
quote; the year must match. Abstracts are cached in data/cache/pubmed/<pmid>.txt.

  python -X utf8 -I tools/verify_evidence.py data/evidence/E1.json [more files]     -> prints a report, exit 1 on failures
  python -X utf8 -I tools/verify_evidence.py --all                                   -> every data/evidence/*.json and
                                                                                       data/content/N*.json
"""
import glob
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'data', 'cache', 'pubmed')
os.makedirs(CACHE, exist_ok=True)
UA = {'User-Agent': 'brain-atlas-check/1.0'}


def fetch(pmid):
    p = os.path.join(CACHE, f'{pmid}.txt')
    if os.path.exists(p) and os.path.getsize(p) > 50:
        return open(p, encoding='utf-8').read()
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&rettype=abstract&retmode=text'
    for attempt in range(4):
        try:
            time.sleep(0.4)
            txt = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode('utf-8', 'replace')
            if txt.strip():
                open(p, 'w', encoding='utf-8').write(txt)
                return txt
        except Exception as e:  # rate limit or network: wait and retry
            time.sleep(2 + attempt * 2)
    return ''


def norm(s):
    s = unicodedata.normalize('NFKC', str(s))
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    s = re.sub(r'[‐-―−]', '-', s)
    s = s.replace('±', '+/-').replace('×', 'x')
    s = re.sub(r'\s+', ' ', s).strip().lower()
    s = re.sub(r'\s*([(),;:%=<>/-])\s*', r'\1', s)
    return s


def num_forms(v):
    out = set()
    try:
        f = float(v)
    except Exception:
        return {norm(v)}
    if f == int(f):
        out.add(str(int(f)))
        out.add(f'{int(f):,}')
    for d in (1, 2, 3):
        out.add(f'{f:.{d}f}')
        out.add(f'{f:.{d}f}'.lstrip('0') if abs(f) < 1 else f'{f:.{d}f}')
    out.add(repr(f))
    return out


def check_item(it, where):
    errs = []
    pmid = str(it.get('pmid', '')).strip()
    q = it.get('quote', '')
    if not pmid.isdigit():
        return [f'{where}: no PMID']
    if not q or len(q) < 20:
        return [f'{where}: no quote']
    txt = fetch(pmid)
    if not txt:
        return [f'{where}: PMID {pmid} not found on PubMed']
    nt = norm(txt)
    if norm(q) not in nt:
        # allow a quote that skips a sentence break: every sentence of it must be in the record
        parts = [p for p in re.split(r'(?<=[.;])\s+', q) if len(p) > 12]
        if not parts or not all(norm(p) in nt for p in parts):
            errs.append(f'{where}: quote not found in PMID {pmid}: "{q[:90]}"')
    y = it.get('year')
    if y and str(y) not in txt[:1500]:
        errs.append(f'{where}: year {y} not in PMID {pmid} header')
    d = it.get('data')
    if d:
        nq = norm(q)
        for row in d.get('items', []):
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                errs.append(f'{where}: bad data row {row}')
                continue
            if not any(f in nq for f in num_forms(row[1])):
                errs.append(f'{where}: chart value {row[1]} ({row[0]}) is not in the quote')
    return errs


def check_file(path):
    data = json.load(open(path, encoding='utf-8'))
    if isinstance(data, dict):
        data = [data]
    errs, n = [], 0
    for e in data:
        rid = e.get('id', '?')
        for i, it in enumerate(e.get('evidence') or []):
            n += 1
            errs += check_item(it, f'{rid} evidence {i + 1}')
        st = e.get('stimulation')
        if st:
            n += 1
            errs += check_item(st, f'{rid} stimulation')
    return n, errs


if __name__ == '__main__':
    files = sys.argv[1:]
    if files == ['--all']:
        files = sorted(glob.glob(os.path.join(ROOT, 'data', 'evidence', '*.json')) + glob.glob(os.path.join(ROOT, 'data', 'content', 'N*.json')))
    bad = 0
    for f in files:
        try:
            n, errs = check_file(f)
        except Exception as ex:
            print(f'{os.path.basename(f)}: cannot read ({ex})')
            bad += 1
            continue
        print(f'{os.path.basename(f)}: {n} items, {len(errs)} problems')
        for e in errs:
            print('  ' + e)
        bad += len(errs)
    sys.exit(1 if bad else 0)
