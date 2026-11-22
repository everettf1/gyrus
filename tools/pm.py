"""PubMed helper for writing evidence.
  python -X utf8 -I tools/pm.py find queries.txt      one query per line -> top hits (pmid | year | journal | title)
  python -X utf8 -I tools/pm.py show 123 456 ...       cached abstract text, without the author-affiliation block
Uses the same cache as verify_evidence.py, so anything shown here is what the checker will compare quotes against."""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_evidence import fetch  # noqa: E402

EU = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'


def get(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'atlas-evidence/1.0'}), timeout=40) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception:
            time.sleep(1.5 * (k + 1))
    return ''


def find(q, n=3):
    j = get(EU + 'esearch.fcgi?db=pubmed&retmode=json&retmax=%d&sort=relevance&term=%s' % (n, urllib.parse.quote(q)))
    try:
        ids = json.loads(j)['esearchresult']['idlist']
    except Exception:
        return []
    if not ids:
        return []
    time.sleep(0.4)
    s = get(EU + 'esummary.fcgi?db=pubmed&retmode=json&id=' + ','.join(ids))
    out = []
    try:
        res = json.loads(s)['result']
        for i in ids:
            d = res[i]
            out.append((i, d.get('pubdate', '')[:4], d.get('source', ''), (d.get('sortfirstauthor') or ''), d.get('title', '')[:120]))
    except Exception:
        pass
    return out


def show(pmid):
    txt = fetch(pmid) or ''
    txt = re.sub(r'\nAuthor information:.*?(?=\n\n)', '', txt, flags=re.S)
    txt = re.sub(r'\n(Copyright|©|Comment in|Erratum in|Conflict of interest|PMCID|Update of|Republished).*?(?=\n\n|\Z)', '', txt, flags=re.S)
    return txt.strip()


if __name__ == '__main__':
    if sys.argv[1] == 'find':
        for q in open(sys.argv[2], encoding='utf-8').read().splitlines():
            q = q.strip()
            if not q or q.startswith('#'):
                continue
            print('Q', q)
            for h in find(q):
                print('   ', ' | '.join(h))
            time.sleep(0.4)
    else:
        for p in sys.argv[2:]:
            print('=' * 8, p)
            print(show(p))
            time.sleep(0.35)
