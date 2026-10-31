"""Read Android string pools, resource names, and manifest attributes."""
import struct, zipfile

def chunks(b,start,end):
    while start<end:
        typ,head,size=struct.unpack_from('<HHI',b,start)
        if not size or start+size>end: raise ValueError('Invalid chunk')
        yield start,typ,head,size
        start+=size

def pool(b,p):
    _,head,size,count,styles,flags,strings,sty=struct.unpack_from('<HH6I',b,p)
    offsets=struct.unpack_from('<'+'I'*count,b,p+head)
    out=[]
    def length(q,wide):
        n=struct.unpack_from('<H' if wide else '<B',b,q)[0];q+=2 if wide else 1
        mask=0x8000 if wide else 0x80
        if n&mask:
            v=struct.unpack_from('<H' if wide else '<B',b,q)[0];q+=2 if wide else 1
            n=((n&~mask)<<(16 if wide else 8))|v
        return n,q
    for off in offsets:
        q=p+strings+off
        n,q=length(q,not flags&0x100)
        if flags&0x100:
            n,q=length(q,False);out.append(b[q:q+n].decode('utf8','replace'))
        else:out.append(b[q:q+2*n].decode('utf-16-le','replace'))
    return out

def resources(b):
    out={};global_pool=[]
    for p,t,h,s in chunks(b,12,len(b)):
        if t==1:global_pool=pool(b,p)
        if t!=0x200:continue
        pid=struct.unpack_from('<I',b,p+8)[0]
        to=struct.unpack_from('<I',b,p+268)[0];ko=struct.unpack_from('<I',b,p+276)[0]
        types=pool(b,p+to);keys=pool(b,p+ko)
        for q,t2,h2,s2 in chunks(b,p+h,p+s):
            if t2!=0x201:continue
            tid,flags,_,count,estart=struct.unpack_from('<BBHII',b,q+8)
            if flags&1: offsets=[struct.unpack_from('<HH',b,q+h2+4*i) for i in range(count)];offsets=[(i,x*4) for i,x in offsets]
            elif flags&2: offsets=[(i,x*4) for i in range(count) if (x:=struct.unpack_from('<H',b,q+h2+2*i)[0])!=0xffff]
            else:offsets=[(i,x) for i in range(count) if (x:=struct.unpack_from('<I',b,q+h2+4*i)[0])!=0xffffffff]
            for idx,off in offsets:
                e=q+estart+off
                es,ef,key=struct.unpack_from('<HHI',b,e)
                if ef&8: continue
                name=types[tid-1]+'/'+keys[key];value=None
                if not ef&1:
                    _,_,vt,v=struct.unpack_from('<HBBI',b,e+es)
                    value=global_pool[v] if vt==3 else v
                out[(pid<<24)|(tid<<16)|idx]={'name':name,'value':value}
    return out

def manifest(b):
    strings=[];out=[]
    for p,t,h,s in chunks(b,8,len(b)):
        if t==1:strings=pool(b,p)
        if t!=0x102:continue
        ns,name,astart,asize,count,_,_,_=struct.unpack_from('<II6H',b,p+16)
        attrs={}
        for i in range(count):
            q=p+16+astart+i*asize
            ns,an,raw,_,_,vt,data=struct.unpack_from('<IIIHBBI',b,q)
            attrs[strings[an]]=strings[raw] if raw!=0xffffffff else strings[data] if vt==3 else data
        out.append((strings[name],attrs))
    return out

if __name__=='__main__':
    import sys,json
    with zipfile.ZipFile(sys.argv[1]) as z:
        r=resources(z.read('resources.arsc'))
        print('resources',len(r))
        for k,v in r.items():
            if any(s.lower() in str(v).lower() for s in sys.argv[2:]):print(hex(k),v)
        for name,attrs in manifest(z.read('AndroidManifest.xml')):
            if name in ('manifest','uses-sdk','service'): print(name,attrs)
