"""Build the atlas geometry and the region index.   python -X utf8 -I data/build_meshes.py

Output: data/atlas_geometry.json   (compact: Int16 coordinates in 0.1 mm, Uint16/Uint32 faces, Uint8 labels, base64)
        data/regions_index.json    (every region the app knows: id, name, deck, source labels, side, mesh or parcel)

Sources (downloaded by data/fetch.py):
- fsaverage5 pial and inflated surfaces + sulcal depth (FreeSurfer, via nilearn)
- Destrieux 2009 surface atlas on fsaverage5 (gyri and sulci)
- Harvard-Oxford subcortical atlas, max-prob thr25, 2 mm (FSL)
- AAL3v1 (Rolls et al. 2020): cerebellum, vermis, thalamic nuclei, SN, VTA, red nucleus, LC, raphe
Coordinates are millimetres in MNI-like space (fsaverage is close to MNI305; the volume atlases are MNI152), so the
deep structures sit within a few millimetres of where the cortex expects them.
"""
import base64
import json
import os
import warnings

import nibabel as nib
import numpy as np
import pyfqmr
from nilearn import datasets, surface
from scipy import ndimage
from skimage import measure

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, 'nilearn_data')


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode('ascii')


def q16(v):
    return np.round(np.asarray(v, dtype=np.float64) * 10).astype(np.int16)


# ---------------- cortex ----------------
# fsaverage6 (40,962 vertices per hemisphere) for a smooth render. The Destrieux labels exist on fsaverage5; the
# icosahedral meshes are nested (the first 10,242 fsaverage6 vertices are the fsaverage5 vertices), so each fsaverage6
# vertex takes the label of its nearest fsaverage5 vertex on the sphere, then one majority pass smooths the borders.
from scipy.spatial import cKDTree
fs5 = datasets.fetch_surf_fsaverage('fsaverage5', data_dir=C)
fs = datasets.fetch_surf_fsaverage('fsaverage6', data_dir=C)
des = datasets.fetch_atlas_surf_destrieux(data_dir=C, verbose=0)
DLAB = [str(x.decode() if isinstance(x, bytes) else x) for x in des['labels']]
cortex = {}
for hemi, H in (('left', 'lh'), ('right', 'rh')):
    pial = surface.load_surf_mesh(fs['pial_' + hemi])
    infl = surface.load_surf_mesh(fs['infl_' + hemi])
    sulc = surface.load_surf_data(fs['sulc_' + hemi]).astype(np.float32)
    curv = surface.load_surf_data(fs['curv_' + hemi]).astype(np.float32)
    lab5 = np.asarray(des['map_' + hemi]).astype(np.uint8)
    s5 = np.asarray(surface.load_surf_mesh(fs5['sphere_' + hemi]).coordinates)
    s6 = np.asarray(surface.load_surf_mesh(fs['sphere_' + hemi]).coordinates)
    _, nn = cKDTree(s5).query(s6)
    lab = lab5[nn]
    pv, pf = np.asarray(pial.coordinates), np.asarray(pial.faces)
    nb = [[] for _ in range(len(pv))]
    for a, b_, c in pf:
        nb[a] += [b_, c]; nb[b_] += [a, c]; nb[c] += [a, b_]
    for _ in range(2):
        new = lab.copy()
        for i in range(10242, len(pv)):          # keep the original fsaverage5 labels fixed
            vals, cnt = np.unique(lab[nb[i]], return_counts=True)
            if cnt.max() * 2 > len(nb[i]):
                new[i] = vals[cnt.argmax()]
        lab = new
    # shading signal: mostly sulcal depth (large folds) plus some curvature (crowns and fundi)
    cz = np.clip(curv / (np.percentile(np.abs(curv), 95) + 1e-6), -1, 1)
    sulc = sulc + 0.35 * cz * (np.percentile(sulc, 98) - np.percentile(sulc, 2)) / 2
    iv = np.asarray(infl.coordinates).copy()
    # inflated hemispheres overlap at the midline: push each one out so their medial faces sit 6 mm from x = 0
    if hemi == 'left':
        iv[:, 0] += -6 - iv[:, 0].max()
    else:
        iv[:, 0] += 6 - iv[:, 0].min()
    # inflated is larger and centred differently; match its centre to the pial centre in y and z
    iv[:, 1:] += pv[:, 1:].mean(0) - iv[:, 1:].mean(0)
    s = np.clip((sulc - np.percentile(sulc, 2)) / (np.percentile(sulc, 98) - np.percentile(sulc, 2)), 0, 1)
    cortex[H] = {
        'n': int(len(pv)), 'pial': b64(q16(pv)), 'infl': b64(q16(iv)),
        'faces': b64(pf.astype(np.uint16 if len(pv) < 65536 else np.uint32)), 'faceType': 'u16' if len(pv) < 65536 else 'u32',
        'label': b64(lab), 'sulc': b64(np.round(s * 255).astype(np.uint8)),
    }
    print(hemi, 'vertices', len(pv), 'faces', len(pf), 'labels used', len(np.unique(lab)),
          'pial x range', pv[:, 0].min().round(1), pv[:, 0].max().round(1), 'z range', pv[:, 2].min().round(1), pv[:, 2].max().round(1))


# ---------------- deep structures ----------------
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
    # light Laplacian smoothing (keeps the marching-cubes steps from showing)
    nb = [set() for _ in range(len(v))]
    for a, b_, c in faces:
        nb[a].update((b_, c)); nb[b_].update((a, c)); nb[c].update((a, b_))
    nb = [list(x) for x in nb]
    for it in range(smooth_iter):
        lam = 0.5 if it % 2 == 0 else -0.53   # Taubin: shrink then inflate
        avg = np.array([v[n].mean(0) if n else v[i] for i, n in enumerate(nb)])
        v = v + lam * (avg - v)
    return {'v': b64(q16(v)), 'f': b64(np.asarray(faces, dtype=np.uint16)), 'nv': int(len(v)), 'nf': int(len(faces)),
            'center': [round(float(x), 1) for x in v.mean(0)]}


ho = datasets.fetch_atlas_harvard_oxford('sub-maxprob-thr25-2mm', data_dir=C, verbose=0)
hoimg = nib.load(ho['maps']) if isinstance(ho['maps'], str) else ho['maps']
hod, hoaff = np.asarray(hoimg.get_fdata()).astype(int), hoimg.affine
HOL = list(ho['labels'])
aal = datasets.fetch_atlas_aal(data_dir=C, verbose=0)
aalimg = nib.load(str(aal['maps']).replace('AAL3v1.nii', 'AAL3v1_1mm.nii'))  # 1 mm, so the small nuclei keep their shape
ad, aaff = np.asarray(aalimg.get_fdata()).astype(int), aalimg.affine
AL = list(aal['labels'])
AIDX = {name: int(i) for name, i in zip(AL, aal['indices'])} if 'indices' in aal else None
if AIDX is None or not AIDX:
    raise SystemExit('AAL indices missing')
print('AAL voxel size', np.round(np.abs(np.diag(aaff))[:3], 2), 'HO voxel size', np.round(np.abs(np.diag(hoaff))[:3], 2))


def ho_mask(*names):
    m = np.zeros(hod.shape, bool)
    for n in names:
        m |= hod == HOL.index(n)
    return m


def aal_mask(*names):
    m = np.zeros(ad.shape, bool)
    for n in names:
        m |= ad == AIDX[n]
    return m


def zcut(mask, aff, zmin=None, zmax=None):
    """keep voxels whose MNI z is in [zmin, zmax)"""
    k = np.arange(mask.shape[2])
    z = aff[2, 2] * k + aff[2, 3]
    keep = np.ones_like(z, bool)
    if zmin is not None:
        keep &= z >= zmin
    if zmax is not None:
        keep &= z < zmax
    out = mask.copy()
    out[:, :, ~keep] = False
    return out


deep = {}


def add(rid, mask, aff, faces=2400, sigma=0.9):
    m = mesh_from_mask(mask, aff, faces, sigma)
    if m:
        deep[rid] = m
        print(f'{rid:28s} voxels {int(mask.sum()):6d} -> {m["nf"]} faces at {m["center"]}')
    else:
        print('EMPTY', rid)


for side, S in (('L', 'Left'), ('R', 'Right')):
    s = side.lower()
    add(f'thalamus_{s}', ho_mask(f'{S} Thalamus'), hoaff)
    add(f'caudate_{s}', ho_mask(f'{S} Caudate'), hoaff)
    add(f'putamen_{s}', ho_mask(f'{S} Putamen'), hoaff)
    add(f'globus_pallidus_{s}', ho_mask(f'{S} Pallidum'), hoaff, 1600)
    add(f'nucleus_accumbens_{s}', ho_mask(f'{S} Accumbens'), hoaff, 900)
    add(f'hippocampus_{s}', ho_mask(f'{S} Hippocampus'), hoaff)
    add(f'amygdala_{s}', ho_mask(f'{S} Amygdala'), hoaff, 1400)
    add(f'lateral_ventricle_{s}', ho_mask(f'{S} Lateral Ventricle'), hoaff, 2600)
    # cerebellum: anterior lobe (I to V), posterior lobe (VI to IX incl. crus I/II), flocculonodular (X)
    add(f'cerebellum_anterior_{s}', aal_mask(f'Cerebellum_3_{side}', f'Cerebellum_4_5_{side}'), aaff, 2600, 1.0)
    add(f'cerebellum_posterior_{s}', aal_mask(*[f'Cerebellum_{x}_{side}' for x in ('Crus1', 'Crus2', '6', '7b', '8', '9')]), aaff, 4200, 1.0)
    add(f'flocculonodular_{s}', aal_mask(f'Cerebellum_10_{side}'), aaff, 700, 0.8)
    # thalamic nuclei (AAL3 groups)
    add(f'thal_anterior_{s}', aal_mask(f'Thal_AV_{side}'), aaff, 500, 0.7)
    add(f'thal_mediodorsal_{s}', aal_mask(f'Thal_MDm_{side}', f'Thal_MDl_{side}'), aaff, 800, 0.7)
    add(f'thal_ventral_anterior_{s}', aal_mask(f'Thal_VA_{side}'), aaff, 500, 0.7)
    add(f'thal_ventral_lateral_{s}', aal_mask(f'Thal_VL_{side}'), aaff, 700, 0.7)
    add(f'thal_vpl_{s}', aal_mask(f'Thal_VPL_{side}'), aaff, 600, 0.7)
    add(f'thal_pulvinar_{s}', aal_mask(*[f'Thal_{x}_{side}' for x in ('PuI', 'PuM', 'PuA', 'PuL')]), aaff, 900, 0.7)
    add(f'thal_lgn_{s}', aal_mask(f'Thal_LGN_{side}'), aaff, 300, 0.6)
    add(f'thal_mgn_{s}', aal_mask(f'Thal_MGN_{side}'), aaff, 300, 0.6)
    add(f'substantia_nigra_{s}', aal_mask(f'SN_pc_{side}', f'SN_pr_{side}'), aaff, 500, 0.6)
    add(f'vta_{s}', aal_mask(f'VTA_{side}'), aaff, 300, 0.6)
    add(f'red_nucleus_{s}', aal_mask(f'Red_N_{side}'), aaff, 300, 0.6)
    add(f'locus_coeruleus_{s}', aal_mask(f'LC_{side}'), aaff, 200, 0.6)

add('vermis', aal_mask(*[n for n in AL if n.startswith('Vermis')]), aaff, 2400, 1.0)
add('raphe_nuclei', aal_mask('Raphe_D', 'Raphe_M'), aaff, 300, 0.6)
bs = ho_mask('Brain-Stem')
# brainstem split by MNI z (approximate levels): midbrain above -16, pons -16 to -38, medulla below -38
add('midbrain', zcut(bs, hoaff, zmin=-16), hoaff, 1800)
add('pons', zcut(bs, hoaff, zmin=-38, zmax=-16), hoaff, 1800)
add('medulla', zcut(bs, hoaff, zmax=-38), hoaff, 1400)

geo = {'source': 'fsaverage5 (FreeSurfer) + Destrieux 2009; Harvard-Oxford subcortical; AAL3v1. Built 2026-11-19.',
       'scale': 0.1, 'cortex': cortex, 'destrieux_labels': DLAB, 'deep': deep}
out = os.path.join(HERE, 'atlas_geometry.json')
json.dump(geo, open(out, 'w', encoding='utf-8'), separators=(',', ':'))
print('wrote', out, round(os.path.getsize(out) / 1e6, 2), 'MB')
