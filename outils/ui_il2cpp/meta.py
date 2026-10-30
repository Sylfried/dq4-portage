"""Lecture minimale de global-metadata.dat (v31) : valeurs par défaut des champs (données de tableaux statiques)."""
import struct
import os
META = os.environ.get('DQ_META', 'global-metadata.dat')
_b = None; _H = None
def _load():
    global _b, _H
    if _b is None:
        _b = open(META, 'rb').read()
        hdr = struct.unpack_from('<40i', _b, 8)
        names = ['stringLiteral', 'stringLiteralData', 'string', 'events', 'properties', 'methods', 'parameterDefaultValues', 'fieldDefaultValues',
                 'fieldAndParameterDefaultValueData', 'fieldMarshaledSizes', 'parameters', 'fields']
        _H = {n: (hdr[2 * i], hdr[2 * i + 1]) for i, n in enumerate(names)}
def field_default(fname):
    """Octets par défaut du champ nommé fname (à partir du début des données, longueur inconnue : renvoie tout ce qui suit)."""
    _load(); b = _b; H = _H
    so, ss = H['string']; i = b.find(fname.encode() + b'\0', so, so + ss)
    if i < 0: return None
    nameidx = i - so; fo, fs = H['fields']
    hits = {k for k in range(fs // 12) if struct.unpack_from('<i', b, fo + 12 * k)[0] == nameidx}
    dvo, dvs = H['fieldDefaultValues']
    for k in range(dvs // 12):
        fi, ti, di = struct.unpack_from('<iii', b, dvo + 12 * k)
        if fi in hits: return b[H['fieldAndParameterDefaultValueData'][0] + di:][:4096]
    return None
