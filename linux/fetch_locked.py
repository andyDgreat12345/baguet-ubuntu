"""Build-time fetch of the exact upstream revisions declared in the source."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def main():
    p=argparse.ArgumentParser();p.add_argument('lock',type=Path);p.add_argument('destination',type=Path);a=p.parse_args()
    a.destination.mkdir(parents=True,exist_ok=True)
    for name,item in json.loads(a.lock.read_text()).items():
        if not re.fullmatch(r'[a-z_]+',name) or not re.fullmatch(r'[0-9a-f]{40}',item['commit']):raise SystemExit('Invalid upstream lock')
        target=a.destination/name
        if target.exists():raise SystemExit('Refusing to overwrite upstream checkout')
        subprocess.run(['git','init',str(target)],check=True)
        subprocess.run(['git','-C',str(target),'remote','add','origin',item['repository']],check=True)
        subprocess.run(['git','-C',str(target),'fetch','--depth','1','origin',item['commit']],check=True,timeout=300)
        subprocess.run(['git','-C',str(target),'checkout','--detach','FETCH_HEAD'],check=True)
        actual=subprocess.check_output(['git','-C',str(target),'rev-parse','HEAD'],text=True).strip()
        if actual!=item['commit']:raise SystemExit('Upstream revision mismatch')


if __name__=='__main__':main()
