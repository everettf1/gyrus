"""Region index for the atlas: every region the app can show, its deck, its typing name and what geometry it covers.
python -X utf8 -I data/regions_index.py  -> data/regions_index.json

Cortex regions point at Destrieux labels (both hemispheres unless a side is set). Deep regions point at mesh ids in
atlas_geometry.json (without the _l / _r suffix when they come in pairs).
Names follow Destrieux et al. 2010 (NeuroImage 53:1-15) for gyri and sulci.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Destrieux label -> (typing name, full name, extra aliases, lobe)
D = {
    'G_and_S_frontomargin': ('frontomarginal gyrus', 'Fronto-marginal gyrus and sulcus', ['frontomarginal sulcus', 'fronto-marginal gyrus'], 'frontal'),
    'G_and_S_occipital_inf': ('inferior occipital gyrus', 'Inferior occipital gyrus and sulcus', ['inferior occipital sulcus'], 'occipital'),
    'G_and_S_paracentral': ('paracentral lobule', 'Paracentral lobule and sulcus', ['paracentral sulcus'], 'frontal'),
    'G_and_S_subcentral': ('subcentral gyrus', 'Subcentral gyrus (central operculum) and sulci', ['central operculum', 'rolandic operculum'], 'frontal'),
    'G_and_S_transv_frontopol': ('transverse frontopolar gyri', 'Transverse frontopolar gyri and sulci', ['frontopolar gyri'], 'frontal'),
    'G_and_S_cingul-Ant': ('anterior cingulate gyrus', 'Anterior part of the cingulate gyrus and sulcus', ['anterior cingulate'], 'limbic'),
    'G_and_S_cingul-Mid-Ant': ('anterior midcingulate gyrus', 'Middle-anterior part of the cingulate gyrus and sulcus', ['anterior midcingulate', 'amcc'], 'limbic'),
    'G_and_S_cingul-Mid-Post': ('posterior midcingulate gyrus', 'Middle-posterior part of the cingulate gyrus and sulcus', ['posterior midcingulate', 'pmcc'], 'limbic'),
    'G_cingul-Post-dorsal': ('dorsal posterior cingulate gyrus', 'Posterior-dorsal part of the cingulate gyrus', ['dorsal posterior cingulate', 'dpcc'], 'limbic'),
    'G_cingul-Post-ventral': ('ventral posterior cingulate gyrus', 'Posterior-ventral part of the cingulate gyrus (isthmus)', ['isthmus of cingulate gyrus', 'cingulate isthmus', 'vpcc'], 'limbic'),
    'G_cuneus': ('cuneus', 'Cuneus', [], 'occipital'),
    'G_front_inf-Opercular': ('pars opercularis', 'Opercular part of the inferior frontal gyrus', ['opercular part of the inferior frontal gyrus'], 'frontal'),
    'G_front_inf-Orbital': ('pars orbitalis', 'Orbital part of the inferior frontal gyrus', ['orbital part of the inferior frontal gyrus'], 'frontal'),
    'G_front_inf-Triangul': ('pars triangularis', 'Triangular part of the inferior frontal gyrus', ['triangular part of the inferior frontal gyrus'], 'frontal'),
    'G_front_middle': ('middle frontal gyrus', 'Middle frontal gyrus', ['f2'], 'frontal'),
    'G_front_sup': ('superior frontal gyrus', 'Superior frontal gyrus', ['f1'], 'frontal'),
    'G_Ins_lg_and_S_cent_ins': ('long insular gyrus', 'Long insular gyrus and central sulcus of the insula', ['long gyrus of the insula'], 'insula'),
    'G_insular_short': ('short insular gyri', 'Short insular gyri', ['short gyri of the insula'], 'insula'),
    'G_occipital_middle': ('middle occipital gyrus', 'Middle occipital gyrus', ['lateral occipital gyrus'], 'occipital'),
    'G_occipital_sup': ('superior occipital gyrus', 'Superior occipital gyrus', [], 'occipital'),
    'G_oc-temp_lat-fusifor': ('fusiform gyrus', 'Lateral occipito-temporal gyrus (fusiform gyrus)', ['lateral occipitotemporal gyrus'], 'temporal'),
    'G_oc-temp_med-Lingual': ('lingual gyrus', 'Lingual gyrus', ['medial occipitotemporal gyrus'], 'occipital'),
    'G_oc-temp_med-Parahip': ('parahippocampal gyrus', 'Parahippocampal gyrus', [], 'limbic'),
    'G_orbital': ('orbital gyri', 'Orbital gyri', ['orbital gyrus'], 'frontal'),
    'G_pariet_inf-Angular': ('angular gyrus', 'Angular gyrus', [], 'parietal'),
    'G_pariet_inf-Supramar': ('supramarginal gyrus', 'Supramarginal gyrus', [], 'parietal'),
    'G_parietal_sup': ('superior parietal lobule', 'Superior parietal lobule', [], 'parietal'),
    'G_postcentral': ('postcentral gyrus', 'Postcentral gyrus', [], 'parietal'),
    'G_precentral': ('precentral gyrus', 'Precentral gyrus', [], 'frontal'),
    'G_precuneus': ('precuneus', 'Precuneus', [], 'parietal'),
    'G_rectus': ('gyrus rectus', 'Straight gyrus (gyrus rectus)', ['straight gyrus'], 'frontal'),
    'G_subcallosal': ('subcallosal gyrus', 'Subcallosal area', ['subcallosal area'], 'limbic'),
    'G_temp_sup-G_T_transv': ('heschl\'s gyrus', 'Anterior transverse temporal gyrus (of Heschl)', ['heschls gyrus', 'transverse temporal gyrus', 'heschl gyrus'], 'temporal'),
    'G_temp_sup-Lateral': ('superior temporal gyrus', 'Lateral aspect of the superior temporal gyrus', ['stg'], 'temporal'),
    'G_temp_sup-Plan_polar': ('planum polare', 'Planum polare of the superior temporal gyrus', [], 'temporal'),
    'G_temp_sup-Plan_tempo': ('planum temporale', 'Planum temporale of the superior temporal gyrus', ['temporal plane'], 'temporal'),
    'G_temporal_inf': ('inferior temporal gyrus', 'Inferior temporal gyrus', ['itg'], 'temporal'),
    'G_temporal_middle': ('middle temporal gyrus', 'Middle temporal gyrus', ['mtg'], 'temporal'),
    'Lat_Fis-ant-Horizont': ('anterior horizontal ramus', 'Horizontal ramus of the anterior segment of the lateral sulcus', ['horizontal ramus of the lateral sulcus'], 'frontal'),
    'Lat_Fis-ant-Vertical': ('anterior ascending ramus', 'Vertical ramus of the anterior segment of the lateral sulcus', ['vertical ramus of the lateral sulcus', 'ascending ramus'], 'frontal'),
    'Lat_Fis-post': ('lateral sulcus', 'Posterior ramus of the lateral sulcus (sylvian fissure)', ['sylvian fissure', 'lateral fissure', 'posterior ramus of the lateral sulcus'], 'temporal'),
    'Pole_occipital': ('occipital pole', 'Occipital pole', [], 'occipital'),
    'Pole_temporal': ('temporal pole', 'Temporal pole', [], 'temporal'),
    'S_calcarine': ('calcarine sulcus', 'Calcarine sulcus', ['calcarine fissure'], 'occipital'),
    'S_central': ('central sulcus', 'Central sulcus (of Rolando)', ['rolandic fissure', 'sulcus of rolando'], 'frontal'),
    'S_cingul-Marginalis': ('marginal sulcus', 'Marginal branch of the cingulate sulcus', ['marginal ramus', 'pars marginalis'], 'parietal'),
    'S_circular_insula_ant': ('anterior circular sulcus', 'Anterior segment of the circular sulcus of the insula', [], 'insula'),
    'S_circular_insula_inf': ('inferior circular sulcus', 'Inferior segment of the circular sulcus of the insula', [], 'insula'),
    'S_circular_insula_sup': ('superior circular sulcus', 'Superior segment of the circular sulcus of the insula', [], 'insula'),
    'S_collat_transv_ant': ('anterior transverse collateral sulcus', 'Anterior transverse collateral sulcus', [], 'temporal'),
    'S_collat_transv_post': ('posterior transverse collateral sulcus', 'Posterior transverse collateral sulcus', [], 'occipital'),
    'S_front_inf': ('inferior frontal sulcus', 'Inferior frontal sulcus', [], 'frontal'),
    'S_front_middle': ('middle frontal sulcus', 'Middle frontal sulcus', [], 'frontal'),
    'S_front_sup': ('superior frontal sulcus', 'Superior frontal sulcus', [], 'frontal'),
    'S_interm_prim-Jensen': ('sulcus of jensen', 'Sulcus intermedius primus (of Jensen)', ['intermediate sulcus', 'jensen sulcus'], 'parietal'),
    'S_intrapariet_and_P_trans': ('intraparietal sulcus', 'Intraparietal sulcus and transverse parietal sulci', ['ips', 'interparietal sulcus'], 'parietal'),
    'S_oc_middle_and_Lunatus': ('lunate sulcus', 'Middle occipital sulcus and lunatus sulcus', ['middle occipital sulcus', 'lunatus sulcus'], 'occipital'),
    'S_oc_sup_and_transversal': ('transverse occipital sulcus', 'Superior occipital sulcus and transverse occipital sulcus', ['superior occipital sulcus'], 'occipital'),
    'S_occipital_ant': ('anterior occipital sulcus', 'Anterior occipital sulcus and preoccipital notch', ['preoccipital notch'], 'occipital'),
    'S_oc-temp_lat': ('occipitotemporal sulcus', 'Lateral occipito-temporal sulcus', ['lateral occipitotemporal sulcus'], 'temporal'),
    'S_oc-temp_med_and_Lingual': ('collateral sulcus', 'Medial occipito-temporal (collateral) sulcus and lingual sulcus', ['medial occipitotemporal sulcus', 'lingual sulcus'], 'occipital'),
    'S_orbital_lateral': ('lateral orbital sulcus', 'Lateral orbital sulcus', [], 'frontal'),
    'S_orbital_med-olfact': ('olfactory sulcus', 'Medial orbital sulcus (olfactory sulcus)', ['medial orbital sulcus'], 'frontal'),
    'S_orbital-H_Shaped': ('orbital sulci', 'Orbital sulci (H-shaped sulci)', ['h-shaped sulcus', 'h shaped sulcus'], 'frontal'),
    'S_parieto_occipital': ('parieto-occipital sulcus', 'Parieto-occipital sulcus', ['parietooccipital sulcus', 'parieto occipital sulcus'], 'occipital'),
    'S_pericallosal': ('callosal sulcus', 'Pericallosal sulcus (sulcus of the corpus callosum)', ['pericallosal sulcus'], 'limbic'),
    'S_postcentral': ('postcentral sulcus', 'Postcentral sulcus', [], 'parietal'),
    'S_precentral-inf-part': ('inferior precentral sulcus', 'Inferior part of the precentral sulcus', [], 'frontal'),
    'S_precentral-sup-part': ('superior precentral sulcus', 'Superior part of the precentral sulcus', [], 'frontal'),
    'S_suborbital': ('suborbital sulcus', 'Suborbital sulcus (rostral sulcus)', ['rostral sulcus'], 'frontal'),
    'S_subparietal': ('subparietal sulcus', 'Subparietal sulcus', ['suprasplenial sulcus'], 'parietal'),
    'S_temporal_inf': ('inferior temporal sulcus', 'Inferior temporal sulcus', [], 'temporal'),
    'S_temporal_sup': ('superior temporal sulcus', 'Superior temporal sulcus', ['sts', 'parallel sulcus'], 'temporal'),
    'S_temporal_transverse': ('transverse temporal sulcus', 'Transverse temporal sulcus', [], 'temporal'),
}

regions = []


def rid(s):
    return s.lower().replace("'", '').replace(' ', '_').replace('-', '_')


for lab, (name, full, al, lobe) in D.items():
    deck = 'gyri' if lab.startswith(('G_', 'Pole_')) else 'sulci'
    if lab.startswith('Lat_Fis'):
        deck = 'sulci'
    regions.append({'id': rid(name), 'name': name, 'full': full, 'aliases': al, 'deck': deck, 'lobe': lobe,
                    'cortex': [lab], 'level': 'detail'})

LOBES = {
    'frontal lobe': 'frontal', 'parietal lobe': 'parietal', 'temporal lobe': 'temporal', 'occipital lobe': 'occipital',
    'insula': 'insula', 'limbic lobe': 'limbic',
}
for name, key in LOBES.items():
    regions.append({'id': rid(name), 'name': name, 'full': name.capitalize(), 'aliases': ['insular cortex', 'insular lobe', 'island of reil'] if key == 'insula' else [],
                    'deck': 'lobes', 'lobe': key, 'cortex': [l for l, v in D.items() if v[3] == key], 'level': 'core'})

AREAS = [
    ('prefrontal cortex', ['pfc'], ['G_front_sup', 'G_front_middle', 'G_front_inf-Opercular', 'G_front_inf-Triangul', 'G_front_inf-Orbital',
                                    'G_and_S_frontomargin', 'G_and_S_transv_frontopol', 'G_orbital', 'G_rectus', 'S_front_sup', 'S_front_middle',
                                    'S_front_inf', 'S_orbital_lateral', 'S_orbital_med-olfact', 'S_orbital-H_Shaped', 'S_suborbital'], None, False),
    ('dorsolateral prefrontal cortex', ['dlpfc'], ['G_front_middle', 'S_front_middle', 'S_front_inf'], None, True),
    ('orbitofrontal cortex', ['ofc'], ['G_orbital', 'G_rectus', 'G_front_inf-Orbital', 'S_orbital_lateral', 'S_orbital_med-olfact', 'S_orbital-H_Shaped'], None, False),
    ("broca's area", ['brocas area', 'broca area', 'broca'], ['G_front_inf-Opercular', 'G_front_inf-Triangul'], 'left', False),
    ('primary motor cortex', ['m1', 'motor cortex'], ['G_precentral'], None, False),
    ('primary somatosensory cortex', ['s1', 'somatosensory cortex'], ['G_postcentral'], None, False),
    ('primary auditory cortex', ['a1', 'auditory cortex'], ['G_temp_sup-G_T_transv'], None, False),
    ("wernicke's area", ['wernickes area', 'wernicke area', 'wernicke'], ['G_temp_sup-Plan_tempo'], 'left', True),
    ('primary visual cortex', ['v1', 'visual cortex', 'striate cortex'], ['S_calcarine'], None, False),
    ('anterior cingulate cortex', ['acc'], ['G_and_S_cingul-Ant', 'G_and_S_cingul-Mid-Ant'], None, False),
    ('posterior cingulate cortex', ['pcc'], ['G_cingul-Post-dorsal', 'G_cingul-Post-ventral'], None, False),
]
HCP_OF = {"broca's area": ['44', '45'], 'primary motor cortex': ['4'], 'primary somatosensory cortex': ['3a', '3b', '1', '2'],
          'primary auditory cortex': ['A1'], 'primary visual cortex': ['V1']}
for name, al, labs, side, approx in AREAS:
    r = {'id': rid(name), 'name': name, 'full': name[0].upper() + name[1:], 'aliases': al, 'deck': 'areas', 'cortex': labs, 'level': 'core'}
    if name in HCP_OF:
        r.pop('cortex'); r['hcp'] = HCP_OF[name]
    if side:
        r['side'] = side
    if approx:
        r['approx'] = True
    regions.append(r)

DEEP = [
    # id, name, aliases, deck, meshes (pair prefix or single), level
    ('thalamus', 'thalamus', [], 'deep', ['thalamus'], 'core'),
    ('caudate_nucleus', 'caudate nucleus', ['caudate'], 'deep', ['caudate'], 'core'),
    ('putamen', 'putamen', [], 'deep', ['putamen'], 'core'),
    ('globus_pallidus', 'globus pallidus', ['pallidum'], 'deep', ['globus_pallidus'], 'core'),
    ('nucleus_accumbens', 'nucleus accumbens', ['accumbens', 'ventral striatum'], 'deep', ['nucleus_accumbens'], 'core'),
    ('hippocampus', 'hippocampus', [], 'deep', ['hippocampus'], 'core'),
    ('amygdala', 'amygdala', [], 'deep', ['amygdala'], 'core'),
    ('lateral_ventricle', 'lateral ventricle', ['lateral ventricles'], 'deep', ['lateral_ventricle'], 'core'),
    ('striatum', 'striatum', ['corpus striatum'], 'deep', ['caudate', 'putamen', 'nucleus_accumbens'], 'core'),
    ('basal_ganglia', 'basal ganglia', ['basal nuclei'], 'deep', ['caudate', 'putamen', 'globus_pallidus', 'nucleus_accumbens', 'substantia_nigra'], 'core'),
    ('substantia_nigra', 'substantia nigra', [], 'brainstem', ['substantia_nigra'], 'core'),
    ('ventral_tegmental_area', 'ventral tegmental area', ['vta'], 'brainstem', ['vta'], 'core'),
    ('red_nucleus', 'red nucleus', [], 'brainstem', ['red_nucleus'], 'detail'),
    ('locus_coeruleus', 'locus coeruleus', ['locus ceruleus'], 'brainstem', ['locus_coeruleus'], 'core'),
    ('raphe_nuclei', 'raphe nuclei', ['raphe'], 'brainstem', ['raphe_nuclei'], 'core'),
    ('midbrain', 'midbrain', ['mesencephalon'], 'brainstem', ['midbrain'], 'core'),
    ('pons', 'pons', [], 'brainstem', ['pons'], 'core'),
    ('medulla_oblongata', 'medulla oblongata', ['medulla'], 'brainstem', ['medulla'], 'core'),
    ('cerebellum', 'cerebellum', [], 'brainstem', ['cerebellum_anterior', 'cerebellum_posterior', 'flocculonodular', 'vermis'], 'core'),
    ('anterior_lobe_of_cerebellum', 'anterior lobe of the cerebellum', ['anterior lobe', 'cerebellar anterior lobe'], 'brainstem', ['cerebellum_anterior'], 'detail'),
    ('posterior_lobe_of_cerebellum', 'posterior lobe of the cerebellum', ['posterior lobe', 'cerebellar posterior lobe'], 'brainstem', ['cerebellum_posterior'], 'detail'),
    ('flocculonodular_lobe', 'flocculonodular lobe', ['flocculus', 'vestibulocerebellum'], 'brainstem', ['flocculonodular'], 'detail'),
    ('vermis', 'vermis', ['cerebellar vermis'], 'brainstem', ['vermis'], 'core'),
    ('anterior_nucleus_of_thalamus', 'anterior nucleus', ['anterior nucleus of the thalamus', 'anterior thalamic nucleus'], 'thalamus', ['thal_anterior'], 'detail'),
    ('mediodorsal_nucleus', 'mediodorsal nucleus', ['dorsomedial nucleus', 'md nucleus'], 'thalamus', ['thal_mediodorsal'], 'detail'),
    ('ventral_anterior_nucleus', 'ventral anterior nucleus', ['va nucleus'], 'thalamus', ['thal_ventral_anterior'], 'detail'),
    ('ventral_lateral_nucleus', 'ventral lateral nucleus', ['vl nucleus'], 'thalamus', ['thal_ventral_lateral'], 'detail'),
    ('ventral_posterolateral_nucleus', 'ventral posterolateral nucleus', ['vpl', 'vpl nucleus'], 'thalamus', ['thal_vpl'], 'detail'),
    ('pulvinar', 'pulvinar', ['pulvinar nucleus'], 'thalamus', ['thal_pulvinar'], 'detail'),
    ('lateral_geniculate_nucleus', 'lateral geniculate nucleus', ['lgn'], 'thalamus', ['thal_lgn'], 'detail'),
    ('medial_geniculate_nucleus', 'medial geniculate nucleus', ['mgn'], 'thalamus', ['thal_mgn'], 'detail'),
]
for i, name, al, deck, meshes, level in DEEP:
    regions.append({'id': i, 'name': name, 'full': name[0].upper() + name[1:], 'aliases': al, 'deck': deck, 'deep': meshes, 'level': level})

# ---------------- SECOND PASS (2026-11-19) ----------------
# HCP-MMP1.0 areas (Glasser et al. 2016). approx = the HCP area is the closest match, not an exact equivalent.
HCP_AREAS = [
    ('premotor cortex', ['pmc', 'premotor area', 'lateral premotor cortex', 'area 6'], ['6a', '6d', '6v', '6r'], 'frontal', False),
    ('supplementary motor area', ['sma', 'sma proper'], ['6mp'], 'frontal', True),
    ('pre-supplementary motor area', ['pre sma', 'presma', 'pre-sma'], ['6ma'], 'frontal', True),
    ('frontal eye field', ['fef', 'frontal eye fields'], ['FEF'], 'frontal', False),
    ('area 55b', ['55b'], ['55b'], 'frontal', False),
    ('inferior frontal junction', ['ifj'], ['IFJa', 'IFJp'], 'frontal', False),
    ('frontopolar cortex', ['frontal pole', 'fpc', 'area 10', 'rostral prefrontal cortex'], ['10pp', 'a10p', 'p10p', '10d'], 'frontal', True),
    ('dorsomedial prefrontal cortex', ['dmpfc'], ['8BM', '9m', '8BL'], 'frontal', True),
    ('ventromedial prefrontal cortex', ['vmpfc'], ['10r', '10v', 'p32', 's32'], 'frontal', True),
    ('subgenual cingulate cortex', ['sgacc', 'subgenual anterior cingulate cortex', 'area 25', 'cg25'], ['25'], 'limbic', False),
    ('anterior insula', ['anterior insular cortex', 'ai'], ['AAIC', 'AVI'], 'insula', True),
    ('posterior insula', ['posterior insular cortex'], ['Ig', 'PoI1', 'PoI2'], 'insula', True),
    ('piriform cortex', ['primary olfactory cortex', 'pir'], ['Pir'], 'frontal', False),
    ('secondary somatosensory cortex', ['s2', 'sii', 'parietal operculum'], ['OP1', 'OP2-3', 'OP4'], 'parietal', True),
    ('lateral intraparietal area', ['lip'], ['LIPv', 'LIPd'], 'parietal', False),
    ('anterior intraparietal area', ['aip'], ['AIP'], 'parietal', False),
    ('temporoparietal junction', ['tpj'], ['TPOJ1', 'TPOJ2', 'TPOJ3', 'STV', 'PSL'], 'parietal', True),
    ('auditory belt', ['belt', 'belt areas', 'auditory belt areas'], ['MBelt', 'LBelt', 'PBelt'], 'temporal', False),
    ('inferior temporal cortex', ['it cortex', 'area te'], ['TE1a', 'TE1m', 'TE1p', 'TE2a', 'TE2p'], 'temporal', True),
    ('entorhinal cortex', ['ec', 'area 28'], ['EC'], 'limbic', False),
    ('perirhinal cortex', ['prc', 'areas 35 and 36'], ['PeEc'], 'limbic', True),
    ('parahippocampal place area', ['ppa'], ['PHA1', 'PHA2', 'PHA3'], 'limbic', True),
    ('retrosplenial cortex', ['rsc', 'retrosplenial complex'], ['RSC'], 'limbic', False),
    ('fusiform face area', ['ffa', 'fusiform face complex', 'ffc'], ['FFC'], 'temporal', True),
    ('secondary visual cortex', ['v2', 'area 18', 'prestriate cortex'], ['V2'], 'occipital', False),
    ('area v3', ['v3', 'visual area 3', 'third visual area'], ['V3'], 'occipital', False),
    ('area v4', ['v4', 'visual area 4'], ['V4'], 'occipital', False),
    ('area mt', ['mt', 'v5', 'area v5', 'middle temporal area', 'mt v5'], ['MT'], 'occipital', False),
    ('lateral occipital complex', ['loc', 'lo'], ['LO1', 'LO2', 'LO3'], 'occipital', True),
]
for name, al, labs, lobe, approx in HCP_AREAS:
    r = {'id': rid(name), 'name': name, 'full': name[0].upper() + name[1:], 'aliases': al, 'deck': 'areas', 'lobe': lobe, 'hcp': labs, 'level': 'core'}
    if approx:
        r['approx'] = True
    regions.append(r)

# Yeo 2011 7 networks (resting-state functional connectivity, 1000 subjects)
NETWORKS = [
    ('visual network', ['vis network', 'visual resting state network'], ['Vis']),
    ('somatomotor network', ['sensorimotor network', 'smn', 'somatomotor'], ['SomMot']),
    ('dorsal attention network', ['dan', 'dorsal attention'], ['DorsAttn']),
    ('salience network', ['ventral attention network', 'van', 'salience ventral attention network', 'cingulo-opercular network'], ['SalVentAttn']),
    ('limbic network', [], ['Limbic']),
    ('frontoparietal control network', ['frontoparietal network', 'fpn', 'control network', 'central executive network', 'fpcn'], ['Cont']),
    ('default mode network', ['dmn', 'default network', 'default mode'], ['Default']),
]
for name, al, nets in NETWORKS:
    regions.append({'id': rid(name), 'name': name, 'full': name[0].upper() + name[1:], 'aliases': al, 'deck': 'networks', 'net': nets, 'level': 'core'})

# white-matter tracts (Juelich histological atlas, maximum probability at 25 %: the dense core of each bundle)
TRACTS = [
    ('corpus_callosum', 'corpus callosum', ['callosum', 'callosal body'], ['tract_callosal'], 'core'),
    ('corticospinal_tract', 'corticospinal tract', ['cst', 'pyramidal tract'], ['tract_cst'], 'core'),
    ('optic_radiation', 'optic radiation', ['optic radiations', 'geniculocalcarine tract'], ['tract_optic'], 'core'),
    ('acoustic_radiation', 'acoustic radiation', ['auditory radiation', 'geniculotemporal radiation'], ['tract_acoustic'], 'detail'),
    ('cingulum', 'cingulum', ['cingulum bundle'], ['tract_cingulum'], 'core'),
    ('superior_longitudinal_fasciculus', 'superior longitudinal fasciculus', ['slf', 'superior longitudinal fascicle'], ['tract_slf'], 'core'),
    ('inferior_fronto_occipital_fasciculus', 'inferior fronto-occipital fasciculus', ['ifof', 'inferior occipitofrontal fasciculus', 'inferior fronto occipital fasciculus'], ['tract_ifof'], 'detail'),
    ('superior_fronto_occipital_fasciculus', 'superior fronto-occipital fasciculus', ['sfof', 'superior occipitofrontal fasciculus'], ['tract_sfof'], 'detail'),
    ('uncinate_fasciculus', 'uncinate fasciculus', ['uf', 'uncinate fascicle'], ['tract_uncinate'], 'core'),
    ('fornix', 'fornix', [], ['tract_fornix'], 'core'),
]
for i, name, al, meshes, level in TRACTS:
    regions.append({'id': i, 'name': name, 'full': name[0].upper() + name[1:], 'aliases': al, 'deck': 'tracts', 'deep': meshes, 'level': level, 'approx': True})

# more deep nuclei. sub = drawn inside a larger structure, shown only when asked about or selected
DEEP2 = [
    ('hypothalamus', 'hypothalamus', [], 'deep', ['hypothalamus'], 'core', 'Diencephalon', False),
    ('subthalamic_nucleus', 'subthalamic nucleus', ['stn', 'corpus luysii', 'nucleus of luys'], 'deep', ['subthalamic_nucleus'], 'core', 'Diencephalon', False),
    ('habenula', 'habenula', ['habenular nuclei', 'habenular nucleus'], 'deep', ['habenula'], 'detail', 'Diencephalon', False),
    ('mammillary_bodies', 'mammillary bodies', ['mammillary body', 'mamillary bodies', 'corpora mammillaria'], 'deep', ['mammillary_body'], 'core', 'Diencephalon', False),
    ('ventral_pallidum', 'ventral pallidum', ['vp'], 'deep', ['ventral_pallidum'], 'detail', None, False),
    ('extended_amygdala', 'extended amygdala', ['bed nucleus of the stria terminalis', 'bnst'], 'deep', ['extended_amygdala'], 'detail', None, False),
    ('globus_pallidus_externus', 'globus pallidus externus', ['gpe', 'external globus pallidus', 'external segment of the globus pallidus'], 'deep', ['gpe'], 'detail', None, True),
    ('globus_pallidus_internus', 'globus pallidus internus', ['gpi', 'internal globus pallidus', 'internal segment of the globus pallidus'], 'deep', ['gpi'], 'detail', None, True),
    ('cornu_ammonis', 'cornu ammonis', ['ca fields', 'ammons horn', 'ca1', 'ca3'], 'deep', ['hipp_ca'], 'detail', None, True),
    ('dentate_gyrus', 'dentate gyrus', ['dg', 'fascia dentata'], 'deep', ['dentate_gyrus'], 'detail', None, True),
    ('subiculum', 'subiculum', [], 'deep', ['subiculum'], 'detail', None, True),
    ('basolateral_amygdala', 'basolateral amygdala', ['laterobasal amygdala', 'bla', 'laterobasal group'], 'deep', ['amyg_lb'], 'detail', None, True),
    ('centromedial_amygdala', 'centromedial amygdala', ['central amygdala', 'centromedial group', 'cea'], 'deep', ['amyg_cm'], 'detail', None, True),
    ('superficial_amygdala', 'superficial amygdala', ['cortical amygdala', 'superficial group'], 'deep', ['amyg_sf'], 'detail', None, True),
    ('substantia_nigra_pars_compacta', 'substantia nigra pars compacta', ['snc', 'pars compacta'], 'brainstem', ['snc'], 'core', None, True),
    ('substantia_nigra_pars_reticulata', 'substantia nigra pars reticulata', ['snr', 'pars reticulata'], 'brainstem', ['snr'], 'detail', None, True),
    ('lateral_posterior_nucleus', 'lateral posterior nucleus', ['lp nucleus', 'lp'], 'thalamus', ['thal_lp'], 'detail', None, False),
    ('intralaminar_nuclei', 'intralaminar nuclei', ['intralaminar nucleus', 'centromedian nucleus', 'cm nucleus'], 'thalamus', ['thal_il'], 'detail', None, False),
]
for i, name, al, deck, meshes, level, cat, sub in DEEP2:
    r = {'id': i, 'name': name, 'full': name[0].upper() + name[1:], 'aliases': al, 'deck': deck, 'deep': meshes, 'level': level}
    if cat:
        r['cat'] = cat
    if sub:
        r['sub'] = True
    regions.append(r)

TITLES = {'area_mt': 'Area MT (V5)', 'area_v3': 'Area V3', 'area_v4': 'Area V4', 'area_55b': 'Area 55b', 'lateral_intraparietal_area': 'Lateral intraparietal area (LIP)',
          'anterior_intraparietal_area': 'Anterior intraparietal area (AIP)', 'secondary_visual_cortex': 'Secondary visual cortex (V2)',
          'secondary_somatosensory_cortex': 'Secondary somatosensory cortex (S2)'}
for r in regions:
    if r['id'] in TITLES:
        r['title'] = TITLES[r['id']]

ids = [r['id'] for r in regions]
assert len(ids) == len(set(ids)), [x for x in ids if ids.count(x) > 1]
geo = json.load(open(os.path.join(HERE, 'atlas_geometry.json'), encoding='utf-8'))
for r in regions:
    for m in r.get('deep', []):
        assert m in geo['deep'] or (m + '_l') in geo['deep'], (r['id'], m)
    for lab in r.get('cortex', []):
        assert lab in geo['destrieux_labels'], (r['id'], lab)
    for lab in r.get('hcp', []):
        assert lab in geo['hcp_labels'], (r['id'], lab)
    for lab in r.get('net', []):
        assert lab in geo['net_labels'], (r['id'], lab)
# no typing name may belong to two regions
seen = {}
for r in regions:
    for a in [r['name']] + r.get('aliases', []):
        k = ''.join(ch for ch in a.lower() if ch.isalnum())
        assert k not in seen or seen[k] == r['id'], ('alias collision', a, seen.get(k), r['id'])
        seen[k] = r['id']
json.dump(regions, open(os.path.join(HERE, 'regions_index.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
from collections import Counter
print(len(regions), 'regions', Counter(r['deck'] for r in regions))
