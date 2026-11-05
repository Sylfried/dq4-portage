"""Lecture minimale d'un fichier de journal du jeu (data1.dat a data5.dat) : de quoi dire s'il est utilisable, sans le charger dans le moteur.

Format (desassemblage de Cryption::Filter 0x152de8 et de Profile::isValidData ; verifie sur les sauvegardes d'un telephone et sur celles ecrites par le moteur) : 15 360 octets chiffres par un flux xorshift32 dont la graine est le CRC32
(polynome 0x7a7b58c6, cle « vb76Eg43 ") ; en clair : mot 0 = « rate » (0x65747261) et mot 1 = 0x0bf697de pour une banque valide, « DWEN » (banque neuve) ou « DLED » (banque supprimee) pour une banque vide ; le mot 2 est la somme
des 0x3660 premiers octets (mot 2 mis a zero). data9.dat (512 octets) n'est qu'un numero de banque : seule sa taille se controle."""
import struct

from dq4_pc.language import tr

KEY, POLY = b'vb76Eg43', 0x7a7b58c6
MAGIE1, MAGIE2 = 0x65747261, 0x0bf697de
NEW, DELETED = 0x4e455744, 0x44454c44
LOGFILE_SIZE, SUM_SIZE = 0x3c00, 0x3660


def _seed():
    s = 0xffffffff
    for ch in KEY:
        s ^= ch
        for _ in range(8): s = ((s >> 1) ^ (-(s & 1) & POLY)) & 0xffffffff
    return ~s & 0xffffffff


def decrypt(raw):
    """Filtre du jeu (xor symetrique : sert aussi a chiffrer)."""
    s = _seed(); out = bytearray(len(raw))
    for i, b in enumerate(raw):
        s ^= (s << 13) & 0xffffffff; s ^= s >> 17; s ^= (s << 5) & 0xffffffff
        out[i] = b ^ (s & 0xff)
    return bytes(out)


def checksum(plain):
    b = bytearray(plain[:SUM_SIZE]); b[8:12] = b'\0\0\0\0'
    return sum(b) & 0xffffffff


def check(name_str, raw):
    """-> None si le fichier est utilisable, sinon la raison (texte pour le joueur). Les tailles sont controlees par l'appelant ; data9.dat n'a pas de somme."""
    if name_str.lower() == 'data9.dat' or len(raw) != LOGFILE_SIZE: return None
    plain = decrypt(raw); m0, m1, ck = struct.unpack_from('<III', plain, 0)
    if m0 in (NEW, DELETED): return None                                      # banque vide : valide, sans somme
    if m0 != MAGIE1 or m1 != MAGIE2: return tr("ce n'est pas un journal du jeu (en-tete inconnu)")
    if ck != checksum(plain): return tr('fichier abime (somme de controle incorrecte)')
    return None
