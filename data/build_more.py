"""Second geometry pass (2026-11-19). Adds to atlas_geometry.json, keeping everything already there:
- surface layers on the fsaverage6 cortex: `hcp` (HCP-MMP1.0, Glasser et al. 2016, 180 areas per hemisphere, from the
  fsaverage annotation on figshare 3498446; fsaverage6 vertices are the first 40,962 fsaverage vertices) and `net`
  (Yeo 2011 7 networks, read from the Schaefer 2018 400-parcel 7-network fsaverage6 annotation, CBIG GitHub)
- meshes: Juelich histological atlas (Eickhoff 2005 / FSL) white-matter tracts, hippocampal subfields and amygdala
  groups; Pauli 2017 (CIT168) subcortical nuclei; AAL3 thalamic LP, IL and Re.
python -X utf8 -I data/build_more.py      (backs up the old file to atlas_geometry_v1.json the first time)
"""
import base64
import json
import os
import shutil
import warnings

import nibabel as nib
import numpy as np
import pyfqmr
from nilearn import datasets
from scipy import ndimage
from skimage import measure

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
C1 = os.path.join(HERE, 'nilearn_data')
C2 = os.path.join(HERE, 'cache')
EXT = os.path.join(C2, 'ext')
GEO = os.path.join(HERE, 'atlas_geometry.json')
if not os.path.exists(os.path.join(HERE, 'atlas_geometry_v1.json')):
    shutil.copyfile(GEO, os.path.join(HERE, 'atlas_geometry_v1.json'))
geo = json.load(open(os.path.join(HERE, 'atlas_geometry_v1.json'), encoding='utf-8'))


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode('ascii')


def q16(v):
    return np.round(np.asarray(v, dtype=np.float64) * 10).astype(np.int16)


# ------------------------------------------------------------------ surface layers
def strip(n):
    n = n.decode() if isinstance(n, bytes) else n
    if n.startswith(('L_', 'R_')):
        n = n[2:]
    if n.endswith('_ROI'):
        n = n[:-4]
    return n


lab_l, _, names_l = nib.freesurfer.read_annot(os.path.join(EXT, 'lh.HCP-MMP1.annot'))
HCP = [strip(n) for n in names_l]          # index 0 is '???' (medial wall / unknown)
HIDX = {n: i for i, n in enumerate(HCP)}
NETS = ['medial wall', 'Vis', 'SomMot', 'DorsAttn', 'SalVentAttn', 'Limbic', 'Cont', 'Default']
for H in ('lh', 'rh'):
    n = geo['cortex'][H]['n']
    lab, _, names = nib.freesurfer.read_annot(os.path.join(EXT, f'{H}.HCP-MMP1.annot'))
    names = [strip(x) for x in names]
    remap = np.array([HIDX.get(x, 0) for x in names] + [0], dtype=np.uint8)
    lab = np.where(lab < 0, len(names), lab)
    hcp = remap[lab[:n]]
    lab2, _, names2 = nib.freesurfer.read_annot(os.path.join(EXT, f'{H}.Schaefer400_7net.annot'))
    assert len(lab2) == n, (H, len(lab2), n)
    netof = []
    for x in names2:
        x = x.decode() if isinstance(x, bytes) else x
        k = 0
        if x.startswith('7Networks_'):
            k = NETS.index(x.split('_')[2])
        netof.append(k)
    netof = np.array(netof + [0], dtype=np.uint8)
    lab2 = np.where(lab2 < 0, len(names2), lab2)
    net = netof[lab2]
    geo['cortex'][H]['hcp'] = b64(hcp.astype(np.uint8))
    geo['cortex'][H]['net'] = b64(net.astype(np.uint8))
    print(H, 'hcp areas used', len(np.unique(hcp)), 'networks used', np.unique(net).tolist())
geo['hcp_labels'] = HCP
geo['net_labels'] = NETS


# ------------------------------------------------------------------ meshes
def mesh_from_mask(mask, affine, target_faces, sigma=0.9, smooth_iter=8):
    if mask.sum() < 4:
        return None
    pad = np.pad(mask.astype(np.float32), 2)
    f = ndimage.gaussian_filter(pad, sigma)
    lvl = 0.5 if f.max() > 0.5 else f.max() * 0.6
    v, faces, _, _ = measure.marching_cubes(f, level=lvl)
    v -= 2
    v = nib.affines.apply_affine(affine, v)
    if len(faces) > target_faces:
        sim = pyfqmr.Simplify()
        sim.setMesh(v, faces)
        sim.simplify_mesh(target_count=target_faces, aggressiveness=6, preserve_border=True, verbose=0)
        v, faces, _ = sim.getMesh()
    nb = [set() for _ in range(len(v))]
    for a, b_, c in faces:
        nb[a].update((b_, c)); nb[b_].update((a, c)); nb[c].update((a, b_))
    nb = [list(x) for x in nb]
    for it in range(smooth_iter):
        lam = 0.5 if it % 2 == 0 else -0.53
        avg = np.array([v[n].mean(0) if n else v[i] for i, n in enumerate(nb)])
        v = v + lam * (avg - v)
    return {'v': b64(q16(v)), 'f': b64(np.asarray(faces, dtype=np.uint16)), 'nv': int(len(v)), 'nf': int(len(faces)),
            'center': [round(float(x), 1) for x in v.mean(0)]}


def xside(mask, aff, side):
    """keep voxels left (x < 0) or right (x > 0) of the midline"""
    i = np.arange(mask.shape[0])
    x = aff[0, 0] * i + aff[0, 3]
    out = mask.copy()
    out[(x >= 0) if side == 'l' else (x <= 0), :, :] = False
    return out


deep = geo['deep']


def add(rid, mask, aff, faces=2400, sigma=0.9):
    m = mesh_from_mask(mask, aff, faces, sigma)
    if m:
        deep[rid] = m
        print(f'{rid:28s} voxels {int(mask.sum()):7d} -> {m["nf"]} faces at {m["center"]}')
    else:
        print('EMPTY', rid)


# Juelich (FSL), max probability, 25 % threshold, 1 mm
ju = datasets.fetch_atlas_juelich('maxprob-thr25-1mm', data_dir=C2, verbose=0)
jimg = ju['maps'] if hasattr(ju['maps'], 'get_fdata') else nib.load(ju['maps'])
jd, jaff = np.asarray(jimg.get_fdata()).astype(int), jimg.affine
JL = [str(x) for x in ju['labels']]


def jm(*names):
    m = np.zeros(jd.shape, bool)
    for n in names:
        m |= jd == JL.index(n)
    return m


TRACTS = [('tract_cst', 'WM Corticospinal tract', 2600), ('tract_optic', 'WM Optic radiation', 2200),
          ('tract_acoustic', 'WM Acoustic radiation', 900), ('tract_cingulum', 'WM Cingulum', 2000),
          ('tract_slf', 'WM Superior longitudinal fascicle', 2600), ('tract_ifof', 'WM Inferior occipito-frontal fascicle', 2600),
          ('tract_sfof', 'WM Superior occipito-frontal fascicle', 1600), ('tract_uncinate', 'WM Uncinate fascicle', 1400)]
for rid, lab, nf in TRACTS:
    m = jm(lab)
    for s in ('l', 'r'):
        add(f'{rid}_{s}', xside(m, jaff, s), jaff, nf, 1.0)
add('tract_fornix', jm('WM Fornix'), jaff, 1600, 0.9)
add('tract_callosal', jm('WM Callosal body'), jaff, 3200, 1.0)
for rid, labs, nf in [('hipp_ca', ['GM Hippocampus cornu ammonis'], 1600), ('dentate_gyrus', ['GM Hippocampus dentate gyrus'], 1200),
                      ('subiculum', ['GM Hippocampus subiculum'], 1000), ('amyg_lb', ['GM Amygdala_laterobasal group'], 1000),
                      ('amyg_cm', ['GM Amygdala_centromedial group'], 600), ('amyg_sf', ['GM Amygdala_superficial group'], 700)]:
    m = jm(*labs)
    for s in ('l', 'r'):
        add(f'{rid}_{s}', xside(m, jaff, s), jaff, nf, 0.8)

# Pauli 2017 (CIT168) deterministic
pa = datasets.fetch_atlas_pauli_2017('deterministic', data_dir=C2, verbose=0)
pimg = pa['maps'] if hasattr(pa['maps'], 'get_fdata') else nib.load(pa['maps'])
pd, paff = np.asarray(pimg.get_fdata()).astype(int), pimg.affine
PL = [str(x) for x in pa['labels']]
print('Pauli voxel size', np.round(np.abs(np.diag(paff))[:3], 2), 'labels', PL)
for rid, lab, nf, sg in [('hypothalamus', 'HTH', 900, 0.8), ('subthalamic_nucleus', 'STH', 400, 0.6), ('habenula', 'HN', 200, 0.5),
                         ('mammillary_body', 'MN', 250, 0.5), ('ventral_pallidum', 'VeP', 500, 0.6), ('gpe', 'GPe', 900, 0.7),
                         ('gpi', 'GPi', 600, 0.7), ('extended_amygdala', 'EXA', 600, 0.6), ('snc', 'SNc', 500, 0.6), ('snr', 'SNr', 400, 0.6)]:
    m = pd == PL.index(lab)
    for s in ('l', 'r'):
        add(f'{rid}_{s}', xside(m, paff, s), paff, nf, sg)

# AAL3 thalamic nuclei not used before
aal = datasets.fetch_atlas_aal(data_dir=C1, verbose=0)
aalimg = nib.load(str(aal['maps']).replace('AAL3v1.nii', 'AAL3v1_1mm.nii'))
ad, aaff = np.asarray(aalimg.get_fdata()).astype(int), aalimg.affine
AIDX = {name: int(i) for name, i in zip(list(aal['labels']), aal['indices'])}
print('AAL thal labels', [k for k in AIDX if k.startswith('Thal_')])
for rid, key, nf in [('thal_lp', 'Thal_LP', 400), ('thal_il', 'Thal_IL', 400), ('thal_re', 'Thal_Re', 200)]:
    for s, S in (('l', 'L'), ('r', 'R')):
        nm = f'{key}_{S}'
        if nm in AIDX:
            add(f'{rid}_{s}', ad == AIDX[nm], aaff, nf, 0.6)
        else:
            print('missing AAL label', nm)

geo['source'] = (geo['source'] + ' Second pass 2026-11-19: HCP-MMP1.0 (Glasser 2016) and Yeo 2011 7 networks (via Schaefer 2018 '
                 'fsaverage6) on the surface; Juelich histological atlas tracts, hippocampal subfields and amygdala groups; '
                 'Pauli 2017 subcortical nuclei; AAL3 LP, IL, Re.')
json.dump(geo, open(GEO, 'w', encoding='utf-8'), separators=(',', ':'))
print('wrote', GEO, round(os.path.getsize(GEO) / 1e6, 2), 'MB', len(deep), 'meshes')
