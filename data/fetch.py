"""Download the open brain data the atlas is built from and print what each contains.
python -X utf8 -I data/fetch.py
- fsaverage5 cortical surfaces (pial, inflated, sulcal depth), bundled with nilearn
- Destrieux surface atlas on fsaverage5 (gyri and sulci, 74 labels per hemisphere)
- Harvard-Oxford subcortical atlas (MNI152, 2 mm) for deep structures
- AAL atlas (for cerebellum parts and vermis)
"""
import os

import numpy as np
from nilearn import datasets, surface

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'nilearn_data')
fs = datasets.fetch_surf_fsaverage('fsaverage5', data_dir=CACHE)
print('fsaverage5 keys:', sorted(k for k in fs.keys() if not k.startswith('description')))
for k in ('pial_left', 'infl_left', 'sulc_left'):
    v = fs[k]
    print(k, type(v).__name__, getattr(v, 'parts', None) and list(v.parts.keys()))
des = datasets.fetch_atlas_surf_destrieux(data_dir=CACHE)
print('destrieux labels:', len(des['labels']), des['labels'][:6], '...')
print('map_left shape', np.asarray(des['map_left']).shape, 'unique', len(np.unique(des['map_left'])))
ho = datasets.fetch_atlas_harvard_oxford('sub-maxprob-thr25-2mm', data_dir=CACHE)
print('harvard-oxford sub labels:', ho['labels'])
try:
    aal = datasets.fetch_atlas_aal(data_dir=CACHE)
    print('aal labels:', len(aal['labels']), [l for l in aal['labels'] if 'Cerebel' in l or 'Vermis' in l][:30])
except Exception as e:
    print('aal failed', e)
