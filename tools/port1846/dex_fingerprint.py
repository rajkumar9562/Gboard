"""DEX equivalent of the repository's gboardStructuralFingerprint()."""
import hashlib, struct
from dex_reader import uleb

BASE = ('nop move move/from16 move/16 move-wide move-wide/from16 move-wide/16 '
        'move-object move-object/from16 move-object/16 move-result move-result-wide '
        'move-result-object move-exception return-void return return-wide return-object '
        'const/4 const/16 const const/high16 const-wide/16 const-wide/32 const-wide '
        'const-wide/high16 const-string const-string/jumbo const-class monitor-enter '
        'monitor-exit check-cast instance-of array-length new-instance new-array '
        'filled-new-array filled-new-array/range fill-array-data throw goto goto/16 '
        'goto/32 packed-switch sparse-switch cmpl-float cmpg-float cmpl-double '
        'cmpg-double cmp-long if-eq if-ne if-lt if-ge if-gt if-le if-eqz if-nez '
        'if-ltz if-gez if-gtz if-lez').split()
NAMES = dict(enumerate(BASE))
for start, prefix in [(0x44,'aget'),(0x4b,'aput'),(0x52,'iget'),(0x59,'iput'),(0x60,'sget'),(0x67,'sput')]:
    for i,suffix in enumerate(['','-wide','-object','-boolean','-byte','-char','-short']):NAMES[start+i]=prefix+suffix
for start,suffix in [(0x6e,''),(0x74,'/range')]:
    for i,kind in enumerate(['virtual','super','direct','static','interface']):NAMES[start+i]='invoke-'+kind+suffix
for i,n in enumerate(('neg-int not-int neg-long not-long neg-float neg-double int-to-long int-to-float '
                      'int-to-double long-to-int long-to-float long-to-double float-to-int float-to-long '
                      'float-to-double double-to-int double-to-long double-to-float int-to-byte int-to-char int-to-short').split()):NAMES[0x7b+i]=n
math=[]
for kind in ['int','long','float','double']:
    ops=['add','sub','mul','div','rem']+(['and','or','xor','shl','shr','ushr'] if kind in ('int','long') else [])
    math.extend(op+'-'+kind for op in ops)
for i,n in enumerate(math):NAMES[0x90+i]=n;NAMES[0xb0+i]=n+'/2addr'
for i,n in enumerate(['add','rsub','mul','div','rem','and','or','xor']):NAMES[0xd0+i]=n+'-int/lit16'
for i,n in enumerate(['add','rsub','mul','div','rem','and','or','xor','shl','shr','ushr']):NAMES[0xd8+i]=n+'-int/lit8'

def signed(n,bits):return n-(1<<bits) if n&(1<<(bits-1)) else n

def canonical_instruction(index,pos,op,w,ref):
    name=NAMES.get(op)
    if name is None:raise ValueError(f'Unsupported opcode {op:#x}')
    s=f'{index}:{name}'
    if op in (3,6,9):s+=f'|registers={w[1]},{w[2]}'
    elif op in (2,5,8):s+=f'|registers={w[0]>>8},{w[1]}'
    elif op in (0x24,) or 0x6e<=op<=0x72:
        a=w[0]>>12;g=w[0]>>8&15
        regs=[w[2]>>(4*i)&15 for i in range(4)]
        s+='|registers='+','.join(map(str,[a]+regs+[g]))
    elif op in (0x25,) or 0x74<=op<=0x78:s+=f'|range={w[2]},{w[0]>>8}'
    elif 0x2d<=op<=0x31 or 0x44<=op<=0x51 or 0x90<=op<=0xaf:s+=f'|registers={w[0]>>8},{w[1]&255},{w[1]>>8}'
    elif op in (1,4,7,0x20,0x21,0x23) or 0x32<=op<=0x37 or 0x52<=op<=0x5f or 0x7b<=op<=0x8f or 0xb0<=op<=0xcf or 0xd0<=op<=0xd7:
        s+=f'|registers={w[0]>>8&15},{w[0]>>12}'
    elif 0xd8<=op<=0xe2:s+=f'|registers={w[0]>>8},{w[1]&255}'
    elif op==0x12:s+=f'|register={w[0]>>8&15}'
    elif op not in (0,0xe,0x28,0x29,0x2a):s+=f'|register={w[0]>>8}'
    if ref is not None:s+='|reference='+ref
    lit=None
    if op==0x12:lit=signed(w[0]>>12,4)
    elif op in (0x13,0x16) or 0xd0<=op<=0xd7:lit=signed(w[1],16)
    elif op in (0x14,0x17):lit=signed(w[1]|w[2]<<16,32)
    elif op==0x15:lit=signed(w[1]<<16,32)
    elif op==0x18:lit=signed(sum(v<<(16*i) for i,v in enumerate(w[1:])),64)
    elif op==0x19:lit=signed(w[1]<<48,64)
    elif 0xd8<=op<=0xe2:lit=signed(w[1]>>8,8)
    if lit is not None:s+=f'|literal={lit}'
    offset=None
    if op==0x28:offset=signed(w[0]>>8,8)
    elif op==0x29 or 0x32<=op<=0x3d:offset=signed(w[1],16)
    elif op in (0x26,0x2a,0x2b,0x2c):offset=signed(w[1]|w[2]<<16,32)
    if offset is not None:s+=f'|offset={offset}'
    return s

def fingerprint(method):
    regs,args,outs,tries,debug,size=struct.unpack_from('<4H2I',method.dex.b,method.code)
    require_no_payload=False
    lines=[f'registers={regs}']
    for idx,(pos,op,w,ref) in enumerate(method.insns()):
        if op==0 and w[0]:raise ValueError('Payload fingerprint is not implemented')
        lines.append(canonical_instruction(idx,pos,op,w,ref))
    if tries:raise ValueError('Try-region fingerprint is not implemented for this reviewer')
    canonical='\n'.join(lines)
    return hashlib.sha256(canonical.encode()).hexdigest(),canonical

def clear_anchor_fingerprint(owner):
    text=(f'registers=2\n0:const/4|register=0|literal=0\n'
          f'1:iput-object|registers=0,1|reference={owner}->jasondevEnglishAnchorKey:'
          'Lcom/google/android/libraries/inputmethod/widgets/SoftKeyView;\n2:return-void')
    return hashlib.sha256(text.encode()).hexdigest()

if __name__=='__main__':
    import sys
    from dex_reader import Apk
    assert clear_anchor_fingerprint('Lqin;')=='72efbe3504490610a371883613263f90d684fe901ea27b9bcf6d3a3fa9691e45'
    a=Apk(sys.argv[1])
    for ref in sys.argv[2:]:
        h,canonical=fingerprint(a.methods[ref]);print(ref,h)
