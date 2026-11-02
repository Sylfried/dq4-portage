#!/usr/bin/env python3
"""Lecture/ecriture des fichiers data1..5.dat / data9.dat de DQ4 (Android) hors moteur.
Chiffrement = Cryption::Filter(lib+0x152de8) : cle "vb76Eg43", polynome 0x7a7b58c6 (CRC32 bit a bit, init ~0, sortie inversee) -> graine d'un xorshift32 (13,17,5) ; octet ^= octet bas de l'etat.
Usage : dq4_sauvegarde.py <dataN.dat> [--dump]
"""
import sys, struct
POLY, CLE = 0x7a7b58c6, b'vb76Eg43'
def graine():
    s = 0xffffffff
    for ch in CLE:
        s ^= ch
        for _ in range(8):
            s = ((s >> 1) ^ (-(s & 1) & POLY)) & 0xffffffff
    return ~s & 0xffffffff
def filtre(data):
    s = graine(); out = bytearray()
    for b in data:
        s ^= (s << 13) & 0xffffffff; s ^= s >> 17; s ^= (s << 5) & 0xffffffff
        out.append(b ^ (s & 0xff))
    return bytes(out)
MAGIE1, MAGIE2 = 0x65747261, 0x0bf697de     # "rate" + constante ; entete valide (Profile::isValidData)
NEW, DEL = 0x4e455744, 0x44454c44           # "DWEN" = banque vide/neuve ; "DLED" = banque supprimee (killbank(n, false))
def analyser(clair):
    n = len(clair); r = {'taille': n}
    w0, w1, ck = struct.unpack_from('<III', clair, 0)
    r['mot0'] = '%08x' % w0
    if n < 0x3000: r['etat'] = 'data9 : mot0 = banque la plus recente = %d' % (0 if w0 == NEW else w0); return r
    if w0 == NEW: r['etat'] = 'vide (DWEN)'; return r
    if w0 == DEL: r['etat'] = 'supprimee (DLED)'; return r
    r['valide'] = (w0 == MAGIE1 and w1 == MAGIE2)
    tmp = bytearray(clair); tmp[8:12] = b'\0\0\0\0'
    calc = sum(tmp[:0x3660]) & 0xffffffff
    r['somme'] = (ck, calc, ck == calc)
    r['banque_stage'], r['typeSave'], r['pad_pos'], r['pad_size'] = clair[0xc], clair[0xd], clair[0xe], clair[0xf]
    r['chapitre'] = clair[0x30]; r['carte'] = clair[0x10:0x18].split(b'\0')[0].decode('latin-1')
    r['nom'] = clair[0x497:0x497 + 0x20].split(b'\0')[0].decode('utf-8', 'replace')
    r['duree'] = struct.unpack_from('<I', clair, 0x25c)[0] if n > 0x260 else None
    return r
if __name__ == '__main__':
    p = sys.argv[1]; d = open(p, 'rb').read(); c = filtre(d)
    print(analyser(c))
    if '--dump' in sys.argv: open(p + '.clair', 'wb').write(c)
