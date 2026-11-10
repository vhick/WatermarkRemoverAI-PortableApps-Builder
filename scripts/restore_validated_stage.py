"""Restore installer input from the *validated ZIP* after runtime smoke tests.

This avoids embedding any Python/Qt runtime test side effects in the installer.
"""
import argparse
from pathlib import Path
from stage import safe_extract
from validate import validate_stage, validate_zip


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--zip',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--version',required=True)
    args=p.parse_args()
    validate_zip(args.zip,args.version)
    stage=safe_extract(args.zip,args.destination,'WatermarkRemoverAIPortable')
    validate_stage(stage,args.version)
    print('Install-stage comes from independently validated original ZIP, not mutated runtime-test directories')

if __name__=='__main__':main()
