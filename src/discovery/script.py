"""
Example file

python Tribler/Main/dispersy.py --script template
"""

from dispersy.dprint import dprint
from dispersy.script import ScriptBase

class TestScript(ScriptBase):
    def run(self):
        self.caller(self.test)

    def test(self):
        dprint("testing...")
        assert True
