"""Small read-only DEX inventory reader; no third-party dependencies."""
import struct, zipfile
from dataclasses import dataclass

def uleb(b, p):
    n = s = 0
    while True:
        v = b[p]; p += 1
        n |= (v & 127) << s
        if not v & 128: return n, p
        s += 7

@dataclass
class Method:
    owner: str
    name: str
    params: tuple
    ret: str
    flags: int = 0
    code: int = 0
    dex: object = None
    @property
    def ref(self): return self.owner+'->'+self.name+'('+''.join(self.params)+')'+self.ret
    def insns(self): return self.dex.instructions(self.code) if self.code else []

@dataclass
class Field:
    owner: str
    name: str
    typ: str
    flags: int = 0
    @property
    def ref(self): return self.owner+'->'+self.name+':'+self.typ

class Dex:
    def __init__(self, b):
        self.b = b
        h = struct.unpack_from('<20I', b, 32)
        ss,so,ts,to,ps,po,fs,fo,ms,mo,cs,co = h[6:18]
        self.strings = []
        for i in range(ss):
            p, = struct.unpack_from('<I',b,so+4*i)
            _,p=uleb(b,p)
            self.strings.append(b[p:b.index(b'\0',p)].decode('utf8','replace'))
        self.types=[self.strings[struct.unpack_from('<I',b,to+4*i)[0]] for i in range(ts)]
        self.protos=[]
        for i in range(ps):
            _,r,p=struct.unpack_from('<III',b,po+12*i)
            args=struct.unpack_from('<'+'H'*struct.unpack_from('<I',b,p)[0],b,p+4) if p else ()
            self.protos.append((tuple(self.types[t] for t in args),self.types[r]))
        self.fields=[]
        for i in range(fs):
            c,t,n=struct.unpack_from('<HHI',b,fo+8*i)
            self.fields.append(Field(self.types[c],self.strings[n],self.types[t]))
        self.methods=[]
        for i in range(ms):
            c,p,n=struct.unpack_from('<HHI',b,mo+8*i)
            args,r=self.protos[p]
            self.methods.append(Method(self.types[c],self.strings[n],args,r,dex=self))
        self.classes={}
        for i in range(cs):
            c,a,s,interfaces,source,ann,data,sv=struct.unpack_from('<8I',b,co+32*i)
            item={'type':self.types[c],'super':self.types[s] if s!=0xffffffff else None,'flags':a,'fields':[],'methods':[],'source':self.strings[source] if source!=0xffffffff else None}
            self.classes[self.types[c]]=item
            if not data: continue
            counts=[];p=data
            for j in range(4): n,p=uleb(b,p); counts.append(n)
            for n in counts[:2]:
                idx=0
                for j in range(n):
                    delta,p=uleb(b,p);flags,p=uleb(b,p);idx+=delta
                    f=self.fields[idx]; f.flags=flags;item['fields'].append(f)
            for n in counts[2:]:
                idx=0
                for j in range(n):
                    delta,p=uleb(b,p);flags,p=uleb(b,p);code,p=uleb(b,p);idx+=delta
                    m=self.methods[idx];m.flags=flags;m.code=code;item['methods'].append(m)

    def instructions(self,p):
        b=self.b
        regs,ins,outs,tries,debug,size=struct.unpack_from('<4H2I',b,p)
        words=struct.unpack_from('<'+'H'*size,b,p+16)
        i=0; result=[]
        while i<size:
            w=words[i]; op=w&255; width=WIDTHS[op];ref=None
            if op==0 and w:
                kind=w>>8
                if kind==1: width=4+words[i+1]*2
                elif kind==2: width=2+words[i+1]*4
                elif kind==3: width=4+(words[i+1]*(words[i+2]|words[i+3]<<16)+1)//2
            if op in (0x1a,0x1b):
                idx=words[i+1] if op==0x1a else words[i+1]|words[i+2]<<16
                ref=self.strings[idx]
            elif op in (0x1c,0x1f,0x20,0x22,0x23,0x24,0x25): ref=self.types[words[i+1]]
            elif 0x52<=op<=0x6d: ref=self.fields[words[i+1]].ref
            elif 0x6e<=op<=0x72 or 0x74<=op<=0x78: ref=self.methods[words[i+1]].ref
            result.append((i,op,words[i:i+width],ref))
            i+=width
        return result

WIDTHS=[1]*256
for op in [0x02,0x05,0x08,0x13,0x15,0x16,0x19,0x1a,0x1c,0x1f,0x20,0x22,0x23,0x29,*range(0x2d,0x3e),*range(0x44,0x6e),*range(0x90,0xb0),*range(0xd0,0xe3),0xfe,0xff]: WIDTHS[op]=2
for op in [0x03,0x06,0x09,0x14,0x17,0x1b,0x24,0x25,0x26,0x2a,0x2b,0x2c,*range(0x6e,0x73),*range(0x74,0x79),0xfc,0xfd]: WIDTHS[op]=3
WIDTHS[0x18]=5;WIDTHS[0xfa]=4;WIDTHS[0xfb]=4

class Apk:
    def __init__(self,path):
        with zipfile.ZipFile(path) as z:
            self.dexes=[Dex(z.read(n)) for n in z.namelist() if n.endswith('.dex')]
        self.classes={k:v for d in self.dexes for k,v in d.classes.items()}
        self.methods={m.ref:m for c in self.classes.values() for m in c['methods']}
        self.fields={f.ref:f for c in self.classes.values() for f in c['fields']}
    def dump(self,typ):
        c=self.classes[typ]
        print(c['type'],'extends',c['super'],'source',c['source'])
        for f in c['fields']:print('  FIELD',f.ref,hex(f.flags))
        for m in c['methods']:
            print('  METHOD',m.ref,hex(m.flags))
            refs=[r for _,op,_,r in m.insns() if r is not None and op in (0x1a,0x1b)]
            if refs:print('    STRINGS',refs[:35])

if __name__=='__main__':
    import sys
    a=Apk(sys.argv[1])
    print('classes',len(a.classes),'methods',len(a.methods),'fields',len(a.fields))
    for typ in sys.argv[2:]:a.dump(typ)
