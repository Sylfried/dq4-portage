import re,sys
a=open(sys.argv[1],encoding='utf-8').read().split('\n'); b=open(sys.argv[2],encoding='utf-8').read().split('\n')
print(len(a),len(b))
def kind(l):
    m=re.match(r'(\s*)(#+ |[-*] |\d+\. |\||```|===|---|>)?',l)
    return (m.group(1) if m else '', (m.group(2) or '') if m else '', l.strip()=='' )
bad=0
for i,(x,y) in enumerate(zip(a,b),1):
    kx,ky=kind(x),kind(y)
    if kx!=ky:
        print('LINE',i,repr(x[:50]),'|',repr(y[:50])); bad+=1
        if bad>15: break
print('structure mismatches:',bad)
