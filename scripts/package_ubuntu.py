#!/usr/bin/env python3
"""Build a source-only ZIP after the public-source check succeeds."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

import check_release


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path,help='Directory outside this source checkout')
    output=parser.parse_args().output.expanduser().resolve()
    base=check_release.BASE
    if output==base or output.is_relative_to(base):
        parser.error('Choose an output directory outside the source checkout')
    if check_release.main():raise SystemExit('Public source check failed')
    if not (base/'VALIDATION.json').is_file():raise SystemExit('Missing validation receipt')
    paths=list(check_release.files())
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='baguet-release-') as temporary:
        stage=Path(temporary)/'baguet-ubuntu';stage.mkdir()
        manifest={}
        for path in paths:
            relative=path.relative_to(base);target=stage/relative
            if path.is_symlink():raise SystemExit('Symlink is not permitted')
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,target)
            manifest[str(relative)]=hashlib.sha256(target.read_bytes()).hexdigest()
        (stage/'SOURCE-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
        archive=Path(temporary)/'Baguet-Ubuntu-24.04.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zipped:
            for path in sorted(stage.rglob('*')):
                if path.is_file():zipped.write(path,path.relative_to(stage.parent))
        with zipfile.ZipFile(archive) as zipped:
            if zipped.testzip():raise SystemExit('Archive integrity check failed')
            for relative,digest in manifest.items():
                if hashlib.sha256(zipped.read('baguet-ubuntu/'+relative)).hexdigest()!=digest:
                    raise SystemExit('Archive source mismatch')
        final=output/archive.name;shutil.copy2(archive,final)
    digest=hashlib.sha256(final.read_bytes()).hexdigest()
    (output/'SHA256SUMS.txt').write_text(digest+'  '+final.name+'\n')
    shutil.copy2(base/'00-OPEN-FIRST.txt',output/'00-OPEN-FIRST.txt')
    shutil.copy2(base/'VALIDATION.json',output/'VALIDATION.json')
    print(json.dumps({'archive':str(final),'bytes':final.stat().st_size,
                      'source_files':len(manifest),'sha256':digest},indent=2))


if __name__=='__main__':main()
