"""aira_live.Aira that accepts any AIRA Modular personality's identity reply."""
import sys
import mido

sys.path.insert(0, r"C:\Users\admin\Documents\Codex\2026-09-22\files-mentioned-by-the-user-handoff\work\live")
import aira_live


class AiraAny(aira_live.Aira):
    def __init__(self):
        ins = [n for n in mido.get_input_names() if 'AIRA MODULAR CTRL' in n]
        outs = [n for n in mido.get_output_names() if 'AIRA MODULAR CTRL' in n]
        notes = [n for n in mido.get_output_names() if 'AIRA MODULAR' in n and 'CTRL' not in n]
        assert len(ins) == len(outs) == len(notes) == 1, (ins, outs, notes)
        self.ip = mido.open_input(ins[0])
        self.op = mido.open_output(outs[0])
        self.np = mido.open_output(notes[0])
        self.op.send(mido.Message('sysex', data=[0x7e, 0x7f, 6, 1]))
        self.ident = self._rx(lambda d: len(d) >= 10 and d[0] == 0x7e and d[2:5] == [6, 2, 0x41])
        # SCOOPER answers family 0x18, DEMORA 0x16; patch SysEx uses the same model byte.
        aira_live.MODEL = self.ident[5]
        self.dev = self.ident[1]
        self.log = []
