"""Run committed playground tests without including teammates' untracked drafts.

COSTAR_KIT and COSTAR_KIT_PASSWORD enable the seven real-kit cases; they also
require locally cached Vexcel/Matterport responses. No keys are printed.
"""
from pathlib import Path
import subprocess
import sys
import unittest

root=Path(__file__).resolve().parent.parent
files=subprocess.check_output(['git','-C',str(root),'ls-files','--','playground/test_*.py'],text=True).splitlines()
suite=unittest.defaultTestLoader.loadTestsFromNames([Path(p).stem for p in files])
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
