import numpy as np, sys
from PIL import Image
def L(n): return np.asarray(Image.open('/tmp/m_dc_var_b%d.png' % n).convert('RGB')).astype(np.float32)
a, b = L(int(sys.argv[1])), L(int(sys.argv[2]))
x0, x1, y0, y1 = map(int, sys.argv[3:7])
A = a[y0:y1, x0:x1].mean(-1); 
best = []
for dy in range(-12, 13):
    for dx in range(-4, 5):
        B = b[y0 + dy:y1 + dy, x0 + dx:x1 + dx].mean(-1)
        best.append((np.abs(A - B).mean(), dy, dx))
best.sort(); print(best[:4])
