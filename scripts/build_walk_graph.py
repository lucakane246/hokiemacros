import xml.etree.ElementTree as ET, json, math, sys
sys.path.insert(0,'.'); from geo import pix
K=3200/3776
WALK={'footway','path','pedestrian','steps','service','residential','living_street','tertiary','tertiary_link','secondary','secondary_link','primary','primary_link','unclassified','cycleway','track','corridor','road'}
X0,Y0,X1,Y1=506-150,-474-150,3245+150,2108+150   # map rect plus a margin
nodes={}; ways=[]
for ev,el in ET.iterparse('merged.osm'):
    if el.tag=='node':
        nodes[el.get('id')]=(float(el.get('lat')),float(el.get('lon')))
    elif el.tag=='way':
        tags={t.get('k'):t.get('v') for t in el.findall('tag')}
        h=tags.get('highway')
        if h in WALK and tags.get('foot')!='no' and tags.get('access') not in ('private','no') and tags.get('area')!='yes':
            ways.append([nd.get('ref') for nd in el.findall('nd')])
        el.clear()
print(len(nodes),'nodes',len(ways),'walkable ways')
idx={}; pts=[]; adj={}
def nid(ref):
    if ref not in idx:
        la,lo=nodes[ref]; x,y=pix(la,lo); idx[ref]=len(pts); pts.append((round(x*K,1),round(y*K,1)))
    return idx[ref]
edges=set()
for w in ways:
    w=[r for r in w if r in nodes]
    for a,b in zip(w,w[1:]):
        pa,pb=pix(*nodes[a]),pix(*nodes[b])
        if not any(X0<=p[0]*K<=X1 and Y0<=p[1]*K<=Y1 for p in (pa,pb)): continue
        i,j=nid(a),nid(b)
        if i!=j: edges.add((min(i,j),max(i,j)))
# keep the largest connected component
par=list(range(len(pts)))
def f(x):
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
for i,j in edges: par[f(i)]=f(j)
from collections import Counter
big=Counter(f(i) for i in range(len(pts))).most_common(1)[0][0]
keep=[i for i in range(len(pts)) if f(i)==big]; remap={o:n for n,o in enumerate(keep)}
P=[pts[i] for i in keep]; E=[(remap[i],remap[j]) for i,j in edges if i in remap and j in remap]
# simplify degree-2 chains? keep simple: store flat arrays
out={'p':[v for xy in P for v in (round(xy[0]),round(xy[1]))],'e':[v for e in E for v in e]}
# scale: metres per map unit
la1,lo1=37.229,-80.424; la2,lo2=37.229,-80.414
x1,_=pix(la1,lo1); x2,_=pix(la2,lo2)
m=6371000*math.radians(10e-3)*math.cos(math.radians(37.229))
out['m']=round(m/((x2-x1)*K),5)
s=json.dumps(out,separators=(',',':')); open('walk.json','w').write(s)
print(len(P),'graph nodes',len(E),'edges',len(s)//1024,'KB', 'm/unit',out['m'])

# ---- simplify: drop degree-2 nodes that sit (almost) on a straight line between their neighbours
from collections import defaultdict
nb=defaultdict(set)
for i,j in E: nb[i].add(j); nb[j].add(i)
alive=set(range(len(P)))
def off(a,b,c):
    (ax,ay),(bx,by),(cx,cy)=P[a],P[b],P[c]; L=math.hypot(cx-ax,cy-ay) or 1e-9
    return abs((cx-ax)*(ay-by)-(ax-bx)*(cy-ay))/L
changed=True
while changed:
    changed=False
    for b in list(alive):
        if len(nb[b])!=2: continue
        a,c=nb[b]
        if c in nb[a]: continue
        if off(a,b,c)<1.2:
            nb[a].discard(b); nb[c].discard(b); nb[a].add(c); nb[c].add(a); alive.discard(b); del nb[b]; changed=True
keep=sorted(alive); rm={o:n for n,o in enumerate(keep)}
P2=[P[i] for i in keep]; E2=sorted({(min(rm[i],rm[j]),max(rm[i],rm[j])) for i in keep for j in nb[i]})
out['p']=[v for xy in P2 for v in (round(xy[0]),round(xy[1]))]; out['e']=[v for e in E2 for v in e]
s=json.dumps(out,separators=(',',':')); open('walk.json','w').write(s)
import gzip; print('simplified:',len(P2),'nodes',len(E2),'edges',len(s)//1024,'KB, gz',len(gzip.compress(s.encode()))//1024,'KB')
