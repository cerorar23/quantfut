import argparse,sys
from pathlib import Path
from . import build
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();r=build(a.source,a.output)
print({k:r[k] for k in ('rows','aliases_merged','rows_rewritten','still_ambiguous')})
