"""Qui lit / ecrit g_field_pad_blink (GOT 0x23e4c0) ?"""
import sys, re, collections
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad')
import scan as SC, plt as P
ins_l = list(SC.balayer())
byaddr = {i.address: k for k, i in enumerate(ins_l)}
regs = {}
hits = []
for k, i in enumerate(ins_l):
    if i.mnemonic == 'adrp':
        r, imm = i.op_str.split(', #'); regs[r] = int(imm, 16)
    if i.mnemonic == 'ldr':
        m = re.match(r'(x\d+), \[(x\d+), #(0x[0-9a-f]+)\]', i.op_str)
        if m and m.group(2) in regs and regs[m.group(2)] + int(m.group(3), 16) == 0x23e4c0:
            hits.append(k)
for k in hits:
    f = SC.fonction(ins_l[k].address)
    print('==', hex(ins_l[k].address), f)
    for j in ins_l[k+1:k+9]:
        if j.mnemonic.startswith('str') or j.mnemonic.startswith('ldr') or j.mnemonic.startswith('mov') or j.mnemonic.startswith('cmp'): print('   ', hex(j.address), j.mnemonic, j.op_str)
