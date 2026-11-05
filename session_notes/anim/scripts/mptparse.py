"""Lecture directe d'un fichier MPT du patch (assets/msg/en/bNNNNNNN.mpt), sans le moteur.
En-tete (u32) : 'MPT0', taille, premier id, dernier id, nombre n, debut de la table (0x20), ... ; table : n enregistrements de 6 octets (id - premier id, longueur en octets, decalage / 4) ;
les textes commencent a 0x20 + 6 n + 2 (apres 'fe fe'), chacun aligne sur 4 octets."""
import struct, sys, re
def parse(path):
    d = open(path, 'rb').read()
    sz, first, last, n, tab = struct.unpack('<IIIII', d[4:24]); base = tab + 6 * n + 2
    out = {}
    for k in range(n):
        dl, ln, off = struct.unpack('<HHH', d[tab + 6 * k: tab + 6 * k + 6])
        out[first + dl] = d[base + 4 * off: base + 4 * off + ln].decode('utf-8', 'replace').rstrip('\0')
    return out
def clean(t): return re.sub(r'@[0-9a-z]@?', '|', t)
if __name__ == '__main__':
    for k, v in parse(sys.argv[1]).items(): print(k, repr(v))
