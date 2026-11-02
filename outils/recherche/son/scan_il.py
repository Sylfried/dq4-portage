import struct, sys
so = open('/home/claude/il2/libil2cpp.so', 'rb').read()
e_phoff = struct.unpack_from('<Q', so, 0x20)[0]; e_phentsize, e_phnum = struct.unpack_from('<HH', so, 0x36)
segs = []
for i in range(e_phnum):
    p_type, p_flags, p_off, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from('<IIQQQQQQ', so, e_phoff + i*e_phentsize)
    if p_type == 1: segs.append((p_vaddr, p_off, p_filesz, p_flags)); print('seg', hex(p_vaddr), hex(p_off), hex(p_filesz), p_flags)
targets = {int(x, 16) for x in sys.argv[1:]}
for v, o, s, fl in segs:
    if not fl & 1: continue
    code = so[o:o+s]
    for i in range(0, len(code) - 3, 4):
        w = struct.unpack_from('<I', code, i)[0]
        if (w >> 26) in (0x25, 0x05):
            imm = w & 0x3ffffff
            if imm & 0x2000000: imm -= 0x4000000
            t = v + i + imm * 4
            if t in targets: print(hex(v + i), 'bl' if w >> 26 == 0x25 else 'b', hex(t))
