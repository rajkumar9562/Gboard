#!/usr/bin/env python3
"""Validate the partial port's contracts and, optionally, the exact input APKM.

This verifies static evidence only. It does not execute Morphe transformations.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile
import subprocess
import tempfile
from dex_reader import Apk
from android_resources import resources, manifest
from dex_fingerprint import fingerprint, clear_anchor_fingerprint

ROOT = Path(__file__).resolve().parents[2]
PORT = ROOT / 'port-18.4.6'

def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()

def sha(value):
    return hashlib.sha256(compact(value)).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def require(ok, message):
    if not ok:
        raise ValueError(message)

def validate_schema(value, schema, root=None, path='$'):
    root = schema if root is None else root
    if '$ref' in schema:
        node = root
        for part in schema['$ref'].removeprefix('#/').split('/'):
            node = node[part.replace('~1', '/').replace('~0', '~')]
        return validate_schema(value, node, root, path)
    typ = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int,
             'number': (int, float), 'boolean': bool}
    if typ:
        require(isinstance(value, types[typ]), f'{path}: invalid type')
    if 'const' in schema:
        require(value == schema['const'], f'{path}: incorrect constant')
    if 'enum' in schema:
        require(value in schema['enum'], f'{path}: unknown enum value')
    if isinstance(value, dict):
        require(set(schema.get('required', [])) <= value.keys(), f'{path}: missing keys')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False:
            require(value.keys() <= props.keys(), f'{path}: extra keys')
        for key in value.keys() & props.keys():
            validate_schema(value[key], props[key], root, path+'.'+key)
    if isinstance(value, list):
        require(len(value) >= schema.get('minItems', 0), f'{path}: too few items')
        require(len(value) <= schema.get('maxItems', len(value)), f'{path}: too many items')
        if schema.get('uniqueItems'):
            require(len({compact(v) for v in value}) == len(value), f'{path}: duplicate items')
        if 'items' in schema:
            for i, item in enumerate(value):
                validate_schema(item, schema['items'], root, f'{path}[{i}]')
    if isinstance(value, str):
        import re
        require(len(value) >= schema.get('minLength', 0), f'{path}: short string')
        if 'pattern' in schema:
            require(re.search(schema['pattern'], value) is not None, f'{path}: wrong pattern')
    if isinstance(value, (int, float)) and 'minimum' in schema:
        require(value >= schema['minimum'], f'{path}: below minimum')

def contracts():
    bundle = read(PORT/'port-bundle.json')
    reviewed = read(PORT/'reviewed-bindings.json')
    evidence = read(PORT/'static-review.json')
    cat_path = ROOT/'patches/src/main/resources/gboard/gboard-port-product-catalog.json'
    catalog = read(cat_path)
    schema = read(ROOT/'patches/src/bindingCompiler/resources/gboard/gboard-port-bundle.schema.json')
    validate_schema(bundle, schema)
    body = {k: v for k, v in bundle.items() if k != 'bundle_sha256'}
    require(sha(body) == bundle['bundle_sha256'], 'PortBundle digest differs')
    require(hashlib.sha256(cat_path.read_bytes()).hexdigest() == bundle['product_catalog']['sha256'],
            'Catalog digest differs')
    target = bundle['target_contract']
    require(sha(evidence) == target['profile_sha256'] == reviewed['profile_sha256'],
            'Static review linkage differs')
    require(sha(reviewed['bindings']) == target['projection_sha256'] == reviewed['projection_sha256'],
            'Projection digest differs')
    require(reviewed['port_bundle_sha256'] == bundle['bundle_sha256'], 'Profile bundle linkage differs')
    require(reviewed['bindings'] == evidence['bindings'], 'Review exports differ')
    runtime_contracts = read(PORT/'runtime-contracts.json')
    require(sha(runtime_contracts) == evidence['runtime_contracts_sha256'], 'Runtime contract digest differs')
    require(reviewed['target_version'] == target['target_version'] == '18.4.6', 'Wrong target')
    require(reviewed['profile_version'] == target['profile_version'], 'Wrong profile version')
    required = set()
    admitted = {}
    for f, orig in zip(bundle['features'], catalog['features'], strict=True):
        require(f['feature_id'] == orig['feature_id'], 'Feature order/inventory drift')
        originals = {c['contribution_id']: c for c in orig['contributions']}
        for c in f['admitted_contributions']:
            expected = dict(originals[c['contribution_id']])
            for key in ['required_bindings', 'runtime_calls']:
                expected[key] = sorted(expected[key])
            require(c == expected, 'Admitted contribution drift')
            required.update(c['required_bindings'])
        if f['admitted_contributions']:
            admitted[f['feature_id']] = f
    require(required == set(reviewed['bindings']) == {b['key'] for b in target['binding_exports']},
            'Required binding union differs')
    require(set(admitted) == set(evidence['admitted_features']), 'Admitted feature inventory differs')
    for f in admitted.values():
        require(set(f['depends_on_feature_ids']) <= admitted.keys(), 'Missing feature dependency')
    inventory = read(ROOT/'patches-list.json')
    require({p['name'] for p in inventory['patches']} ==
            {f['public_patch_name'] for f in admitted.values()}, 'Published metadata inventory differs')
    expected = {'com.google.android.inputmethod.latin': target['artifact_identity']['version_names']}
    require(all(p['compatiblePackages'] == expected for p in inventory['patches']), 'Wrong metadata target')
    return bundle, reviewed, evidence

def verify_apk(path, reviewed, evidence):
    data = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if 'base.apk' in z.namelist():
            data = z.read('base.apk')
    require(hashlib.sha256(data).hexdigest() == evidence['base_apk_sha256'],
            'This is not the reviewed base APK; stop and remap the port')
    a = Apk(io.BytesIO(data))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        attrs = dict(manifest(z.read('AndroidManifest.xml'))[:2])
        require(attrs['manifest']['versionName'] == evidence['target_version'], 'Manifest version differs')
        require(attrs['manifest']['package'] == 'com.google.android.inputmethod.latin', 'Wrong package')
        r = resources(z.read('resources.arsc'))
        xml = {v['name']: v['value'] for v in r.values() if v['name'].startswith('xml/')}
        require({'xml/settings','xml/settings_legacy','xml/setting_about'} <= xml.keys(),
                'Required settings resources missing')
        about = manifest(z.read(xml['xml/setting_about']))
        version = [attrs for tag, attrs in about if attrs.get('key') == 0x7f140b2d]
        require(len(version) == 1 and version[0]['title'] == 0x7f140b37, 'About XML identity drift')
    stock_strings = {s for d in a.dexes for s in d.strings}
    stock_strings.update(v['value'] for v in r.values() if isinstance(v['value'], str))
    # Some developer defaults are serialized as name=value resource strings.
    stock_strings.update(s.split('=', 1)[0] for s in list(stock_strings) if '=' in s)
    flag_names = [
        'config_max_access_points', 'config_default_access_points_num_on_bar',
        'emoji_scale_supported', 'text_clip_item_char_limit',
        'enable_close_proactive_suggestions_access_point', 'enable_pk_simulator',
        'free_cursor', 'free_cursor_lock_mode', 'enable_device_intelligence',
        'enable_grammar_checker', 'enable_inline_suggestions_on_client_side',
        'more_pill_keys', 'super_insert', 'super_insert_vk', 'enable_use_bluetooth_setting',
    ]
    require(set(flag_names) <= stock_strings, 'Selected stock flag names are missing: '+
            str(sorted(set(flag_names)-stock_strings)))
    for k, b in reviewed['bindings'].items():
        if b['kind'] == 'method':
            ref = b['class_type']+'->'+b['method_name']+'('+''.join(b['parameter_types'])+')'+b['return_type']
            require(ref in a.methods, f'{k}: definition missing: {ref}')
            require(a.methods[ref].code != 0 or a.methods[ref].flags & 0x400,
                    f'{k}: method has neither implementation nor abstract declaration')
        elif b['kind'] == 'field':
            ref = b['class_type']+'->'+b['field_name']+':'+b['field_type']
            require(ref in a.fields, f'{k}: definition missing: {ref}')
        else:
            s = b['source']; src = reviewed['bindings'][s['binding']]
            component = s['component']
            t = src['class_type'] if component == 'owner' else src['field_type'] if component == 'field_type' else src['return_type'] if component == 'return' else src['parameter_types'][s['index']]
            require(t in a.classes, f'{k}: derived class missing')
    checks = []
    def method(key):
        b = reviewed['bindings'][key]
        return a.methods[b['class_type']+'->'+b['method_name']+'('+''.join(b['parameter_types'])+')'+b['return_type']]
    def shape(key, registers=None, tries=None, returns=None, flags=None):
        m = method(key)
        regs, args, outs, catches, debug, size = struct.unpack_from('<4H2I', m.dex.b, m.code)
        if registers is not None: require(regs == registers, key+': register drift')
        if tries is not None: require(catches == tries, key+': exception drift')
        if flags is not None: require(m.flags == flags, key+': access drift')
        if returns is not None:
            actual = [(op, words[0] >> 8) for _, op, words, _ in m.insns() if 0x0e <= op <= 0x11]
            require(actual == returns, key+': return drift: '+str(actual))
        checks.append(key)
        return m
    m = shape('flag_bool_getter', 3, 0, [(0x11, 2)], 0x11)
    require([(op, words[0] >> 8, ref) for _,op,words,ref in m.insns() if op == 0x54] ==
            [(0x54, 32, 'Lodx;->f:Loeg;'), (0x54, 2, 'Loeg;->a:Ljava/lang/Object;')],
            'Flag getter snapshot/result register contract differs')
    m = shape('signature_check', 8, 0, [(0x0f,6),(0x0f,4),(0x0f,3)], 9)
    refs = [ref for _,_,_,ref in m.insns()]
    for ref in ['Lryi;->c(Landroid/content/Context;Ljava/lang/String;)[B',
                'Ljava/util/Arrays;->equals([B[B)Z','Lryi;->e:[B','Lryi;->d:[B',
                'Lryi;->c:[B','Lrxk;->b:Z']:
        require(refs.count(ref) == 1, 'Signature whitelist anchor differs: '+ref)
    require({(words[0] >> 8 & 15, words[0] >> 12) for _,op,words,_ in m.insns() if op == 0x12}
            == {(0,3),(3,0),(4,1),(5,2)}, 'Signature literal contract differs')
    m = shape('frosted_configure', 11)
    require(sum(ref == 'Landroid/view/Window;->setLayout(II)V' for *_,ref in m.insns()) == 1,
            'Frosted Glass Window.setLayout anchor differs')
    shape('calculator_selection', 8)
    m = shape('soft_key_bind', 8, flags=0x11)
    require(sum(op == 0x0f for _,op,_,_ in m.insns()) == 1 and
            struct.unpack_from('<H',m.dex.b,m.code+6)[0] > 0,
            'SoftKey bind return/exception shape differs')
    require(sum(ref == 'SoftKeyView.setSoftKeyDef' for *_,ref in m.insns()) == 1,
            'SoftKey bind trace anchor differs')
    m = shape('pointer_owner', 21, flags=0x10)
    insns = m.insns()
    finish = [i for i,x in enumerate(insns) if x[3] == 'Lqbp;->r(JI)V']
    reset = [i for i,x in enumerate(insns) if x[3] == 'Lqbp;->ac()V']
    require(len(finish) == len(reset) == 1 and reset[0] == finish[0]+1,
            'Pointer finish/pre-reset sequence differs')
    require(insns[0][1:3] == (2,(2,16)) and insns[1][1:3] == (2,(258,17)),
            'Pointer coordinates are no longer copied to v0/v1')
    m = shape('pointer_cancel', 4, 0, [(0x0e,0)], 0x11)
    require([x[1] for x in m.insns()] == [0x54,0x38,0x6e,0x54,0x72,0x12,0x5c,0x0e],
            'Pointer cancel instruction shape differs')
    require([x[3] for x in m.insns() if x[3]] == [
            'Lqbp;->q:Lqlm;','Lqlm;->a(J)V','Lqbp;->r:Lqbq;',
            'Lqbq;->k()V','Lqbp;->O:Z'], 'Pointer cancel targets differ')
    m = shape('pointer_reset', flags=0x11)
    refs = [x[3] for x in m.insns()]
    require(refs.index('Lqbp;->ac()V') == refs.index('Lqbp;->s(J)V')+1,
            'Pointer reset sequence differs')
    m = shape('gesture_dispatch',14,0,[(0x0e,0)],0x11)
    require(m.insns() == [
        (0,0x54,(84,m.insns()[0][2][1]),'Lqbn;->n:Lqbl;'),
        (2,0x78,(3704,m.insns()[1][2][1],0),
         'Lqbl;->h(Lqbp;Lpti;Lpue;Lcom/google/android/libraries/inputmethod/metadata/SoftKeyDef;JZZIZJI)V'),
        (5,0x0e,(14,),None)], 'Gesture forwarding boundary differs')
    runtime_contracts = read(PORT/'runtime-contracts.json')
    for ref in runtime_contracts['method_refs']:
        require(ref in a.methods, 'Runtime reflection method missing: '+ref)
    for ref in runtime_contracts['field_refs']:
        require(ref in a.fields, 'Runtime reflection field/type differs: '+ref)
    require(clear_anchor_fingerprint('Lqin;') ==
            '72efbe3504490610a371883613263f90d684fe901ea27b9bcf6d3a3fa9691e45',
            'Fingerprint implementation failed its upstream known-answer check')
    for key, expected in evidence['stock_fingerprints'].items():
        require(fingerprint(method(key))[0] == expected, 'Stock method fingerprint differs: '+key)
    for rid, vector in runtime_contracts['resource_vectors'].items():
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            nodes = manifest(z.read(r[int(rid,16)]['value']))
        paths = [attrs['pathData'] for tag,attrs in nodes if tag == 'path']
        require(hashlib.sha256('\n'.join(paths).encode()).hexdigest() == vector['path_data_sha256'],
                'Resource vector differs: '+vector['role'])
    m = shape('web_clipboard_create', 12, 6, [(0x0e, 0)], 0x11)
    require(sum(ref == 'Landroid/inputmethodservice/InputMethodService;->onCreate()V'
                for *_,ref in m.insns()) == 1, 'Web Clipboard superclass call differs')
    m = shape('settings_homepage_on_create', 7, 0, [(0x0e,0)], 0x14)
    require(m.insns()[0][3].endswith('->getIntent()Landroid/content/Intent;') and
            sum(ref == 'Lexp;->onCreate(Landroid/os/Bundle;)V' for *_,ref in m.insns()) == 1,
            'Settings lifecycle anchors differ')
    m = shape('latin_globe_factory', 11, 0, [(0x11,0)], 0x1c)
    require(sum(ref == 'Lyji;->h:F' for *_,ref in m.insns()) == 1, 'Latin globe interval anchor differs')
    shape('rounded_keyboard_admission', returns=[(0x0f,0),(0x0f,0)], flags=9)
    shape('rounded_keyboard_style_resolver', returns=[(0x11,3),(0x11,5)], flags=0x11)
    for key in ['cursor_resource_preference','cursor_string_preference']:
        shape(key, flags=0x11)
    require(r[0x7f140913]['value'] == 'clipboard_latest_shown_time', 'Clipboard resource ID differs')
    require(r[0x7f140967]['value'] == 'enable_scrub_move', 'Cursor resource ID differs')
    require(a.classes['Lpbb;']['flags'] == 1 and a.classes['Lpbb;']['super'] ==
            'Landroid/inputmethodservice/InputMethodService;', 'IME service class shape differs')
    return {'dex_classes':len(a.classes), 'defined_methods':len(a.methods),
            'defined_fields':len(a.fields), 'exact_bindings_checked':len(reviewed['bindings']),
            'additional_method_shape_checks':checks,
            'stock_flag_names_present':flag_names,
            'runtime_reflection_methods_checked':len(runtime_contracts['method_refs']),
            'runtime_reflection_fields_checked':len(runtime_contracts['field_refs']),
            'stock_fingerprints_checked':list(evidence['stock_fingerprints']),
            'resource_vectors_checked':len(runtime_contracts['resource_vectors']),
            'resource_checks':['settings','settings_legacy','about preference','clipboard timestamp','cursor preference']}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('apk', type=Path, nargs='?')
    p.add_argument('--report', type=Path)
    p.add_argument('--java-tests', action='store_true', help='Compile and run the standalone metadata regression checks')
    args = p.parse_args()
    bundle, reviewed, evidence = contracts()
    result = {'status':'static-contracts-pass', 'target':evidence['target_version'],
              'admitted_features':len(evidence['admitted_features']),
              'unsupported_features':len(bundle['features'])-len(evidence['admitted_features']),
              'compile_test':'not run', 'patch_application_test':'not run', 'device_test':'not run'}
    if args.apk:
        result['apk_evidence'] = verify_apk(args.apk, reviewed, evidence)
        result['status'] = 'static-apk-checks-pass'
    if args.java_tests:
        java_root = ROOT/'extensions/extension/src/main/java/dev/jason/gboardpatches/extension'
        sources = [java_root/'shared/Gboard1846MetadataArrays.java',
                   java_root/'zhuyinslide/GboardZhuyinSlideRuntimeSupport.java',
                   java_root/'zhuyinslide/GboardZhuyinSlidePolicy.java',
                   java_root/'zhuyinbottomrow/GboardZhuyinBottomRowWeightRuntimeSupport.java',
                   ROOT/'tools/port1846/MetadataArraysSelfTest.java']
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',temp,
                            *map(str,sources)],check=True,capture_output=True,text=True)
            subprocess.run(['java','-cp',temp,'MetadataArraysSelfTest'],check=True,
                           capture_output=True,text=True)
        result['java_subset_compile_and_metadata_tests'] = 'passed; full Android build still untested'
    if args.report:
        args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
