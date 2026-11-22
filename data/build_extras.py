"""Extras for the atlas (2026-11-19): real MRI for the cut view, a structure label volume, NeuroQuery function scores,
Julich probability maps, and arterial territories. Writes data/extras.json (gzip + base64 blobs, decoded in the page).

Sources
- MRI: MNI152 2009 template (nilearn load_mni152_template, 1 mm), resampled to 1.5 mm and cropped to the brain.
- Labels: the same atlases the 3D meshes come from (Harvard-Oxford, AAL3, Pauli 2018, Juelich), on the MRI grid.
- Function: NeuroQuery (Dockes et al. 2020, eLife 9:e53385), one predicted map per term, averaged in each region.
- Probability: Juelich histological atlas probability maps (Eickhoff et al. 2005), 10 post-mortem brains.
- Territories: Liu et al. 2023 Johns Hopkins arterial territories atlas (CC BY-SA 4.0), level 1, plus its border zones.
python -X utf8 -I data/build_extras.py
"""
import base64
import gzip
import json
import os
import warnings

import nibabel as nib
import numpy as np
from nilearn import datasets
from scipy import ndimage

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
C1 = os.path.join(HERE, 'nilearn_data')
C2 = os.path.join(HERE, 'cache')
geo = json.load(open(os.path.join(HERE, 'atlas_geometry.json'), encoding='utf-8'))
REG = json.load(open(os.path.join(HERE, 'regions_index.json'), encoding='utf-8'))


def gz64(a):
    return base64.b64encode(gzip.compress(np.ascontiguousarray(a).tobytes(), 9)).decode('ascii')


def unb64(s, dt):
    return np.frombuffer(base64.b64decode(s), dtype=dt)


def lookup(img_data, img_aff, xyz, order=0):
    """value of a volume at MNI points (nearest or linear)"""
    ijk = nib.affines.apply_affine(np.linalg.inv(img_aff), xyz)
    if order == 0:
        ijk = np.rint(ijk).astype(int)
        ok = np.all((ijk >= 0) & (ijk < np.array(img_data.shape[:3])), axis=1)
        out = np.zeros(len(xyz), img_data.dtype)
        out[ok] = img_data[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]]
        return out
    return ndimage.map_coordinates(img_data.astype(np.float32), ijk.T, order=1, mode='constant', cval=0)


out = {}

# ------------------------------------------------------------------ MRI grid
t1 = datasets.load_mni152_template(resolution=1)
td = np.asarray(t1.dataobj).astype(np.float32)
nz = np.argwhere(td > td.max() * 0.02)
lo = nib.affines.apply_affine(t1.affine, nz.min(0)) - 3
hi = nib.affines.apply_affine(t1.affine, nz.max(0)) + 3
SP = 1.5
dims = np.ceil((hi - lo) / SP).astype(int) + 1
gx, gy, gz = [lo[k] + SP * np.arange(dims[k]) for k in range(3)]
G = np.stack(np.meshgrid(gx, gy, gz, indexing='ij'), -1).reshape(-1, 3)   # x fastest? no: index = (i*ny + j)*nz + k
mri = lookup(td, t1.affine, G, order=1).reshape(dims)
p = np.percentile(mri[mri > 0], 99.5)
mri8 = np.clip(mri / p * 255, 0, 255).astype(np.uint8)
# store as [z][y][x] so x is the fastest axis in the page
mri8z = np.transpose(mri8, (2, 1, 0))
out['grid'] = {'origin': [round(float(v), 3) for v in lo], 'spacing': SP, 'dims': [int(d) for d in dims]}
out['mri'] = gz64(mri8z)
print('MRI grid', dims.tolist(), 'origin', np.round(lo, 1).tolist(), 'voxels', int(np.prod(dims)))

# ------------------------------------------------------------------ label volume (deep structures)
ho = datasets.fetch_atlas_harvard_oxford('sub-maxprob-thr25-2mm', data_dir=C1, verbose=0)
hoimg = ho['maps'] if hasattr(ho['maps'], 'get_fdata') else nib.load(ho['maps'])
hod, hoaff = np.asarray(hoimg.get_fdata()).astype(int), hoimg.affine
HOL = list(ho['labels'])
aal = datasets.fetch_atlas_aal(data_dir=C1, verbose=0)
aalimg = nib.load(str(aal['maps']).replace('AAL3v1.nii', 'AAL3v1_1mm.nii'))
ad, aaff = np.asarray(aalimg.get_fdata()).astype(int), aalimg.affine
AIDX = {name: int(i) for name, i in zip(list(aal['labels']), aal['indices'])}
pa = datasets.fetch_atlas_pauli_2017('deterministic', data_dir=C2, verbose=0)
pimg = pa['maps'] if hasattr(pa['maps'], 'get_fdata') else nib.load(pa['maps'])
pd_, paff = np.asarray(pimg.get_fdata()).astype(int), pimg.affine
PL = [str(x) for x in pa['labels']]
ju = datasets.fetch_atlas_juelich('maxprob-thr25-1mm', data_dir=C2, verbose=0)
jimg = ju['maps'] if hasattr(ju['maps'], 'get_fdata') else nib.load(ju['maps'])
jd, jaff = np.asarray(jimg.get_fdata()).astype(int), jimg.affine
JL = [str(x) for x in ju['labels']]

hoG = lookup(hod, hoaff, G)
aG = lookup(ad, aaff, G)
pG = lookup(pd_, paff, G)
jG = lookup(jd, jaff, G)
X, Z = G[:, 0], G[:, 2]

BASES = []
lab = np.zeros(len(G), np.uint8)


def code(base):
    if base not in BASES:
        BASES.append(base)
    return BASES.index(base) + 1


def put(base, m, only=None):
    c = code(base)
    if only is not None:
        m = m & np.isin(lab, only)
    lab[m] = c


for b, names in [('lateral_ventricle', ['Lateral Ventrical', 'Lateral Ventricle']), ('caudate', ['Caudate']), ('putamen', ['Putamen']),
                 ('globus_pallidus', ['Pallidum']), ('nucleus_accumbens', ['Accumbens']), ('thalamus', ['Thalamus']),
                 ('hippocampus', ['Hippocampus']), ('amygdala', ['Amygdala'])]:
    idx = [i for i, n in enumerate(HOL) if any(n.endswith(x) for x in names) and ('Left' in n or 'Right' in n)]
    put(b, np.isin(hoG, idx))
bs = hoG == HOL.index('Brain-Stem')
put('midbrain', bs & (Z >= -16)); put('pons', bs & (Z < -16) & (Z >= -38)); put('medulla', bs & (Z < -38))


def am(*names):
    return np.isin(aG, [AIDX[n] for n in names if n in AIDX])


for S in ('L', 'R'):
    put('cerebellum_anterior', am(f'Cerebellum_3_{S}', f'Cerebellum_4_5_{S}'))
    put('cerebellum_posterior', am(*[f'Cerebellum_{x}_{S}' for x in ('Crus1', 'Crus2', '6', '7b', '8', '9')]))
    put('flocculonodular', am(f'Cerebellum_10_{S}'))
put('vermis', am(*[n for n in AIDX if n.startswith('Vermis')]))
TR = [('tract_callosal', 'WM Callosal body'), ('tract_cst', 'WM Corticospinal tract'), ('tract_optic', 'WM Optic radiation'),
      ('tract_acoustic', 'WM Acoustic radiation'), ('tract_cingulum', 'WM Cingulum'), ('tract_slf', 'WM Superior longitudinal fascicle'),
      ('tract_ifof', 'WM Inferior occipito-frontal fascicle'), ('tract_sfof', 'WM Superior occipito-frontal fascicle'),
      ('tract_uncinate', 'WM Uncinate fascicle'), ('tract_fornix', 'WM Fornix')]
for b, n in TR:
    put(b, jG == JL.index(n), only=[0])
for S in ('L', 'R'):
    for b, keys in [('thal_anterior', ['Thal_AV']), ('thal_mediodorsal', ['Thal_MDm', 'Thal_MDl']), ('thal_ventral_anterior', ['Thal_VA']),
                    ('thal_ventral_lateral', ['Thal_VL']), ('thal_vpl', ['Thal_VPL']), ('thal_pulvinar', ['Thal_PuI', 'Thal_PuM', 'Thal_PuA', 'Thal_PuL']),
                    ('thal_lgn', ['Thal_LGN']), ('thal_mgn', ['Thal_MGN']), ('thal_lp', ['Thal_LP']), ('thal_il', ['Thal_IL']),
                    ('substantia_nigra', ['SN_pc', 'SN_pr']), ('vta', ['VTA']), ('red_nucleus', ['Red_N']), ('locus_coeruleus', ['LC'])]:
        put(b, am(*[f'{k}_{S}' for k in keys]))
put('raphe_nuclei', am('Raphe_D', 'Raphe_M'))
for b, k in [('hypothalamus', 'HTH'), ('subthalamic_nucleus', 'STH'), ('habenula', 'HN'), ('mammillary_body', 'MN'), ('ventral_pallidum', 'VeP'),
             ('extended_amygdala', 'EXA'), ('gpe', 'GPe'), ('gpi', 'GPi'), ('snc', 'SNc'), ('snr', 'SNr')]:
    put(b, pG == PL.index(k))
hc, ac = code('hippocampus'), code('amygdala')
for b, n, par in [('hipp_ca', 'GM Hippocampus cornu ammonis', hc), ('dentate_gyrus', 'GM Hippocampus dentate gyrus', hc), ('subiculum', 'GM Hippocampus subiculum', hc),
                  ('amyg_lb', 'GM Amygdala_laterobasal group', ac), ('amyg_cm', 'GM Amygdala_centromedial group', ac), ('amyg_sf', 'GM Amygdala_superficial group', ac)]:
    put(b, jG == JL.index(n), only=[par])
labz = np.transpose(lab.reshape(dims), (2, 1, 0))
out['labels'] = gz64(labz)
out['label_bases'] = BASES
print('label volume', len(BASES), 'structures', int((lab > 0).sum()), 'labelled voxels')

# ------------------------------------------------------------------ cortex vertices (pial, inward normals)
VX = {}
for H in ('lh', 'rh'):
    c = geo['cortex'][H]
    n = c['n']
    pos = unb64(c['pial'], np.int16).reshape(-1, 3).astype(np.float64) * 0.1
    faces = unb64(c['faces'], np.uint16 if c['faceType'] == 'u16' else np.uint32).reshape(-1, 3).astype(np.int64)
    fn = np.cross(pos[faces[:, 1]] - pos[faces[:, 0]], pos[faces[:, 2]] - pos[faces[:, 0]])
    vn = np.zeros_like(pos)
    for k in range(3):
        np.add.at(vn, faces[:, k], fn)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-9
    VX[H] = {'pos': pos, 'nrm': vn, 'label': unb64(c['label'], np.uint8), 'hcp': unb64(c['hcp'], np.uint8), 'net': unb64(c['net'], np.uint8)}

LIDX = {n: i for i, n in enumerate(geo['destrieux_labels'])}
HIDX = {n: i for i, n in enumerate(geo['hcp_labels'])}
NIDX = {n: i for i, n in enumerate(geo['net_labels'])}


def region_vertices(r, H):
    v = VX[H]
    if r.get('side') == 'left' and H == 'rh':
        return np.zeros(0, int)
    if r.get('cortex'):
        return np.where(np.isin(v['label'], [LIDX[x] for x in r['cortex']]))[0]
    if r.get('hcp'):
        return np.where(np.isin(v['hcp'], [HIDX[x] for x in r['hcp']]))[0]
    if r.get('net'):
        return np.where(np.isin(v['net'], [NIDX[x] for x in r['net']]))[0]
    return np.zeros(0, int)


def region_voxels(r):
    bases = r.get('deep') or []
    codes = [BASES.index(b) + 1 for b in bases if b in BASES]
    return np.where(np.isin(lab, codes))[0] if codes else np.zeros(0, int)


# ------------------------------------------------------------------ arterial territories
# Johns Hopkins "Digital 3D Brain MRI Arterial Territories Atlas" (Liu et al. 2023, Sci Data 10:74), built from the lesions
# of 1,298 acute stroke patients; CC BY-SA 4.0 (label file). Copy from github.com/abby-0925/arterialatlas (the NITRC
# download needs an account). Level 1 labels, left and right merged into 15 sub-territories:
L1 = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4, 9: 5, 10: 5, 11: 6, 12: 6, 13: 7, 14: 7, 15: 8, 16: 8,
      17: 9, 18: 9, 19: 10, 20: 10, 21: 11, 22: 11, 23: 12, 24: 12, 25: 13, 26: 13, 27: 14, 28: 14, 29: 15, 30: 15}
va = nib.load(os.path.join(C2, 'arterial', 'jhu', 'Atlas_182_MNI152', 'ArterialAtlas.nii'))
vd = np.rint(np.asarray(va.dataobj)[..., 0]).astype(int)
vt = np.zeros_like(vd)
for k, v in L1.items():
    vt[vd == k] = v
_, ind = ndimage.distance_transform_edt(vt == 0, return_indices=True)
vfill = vt[tuple(ind)]                       # every voxel takes its nearest territory (ventricles included)
terrG = lookup(vfill, va.affine, G)
terrG[(mri8.reshape(-1) < 12) & (lab == 0)] = 0
out['terr_grid'] = gz64(np.transpose(terrG.reshape(dims).astype(np.uint8), (2, 1, 0)))
tv = {}
for H in ('lh', 'rh'):
    v = VX[H]
    tv[H] = lookup(vfill, va.affine, v['pos'] - v['nrm'] * 2.0).astype(np.uint8)
out['terr_vertex'] = {H: gz64(tv[H]) for H in tv}
tbase = {}
for b in BASES:
    m = terrG[lab == BASES.index(b) + 1]
    m = m[m > 0]
    if len(m):
        tbase[b] = int(np.bincount(m).argmax())
out['terr_base'] = tbase
# watershed border zones (two maps on the left hemisphere: ACA-MCA anterior, MCA-PCA posterior), mirrored to the right
bz = nib.load(os.path.join(C2, 'arterial', 'jhu', 'Atlas_182_MNI152', 'BorderZone_ProbAve.nii'))
bzd = np.nan_to_num(np.asarray(bz.dataobj)).astype(np.float32)
bzs = np.clip(bzd.max(-1) / max(1e-6, float(bzd.max())), 0, 1)
bzs = np.maximum(bzs, bzs[::-1, :, :])      # x is flipped in this affine, so mirroring the array mirrors left and right
bzG = lookup(bzs, bz.affine, G, order=1)
out['bz_grid'] = gz64(np.transpose(np.round(np.clip(bzG, 0, 1) * 255).reshape(dims).astype(np.uint8), (2, 1, 0)))
out['bz_vertex'] = {}
for H in ('lh', 'rh'):
    v = VX[H]
    val = np.max([lookup(bzs, bz.affine, v['pos'] - v['nrm'] * d, order=1) for d in (1.0, 3.0, 6.0)], axis=0)
    out['bz_vertex'][H] = gz64(np.round(np.clip(val, 0, 1) * 255).astype(np.uint8))
print('territory share of cortex vertices (lh):', np.bincount(tv['lh'], minlength=16).tolist())

# ------------------------------------------------------------------ Juelich probability maps
jp = datasets.fetch_atlas_juelich('prob-1mm', data_dir=C2, verbose=0)
jpimg = jp['maps'] if hasattr(jp['maps'], 'get_fdata') else nib.load(jp['maps'])
jpd = np.asarray(jpimg.dataobj).astype(np.float32)
JPL = [str(x) for x in jp['labels']][1:]   # first label is Background


def jidx(sub):
    k = [i for i, n in enumerate(JPL) if sub.lower() in n.lower()]
    assert k, sub
    return k


PMAP = {
    'brocas_area': ["Broca's area BA44", "Broca's area BA45"], 'pars_opercularis': ["Broca's area BA44"], 'pars_triangularis': ["Broca's area BA45"],
    'primary_motor_cortex': ['BA4a', 'BA4p'], 'precentral_gyrus': ['BA4a', 'BA4p'], 'premotor_cortex': ['Premotor cortex BA6'],
    'primary_somatosensory_cortex': ['BA3a', 'BA3b', 'cortex BA1', 'cortex BA2'], 'postcentral_gyrus': ['BA3a', 'BA3b', 'cortex BA1', 'cortex BA2'],
    'secondary_somatosensory_cortex': ['OP1', 'OP2', 'OP3', 'OP4'],
    'primary_auditory_cortex': ['TE1.0', 'TE1.1', 'TE1.2'], 'heschls_gyrus': ['TE1.0', 'TE1.1', 'TE1.2'],
    'primary_visual_cortex': ['V1 BA17'], 'calcarine_sulcus': ['V1 BA17'], 'secondary_visual_cortex': ['V2 BA18'], 'area_v3': ['V3V'],
    'area_v4': ['Visual cortex V4'], 'area_mt': ['Visual cortex V5'],
    'posterior_insula': ['Insula Ig1', 'Insula Ig2'], 'intraparietal_sulcus': ['hIP1', 'hIP2', 'hIP3'],
    'supramarginal_gyrus': ['lobule PF', 'PFcm', 'PFm', 'PFop', 'PFt'], 'angular_gyrus': ['PGp', 'Pga'],
    'superior_parietal_lobule': ['5Ci', '5L', '5M', '7A', '7M', '7P', '7PC'],
    'entorhinal_cortex': ['entorhinal'], 'hippocampus': ['cornu ammonis', 'dentate gyrus', 'subiculum'], 'cornu_ammonis': ['cornu ammonis'],
    'dentate_gyrus': ['Hippocampus dentate'], 'subiculum': ['subiculum'], 'amygdala': ['Amygdala_'], 'basolateral_amygdala': ['laterobasal'],
    'centromedial_amygdala': ['centromedial'], 'superficial_amygdala': ['Amygdala_superficial'],
    'lateral_geniculate_nucleus': ['Lateral geniculate'], 'medial_geniculate_nucleus': ['Medial geniculate'], 'mammillary_bodies': ['Mamillary'],
    'corpus_callosum': ['Callosal body'], 'corticospinal_tract': ['Corticospinal'], 'optic_radiation': ['Optic radiation'], 'acoustic_radiation': ['Acoustic radiation'],
    'cingulum': ['WM Cingulum'], 'superior_longitudinal_fasciculus': ['Superior longitudinal'], 'inferior_fronto_occipital_fasciculus': ['Inferior occipito-frontal'],
    'superior_fronto_occipital_fasciculus': ['Superior occipito-frontal'], 'uncinate_fasciculus': ['Uncinate'], 'fornix': ['WM Fornix'],
}
rids = {r['id'] for r in REG}
CS = 3.0
cdims = np.ceil((hi - lo) / CS).astype(int) + 1
CG = np.stack(np.meshgrid(*[lo[k] + CS * np.arange(cdims[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
prob = {}
for rid, subs in PMAP.items():
    if rid not in rids:
        continue
    ks = sorted({k for s in subs for k in jidx(s)})
    vol = np.clip(jpd[..., ks].sum(-1), 0, 100) / 100.0
    ent = {}
    r = next(x for x in REG if x['id'] == rid)
    if r.get('cortex') or r.get('hcp'):
        for H in ('lh', 'rh'):
            v = VX[H]
            vals = np.max([lookup(vol, jpimg.affine, v['pos'] - v['nrm'] * d, order=1) for d in (0.5, 1.5, 2.5, 3.5)], axis=0)
            keep = np.where(vals >= 0.05)[0]
            ent[H] = [gz64(keep.astype(np.uint16)), gz64(np.round(vals[keep] * 255).astype(np.uint8))]
    cv = lookup(vol, jpimg.affine, CG, order=1)
    keep = np.where(cv >= 0.05)[0]
    ent['vox'] = [gz64(keep.astype(np.uint32)), gz64(np.round(cv[keep] * 255).astype(np.uint8))]
    ent['n'] = len(ks)
    prob[rid] = ent
out['prob'] = prob
out['prob_grid'] = {'origin': [round(float(v), 3) for v in lo], 'spacing': CS, 'dims': [int(d) for d in cdims]}
print('probability maps for', len(prob), 'regions')

# ------------------------------------------------------------------ NeuroQuery function scores
from neuroquery import NeuroQueryModel  # noqa: E402
nq = NeuroQueryModel.from_data_dir(os.path.join(C2, 'neuroquery', 'neuroquery_model'))
vocab = set(nq.full_vocabulary()) if hasattr(nq, 'full_vocabulary') else None
TERMS = json.load(open(os.path.join(HERE, 'function_terms.json'), encoding='utf-8'))
reg_pts = {}
for r in REG:
    pts = []
    for H in ('lh', 'rh'):
        idx = region_vertices(r, H)
        if len(idx):
            v = VX[H]
            pts.append(v['pos'][idx] - v['nrm'][idx] * 2.0)
    vox = region_voxels(r)
    if len(vox):
        pts.append(G[vox])
    if pts:
        reg_pts[r['id']] = np.concatenate(pts)
ids = [r['id'] for r in REG]
scores, kept = [], []
for term in TERMS:
    q = term['q']
    res = nq(q)
    bm = res['brain_map']
    bd = np.asarray(bm.get_fdata()).astype(np.float32)
    row = np.zeros(len(ids), np.float32)
    for i, rid in enumerate(ids):
        if rid in reg_pts:
            row[i] = lookup(bd, bm.affine, reg_pts[rid], order=1).mean()
    if row.max() <= 0:
        print('  no map for', q)
        continue
    kept.append({'t': term['t'], 'q': q, 'syn': term.get('syn', []), 'max': round(float(row.max()), 2)})
    scores.append(np.clip(np.round(row / row.max() * 100), 0, 100).astype(np.uint8))
out['fn_terms'] = kept
out['fn_regions'] = ids
out['fn_scores'] = gz64(np.stack(scores))
print('function terms kept', len(kept), 'of', len(TERMS))

json.dump(out, open(os.path.join(HERE, 'extras.json'), 'w', encoding='utf-8'), separators=(',', ':'))
print('wrote extras.json', round(os.path.getsize(os.path.join(HERE, 'extras.json')) / 1e6, 2), 'MB')
