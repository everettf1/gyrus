"""Neurotransmitter receptor and transporter maps for the atlas (2026-11-20) -> data/chem.json.
PET maps from Hansen et al. 2022, Nat Neurosci 25:1569 (github.com/netneurolab/hansen_receptors, CC BY-NC-SA 4.0),
each a group average from the original study listed in MAPS. For every map: values on the cortex surface (lh, rh),
on the slice grid (3 mm, same grid as the probability maps), a mean per deep structure, and the regions with the
highest density. Colors are scaled within the cortex and within deep structures separately (p2 to p98).
python -X utf8 -I data/build_chem.py"""
import base64
import gzip
import json
import os
import warnings

import nibabel as nib
import numpy as np
from scipy import ndimage

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
PET = os.path.join(HERE, 'cache', 'pet')
geo = json.load(open(os.path.join(HERE, 'atlas_geometry.json'), encoding='utf-8'))
ex = json.load(open(os.path.join(HERE, 'extras.json'), encoding='utf-8'))
REG = json.load(open(os.path.join(HERE, 'regions_index.json'), encoding='utf-8'))

# id, file, label, what it is, tracer, N, source study
MAPS = [
    ('D1', 'D1_SCH23390_hc13_kaller.nii', 'D1 receptor', '[11C]SCH23390', 13, 'Kaller et al. 2017'),
    ('D2', 'D2_fallypride_hc49_jaworska.nii', 'D2 receptor', '[18F]fallypride', 49, 'Jaworska et al. 2020'),
    ('DAT', 'DAT_fpcit_hc174_dukart_spect.nii', 'dopamine transporter (DAT)', '[123I]FP-CIT SPECT', 174, 'Dukart et al. 2018'),
    ('5HT1a', '5HT1a_way_hc36_savli.nii', '5-HT1A receptor', '[11C]WAY-100635', 36, 'Savli et al. 2012'),
    ('5HT2a', '5HT2a_cimbi_hc29_beliveau.nii', '5-HT2A receptor', '[11C]Cimbi-36', 29, 'Beliveau et al. 2017'),
    ('SERT', '5HTT_dasb_hc100_beliveau.nii', 'serotonin transporter (SERT)', '[11C]DASB', 100, 'Beliveau et al. 2017'),
    ('NET', 'NAT_MRB_hc77_ding.nii.gz', 'noradrenaline transporter (NET)', '[11C]MRB', 77, 'Ding et al. 2010'),
    ('VAChT', 'VAChT_feobv_hc18_aghourian_sum.nii', 'vesicular acetylcholine transporter (VAChT)', '[18F]FEOBV', 18, 'Aghourian et al. 2017'),
    ('M1', 'M1_lsn_hc24_naganawa.nii.gz', 'M1 muscarinic receptor', '[11C]LSN3172176', 24, 'Naganawa et al. 2021'),
    ('A4B2', 'A4B2_flubatine_hc30_hillmer.nii.gz', 'alpha4beta2 nicotinic receptor', '[18F]flubatine', 30, 'Hillmer et al. 2016'),
    ('mGluR5', 'mGluR5_abp_hc73_smart.nii', 'mGluR5 receptor', '[11C]ABP688', 73, 'Smart et al. 2019'),
    ('NMDA', 'NMDA_ge179_hc29_galovic.nii.gz', 'NMDA receptor', '[18F]GE-179', 29, 'Galovic et al. 2021'),
    ('GABAa', 'GABAa-bz_flumazenil_hc16_norgaard.nii', 'GABA-A receptor (benzodiazepine site)', '[11C]flumazenil', 16, 'Norgaard et al. 2021'),
    ('H3', 'H3_cban_hc8_gallezot.nii.gz', 'H3 histamine receptor', '[11C]GSK189254', 8, 'Gallezot et al. 2017'),
    ('CB1', 'CB1_omar_hc77_normandin.nii.gz', 'CB1 cannabinoid receptor', '[11C]OMAR', 77, 'Normandin et al. 2015'),
    ('MOR', 'MU_carfentanil_hc204_kantonen.nii', 'mu-opioid receptor', '[11C]carfentanil', 204, 'Kantonen et al. 2020'),
]


BAR_ROWS = [('Caudate', 'caudate_nucleus', 'd'), ('Putamen', 'putamen', 'd'), ('Nucleus accumbens', 'nucleus_accumbens', 'd'),
            ('Globus pallidus', 'globus_pallidus', 'd'), ('Thalamus', 'thalamus', 'd'), ('Hypothalamus', 'hypothalamus', 'd'),
            ('Amygdala', 'amygdala', 'd'), ('Hippocampus', 'hippocampus', 'd'), ('Midbrain', 'midbrain', 'd'), ('Pons', 'pons', 'd'),
            ('Cerebellum', 'cerebellum', 'd'), ('Frontal cortex', 'frontal_lobe', 'c'), ('Insula', 'insula', 'c'),
            ('Temporal cortex', 'temporal_lobe', 'c'), ('Parietal cortex', 'parietal_lobe', 'c'), ('Occipital cortex', 'occipital_lobe', 'c')]
NET_NAMES = {'Vis': 'Visual', 'SomMot': 'Somatomotor', 'DorsAttn': 'Dorsal attention', 'SalVentAttn': 'Salience', 'Limbic': 'Limbic',
             'Cont': 'Control', 'Default': 'Default mode'}
# reference region the tracer was measured against (Hansen 2022, Table S3); it reads near zero by definition
REF = {'D1': 'cerebellum', 'D2': 'cerebellum', 'DAT': 'occipital cortex', '5HT1a': 'cerebellum', '5HT2a': 'cerebellum', 'SERT': 'cerebellum',
       'NET': 'occipital cortex', 'M1': 'cerebellum', 'mGluR5': 'cerebellum', 'MOR': 'occipital cortex'}


def gz64(a):
    return base64.b64encode(gzip.compress(np.ascontiguousarray(a).tobytes(), 9)).decode('ascii')


def unb64(s, dt):
    return np.frombuffer(base64.b64decode(s), dtype=dt)


def ungz(s, dt):
    return np.frombuffer(gzip.decompress(base64.b64decode(s)), dtype=dt)


def lookup(data, aff, xyz):
    ijk = nib.affines.apply_affine(np.linalg.inv(aff), xyz)
    return ndimage.map_coordinates(data, ijk.T, order=1, mode='constant', cval=np.nan)


# cortex vertices with inward normals
VX = {}
for H in ('lh', 'rh'):
    c = geo['cortex'][H]
    pos = unb64(c['pial'], np.int16).reshape(-1, 3).astype(np.float64) * 0.1
    faces = unb64(c['faces'], np.uint16 if c['faceType'] == 'u16' else np.uint32).reshape(-1, 3).astype(np.int64)
    fn = np.cross(pos[faces[:, 1]] - pos[faces[:, 0]], pos[faces[:, 2]] - pos[faces[:, 0]])
    vn = np.zeros_like(pos)
    for k in range(3):
        np.add.at(vn, faces[:, k], fn)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-9
    import scipy.sparse as sp
    n_ = len(pos)
    ii = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2], faces[:, 1], faces[:, 2], faces[:, 0]])
    jj = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0], faces[:, 0], faces[:, 1], faces[:, 2]])
    A = sp.csr_matrix((np.ones(len(ii)), (ii, jj)), shape=(n_, n_))
    A.data[:] = 1
    ADJ = globals().setdefault('ADJ', {})
    ADJ[H] = A + sp.identity(n_)
    VX[H] = {'pos': pos, 'nrm': vn, 'label': unb64(c['label'], np.uint8), 'hcp': unb64(c['hcp'], np.uint8), 'net': unb64(c['net'], np.uint8)}
medial_wall = geo['destrieux_labels'].index('Medial_wall')

# MRI-grid label volume (deep structures)
g = ex['grid']
dims = g['dims']
gx, gy, gz = [g['origin'][k] + g['spacing'] * np.arange(dims[k]) for k in range(3)]
G = np.stack(np.meshgrid(gx, gy, gz, indexing='ij'), -1).reshape(-1, 3)
lab = np.transpose(ungz(ex['labels'], np.uint8).reshape(dims[2], dims[1], dims[0]), (2, 1, 0)).reshape(-1)
BASES = ex['label_bases']
# coarse slice grid (same as the probability maps)
pg = ex['prob_grid']
cdims = pg['dims']
CG = np.stack(np.meshgrid(*[pg['origin'][k] + pg['spacing'] * np.arange(cdims[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
cg_lab = lookup(np.transpose(ungz(ex['labels'], np.uint8).reshape(dims[2], dims[1], dims[0]), (2, 1, 0)).astype(np.float32),
                np.array([[g['spacing'], 0, 0, g['origin'][0]], [0, g['spacing'], 0, g['origin'][1]], [0, 0, g['spacing'], g['origin'][2]], [0, 0, 0, 1]]), CG)
mri = np.transpose(ungz(ex['mri'], np.uint8).reshape(dims[2], dims[1], dims[0]), (2, 1, 0)).astype(np.float32)
mri_aff = np.array([[g['spacing'], 0, 0, g['origin'][0]], [0, g['spacing'], 0, g['origin'][1]], [0, 0, g['spacing'], g['origin'][2]], [0, 0, 0, 1]])
cg_brain = lookup(mri, mri_aff, CG) > 12

LIDX = {n: i for i, n in enumerate(geo['destrieux_labels'])}
HIDX = {n: i for i, n in enumerate(geo['hcp_labels'])}
NIDX = {n: i for i, n in enumerate(geo['net_labels'])}


def region_vertices(r, H):
    v = VX[H]
    if r.get('cortex'):
        return np.where(np.isin(v['label'], [LIDX[x] for x in r['cortex']]))[0]
    if r.get('hcp'):
        return np.where(np.isin(v['hcp'], [HIDX[x] for x in r['hcp']]))[0]
    return np.zeros(0, int)


AGG = {'prefrontal_cortex', 'basal_ganglia', 'striatum', 'cerebellum', 'limbic_lobe'}
out = {'maps': [], 'source': 'Hansen et al. 2022, Nat Neurosci 25:1569; PET group averages from the studies named per map.'}
for mid, fname, label, tracer, n, study in MAPS:
    img = nib.load(os.path.join(PET, fname))
    d = np.asarray(img.dataobj, dtype=np.float32)
    if d.ndim == 4:
        d = d[..., 0]
    d[~np.isfinite(d)] = 0
    # cortex: average over the cortical ribbon (0.5 to 2.5 mm under the pial surface)
    cv = {}
    for H in ('lh', 'rh'):
        v = VX[H]
        vals = np.nanmean([lookup(d, img.affine, v['pos'] - v['nrm'] * t) for t in (1.0, 2.0, 3.0)], axis=0)
        ok = np.isfinite(vals) & (v['label'] != medial_wall)
        x = np.where(ok, vals, 0.0)
        w = ok.astype(float)
        for _ in range(12):      # smooth along the surface so folds do not show up as speckle
            x = ADJ[H] @ x
            w2 = ADJ[H] @ w
            x = np.where(w2 > 0, x / np.maximum(w2, 1e-9), 0) * (w2 > 0)
            w = (w2 > 0).astype(float)
        vals = np.where(v['label'] == medial_wall, np.nan, x)
        cv[H] = vals
    allc = np.concatenate([cv['lh'], cv['rh']])
    c_lo, c_hi = np.nanpercentile(allc, 2), np.nanpercentile(allc, 98)
    # deep structures: mean inside each label
    gvals = lookup(d, img.affine, G)
    base_mean = {}
    for k, b in enumerate(BASES):
        m = lab == k + 1
        if m.sum() >= 3:
            base_mean[b] = float(np.nanmean(gvals[m]))
    dv = np.array([x for x in base_mean.values() if np.isfinite(x)])
    d_lo, d_hi = np.percentile(dv, 2), np.percentile(dv, 98)
    sc = lambda x, lo, hi: np.clip(np.nan_to_num((x - lo) / max(1e-9, hi - lo)), 0, 1)
    ent = {'id': mid, 'label': label, 'tracer': tracer, 'n': n, 'study': study,
           'lh': gz64(np.round(sc(cv['lh'], c_lo, c_hi) * 255).astype(np.uint8)),
           'rh': gz64(np.round(sc(cv['rh'], c_lo, c_hi) * 255).astype(np.uint8)),
           'deep': {b: int(round(float(sc(v, d_lo, d_hi)) * 255)) for b, v in base_mean.items() if np.isfinite(v)}}
    # slice grid: cortex scale outside labelled structures, deep scale inside them
    cvals = lookup(d, img.affine, CG)
    grid = np.where(cg_lab > 0.5, sc(cvals, d_lo, d_hi), sc(cvals, c_lo, c_hi))
    grid[~cg_brain] = 0
    ent['grid'] = gz64(np.round(grid * 255).astype(np.uint8))
    # highest-density regions (raw means), cortical areas and deep structures separately
    cort = []
    for r in REG:
        if r['id'] in AGG or r['deck'] not in ('areas', 'gyri'):
            continue
        vals = np.concatenate([cv[H][region_vertices(r, H)] for H in ('lh', 'rh')])
        if len(vals) > 20 and np.isfinite(vals).any():
            cort.append((float(np.nanmean(vals)), r['id']))
    deep = []
    for r in REG:
        if r['id'] in AGG or not r.get('deep') or r['deck'] == 'tracts':
            continue
        vals = [base_mean[b] for b in r['deep'] if b in base_mean and np.isfinite(base_mean[b])]
        if vals:
            deep.append((float(np.mean(vals)), r['id']))
    cort.sort(reverse=True)
    deep.sort(reverse=True)
    ent['top_cortex'] = [x[1] for x in cort[:5]]
    ent['top_deep'] = [x[1] for x in deep[:5]]
    ent['ratio'] = round(float(np.mean([x[0] for x in deep[:3]]) / max(1e-6, np.nanmean(allc))), 1) if deep else None
    # chart numbers: mean per structure on one scale (percent of the highest), and per cortical network
    RID = {r['id']: r for r in REG}

    def rmean(rid):
        r = RID.get(rid)
        if not r:
            return None
        if r.get('deep'):
            vs = [base_mean[b] for b in r['deep'] if b in base_mean and np.isfinite(base_mean[b])]
            return float(np.mean(vs)) if vs else None
        vs = np.concatenate([cv[H][region_vertices(r, H)] for H in ('lh', 'rh')])
        return float(np.nanmean(vs)) if len(vs) > 20 and np.isfinite(vs).any() else None

    rows = [(lab_, rmean(rid), kind) for lab_, rid, kind in BAR_ROWS]
    rows = [(l_, max(0.0, v), k) for l_, v, k in rows if v is not None]
    top = max([v for _, v, _ in rows] + [1e-9])
    ent['bars'] = [[l_, int(round(100 * v / top)), k] for l_, v, k in rows]
    nets = []
    for ni, nl in enumerate(geo['net_labels']):
        if ni == 0:
            continue
        vs = np.concatenate([cv[H][VX[H]['net'] == ni] for H in ('lh', 'rh')])
        if np.isfinite(vs).any():
            nets.append((NET_NAMES.get(nl, nl), max(0.0, float(np.nanmean(vs)))))
    ntop = max([v for _, v in nets] + [1e-9])
    ent['nets'] = [[l_, int(round(100 * v / ntop))] for l_, v in nets]
    ent['ref'] = REF.get(mid, '')
    out['maps'].append(ent)
    print(f'{mid:7s} cortex {c_lo:.2f}-{c_hi:.2f}  deep top {ent["top_deep"][:3]}  cortex top {ent["top_cortex"][:3]}  ratio {ent["ratio"]}')
out['grid'] = pg
json.dump(out, open(os.path.join(HERE, 'chem.json'), 'w', encoding='utf-8'), separators=(',', ':'))
print('wrote chem.json', round(os.path.getsize(os.path.join(HERE, 'chem.json')) / 1e6, 2), 'MB')
