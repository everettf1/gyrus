"""Build dist/index.html from src/app.html + data (geometry, regions index, content files).

Run:  python -X utf8 -I build.py
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "app.html")
DATA = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "dist")
OUT = os.path.join(OUT_DIR, "index.html")

TEXT_FIELDS = ("hint", "summary", "where", "does", "connects", "clinical", "remember", "how_we_know")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from verify_evidence import check_item  # noqa: E402  (PubMed check; cached)
EV_STATS = {"kept": 0, "dropped": 0}


def good_items(e, rid):
    out = []
    for i, it in enumerate(e.get("evidence") or []):
        if not isinstance(it, dict):
            continue
        errs = check_item(it, "%s evidence %d" % (rid, i + 1))
        if errs:
            EV_STATS["dropped"] += 1
            print("  drop:", errs[0][:150])
            continue
        EV_STATS["kept"] += 1
        out.append({k: (clean(v) if k in ("claim", "finding", "cite") else v) for k, v in it.items()})
    return out


def good_stim(e, rid):
    st = e.get("stimulation")
    if not isinstance(st, dict) or not st.get("effect"):
        return None
    errs = check_item(st, "%s stimulation" % rid)
    if errs:
        EV_STATS["dropped"] += 1
        print("  drop:", errs[0][:150])
        return None
    EV_STATS["kept"] += 1
    return {k: (clean(v) if k in ("effect", "cite", "method") else v) for k, v in st.items()}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clean(s):
    """No em or en dashes anywhere in the UI copy."""
    if not isinstance(s, str):
        return s
    return (
        s.replace(" \u2014 ", ", ").replace("\u2014", ", ").replace(" \u2013 ", " to ").replace("\u2013", "-")
    )


def main():
    geometry = load(os.path.join(DATA, "atlas_geometry.json"))
    regions = load(os.path.join(DATA, "regions_index.json"))
    by_id = {r["id"]: r for r in regions}

    def akey(s):
        return "".join(ch for ch in str(s).lower() if ch.isalnum())

    claimed = {}
    for r0 in regions:  # names and aliases set in regions_index win over aliases added by content files
        for a0 in [r0["name"]] + list(r0.get("aliases", [])):
            claimed.setdefault(akey(a0), r0["id"])
    merged_files = []
    covered = set()
    for path in sorted(glob.glob(os.path.join(DATA, "content", "*.json"))) + sorted(glob.glob(os.path.join(DATA, "evidence", "*.json"))):
        try:
            entries = load(path)
        except Exception as e:  # a half-written file must not break the build
            print("skip %s: %s" % (os.path.basename(path), e))
            continue
        if isinstance(entries, dict):
            entries = list(entries.values()) if "id" not in entries else [entries]
        n = 0
        for e in entries:
            if not isinstance(e, dict) or e.get("id") not in by_id:
                print("  unknown id in %s: %r" % (os.path.basename(path), (e or {}).get("id") if isinstance(e, dict) else e))
                continue
            r = by_id[e["id"]]
            for k in TEXT_FIELDS:
                if e.get(k):
                    r[k] = clean(e[k])
            if e.get("facts"):
                r["facts"] = [clean(x) for x in e["facts"] if x]
            if e.get("quiz"):
                r["quiz"] = [
                    {"q": clean(q.get("q", "")), "type": q.get("type", "function")}
                    for q in e["quiz"]
                    if isinstance(q, dict) and q.get("q")
                ]
            if e.get("refs"):
                r["refs"] = sorted({int(x) for x in e["refs"] if str(x).isdigit() and 1 <= int(x) <= 13})
            if e.get("evidence"):
                ev = good_items(e, r["id"])
                if ev:
                    r["evidence"] = ev
            if e.get("stimulation"):
                st = good_stim(e, r["id"])
                if st:
                    r["stimulation"] = st
            if e.get("see_also"):
                r["see_also"] = [x for x in e["see_also"] if x in by_id and x != r["id"]]
            al = list(r.get("aliases", []))
            for a in e.get("aliases", []) or []:
                a = clean(a).lower()
                if a and a not in al and a != r["name"].lower():
                    owner = claimed.get(akey(a))
                    if owner and owner != r["id"]:
                        print("  alias %r skipped on %s (belongs to %s)" % (a, r["id"], owner))
                        continue
                    claimed[akey(a)] = r["id"]
                    al.append(a)
            r["aliases"] = al
            covered.add(r["id"])
            n += 1
        merged_files.append("%s:%d" % (os.path.basename(path), n))

    # evidence tours (data/topics/topics.json): every item is checked against PubMed like the region evidence
    topics = []
    tp = os.path.join(DATA, "topics", "topics.json")
    if os.path.exists(tp):
        import shutil
        ntop = ntfig = 0
        tfig = {}  # figures chosen for tour cards: sel entries whose region is t_<topic>_<step number>
        for sp in sorted(glob.glob(os.path.join(DATA, "figures", "sel_*.json"))):
            try:
                for s_ in load(sp):
                    if str(s_.get("region", "")).startswith("t_") and s_.get("file") and os.path.exists(os.path.join(DATA, "figures", "img", s_["file"])):
                        tfig[(s_["region"], str(s_["pmid"]))] = s_
            except Exception as e:
                print("skip %s: %s" % (os.path.basename(sp), e))
        os.makedirs(os.path.join(OUT_DIR, "fig"), exist_ok=True)
        for T in load(tp):
            for k, s in enumerate(T.get("steps", [])):
                good = []
                for j, it in enumerate(s.get("ev", [])):
                    errs = check_item(it, "%s step %d item %d" % (T["id"], k + 1, j + 1))
                    if errs:
                        print("  drop:", errs[0][:150])
                        continue
                    ntop += 1
                    item = {kk: (clean(v) if kk in ("claim", "finding", "cite") else v) for kk, v in it.items() if kk != "also"}
                    prior = sum(1 for g in good if str(g.get("pmid")) == str(it.get("pmid")))  # same paper earlier in this step
                    fs = tfig.get(("t_%s_%d%s" % (T["id"], k + 1, "b" if prior == 1 else ""), str(it.get("pmid")))) if prior < 2 else None
                    if fs:
                        item["fig"] = {"src": "fig/" + fs["file"], "caption": clean(fs.get("caption", "")), "notice": clean(fs.get("notice", "")),
                                       "from": fs.get("from", ""), "short": clean(fs.get("short", "")), "license": fs.get("license", "")}
                        shutil.copyfile(os.path.join(DATA, "figures", "img", fs["file"]), os.path.join(OUT_DIR, "fig", fs["file"]))
                        ntfig += 1
                    good.append(item)
                    for rid in it.get("also", []):  # the same card also goes on that region's own page
                        r = by_id.get(rid)
                        if r is not None and not any(str(x.get("pmid")) == str(it.get("pmid")) for x in r.get("evidence", [])):
                            r.setdefault("evidence", []).append(dict(item))
                s["ev"] = good
                for f in ("n", "x", "limit"):
                    if s.get(f):
                        s[f] = clean(s[f])
                if s.get("list"):
                    s["list"] = [clean(x) for x in s["list"]]
            topics.append(T)
        print("topic evidence items kept: %d, with a figure: %d" % (ntop, ntfig))

    # figures chosen from the papers (data/figures/sel_*.json), images in data/figures/img, copied to dist/fig
    import shutil
    figdir = os.path.join(DATA, "figures")
    nfig = 0
    os.makedirs(os.path.join(OUT_DIR, "fig"), exist_ok=True)
    for sp in sorted(glob.glob(os.path.join(figdir, "sel_*.json"))):
        try:
            sels = load(sp)
        except Exception as e:
            print("skip %s: %s" % (os.path.basename(sp), e))
            continue
        for s in sels:
            r = by_id.get(s.get("region"))
            src = os.path.join(figdir, "img", s.get("file", ""))
            if not r or not s.get("file") or not os.path.exists(src):
                continue
            fig = {"src": "fig/" + s["file"], "caption": clean(s.get("caption", "")), "notice": clean(s.get("notice", "")),
                   "from": s.get("from", ""), "short": clean(s.get("short", "")), "license": s.get("license", "")}
            target = None
            for it in r.get("evidence", []):
                if str(it.get("pmid")) == str(s.get("pmid")) and "fig" not in it:
                    target = it
                    break
            if target is None and r.get("stimulation") and str(r["stimulation"].get("pmid")) == str(s.get("pmid")) and "fig" not in r["stimulation"]:
                target = r["stimulation"]
            if target is None:
                continue
            target["fig"] = fig
            shutil.copyfile(src, os.path.join(OUT_DIR, "fig", s["file"]))
            nfig += 1
    print("figures attached: %d" % nfig)
    pending = [r["id"] for r in regions if r["id"] not in covered]
    regions = [r for r in regions if r["id"] in covered]  # regions still being written stay out of the page
    for r in regions:
        r["see_also"] = [x for x in r.get("see_also", []) if x in covered]
    print("left out until written: %d %s" % (len(pending), " ".join(pending[:8]) + (" ..." if len(pending) > 8 else "")))
    payload = json.dumps({"made_by": "Everett Freeman", "geometry": geometry, "regions": regions}, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")

    with open(SRC, encoding="utf-8") as f:
        html = f.read()
    tag = '<script id="atlas-data" type="application/json">' + payload + "</script>"
    xp = os.path.join(DATA, "extras.json")
    if os.path.exists(xp):
        with open(xp, encoding="utf-8") as f:
            extra = f.read().replace("</", "<\\/")
        tag += '\n<script id="atlas-extra" type="application/json">' + extra + "</script>"
    cp = os.path.join(DATA, "chem.json")
    if os.path.exists(cp):
        chem = load(cp)
        chem["maps"] = [{k: v for k, v in m.items() if k != "grid"} for m in chem["maps"]]
        tag += '\n<script id="atlas-chem" type="application/json">' + json.dumps(chem, separators=(",", ":")).replace("</", "<\\/") + "</script>"
    if topics:
        tag += '\n<script id="atlas-topics" type="application/json">' + json.dumps(topics, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"
    if "<!--ATLAS_DATA-->" in html:
        html = html.replace("<!--ATLAS_DATA-->", tag, 1)
    else:  # fall back: put it right before the first module script
        i = html.index('<script type="module"')
        html = html[:i] + tag + "\n" + html[i:]

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    size = os.path.getsize(OUT)
    print("content: %s" % (", ".join(merged_files) or "none"))
    print("regions with content: %d / %d" % (len(covered), len(regions)))
    print("evidence items kept %d, dropped %d; regions with evidence %d, with stimulation %d" % (EV_STATS["kept"], EV_STATS["dropped"], sum(1 for r in regions if r.get("evidence")), sum(1 for r in regions if r.get("stimulation"))))
    print("wrote %s (%.2f MB)" % (OUT, size / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
