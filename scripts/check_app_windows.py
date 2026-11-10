"""Run upstream's explicit Qt desktop self-check on the actual compiled portable root.

A passing check proves UI/bridge startup under this Windows environment; it does
NOT prove real model downloads, GPU inference, media processing or zero OS cache.
"""
import argparse
import os
from pathlib import Path
import subprocess
import time

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--stage',type=Path,required=True)
    args=p.parse_args()
    launcher=args.stage.resolve()/'WatermarkRemoverAIPortable.exe'
    if not launcher.exists(): raise RuntimeError('Missing compiled portable launcher')
    host_paths=[]
    for key in ('APPDATA','LOCALAPPDATA','PROGRAMDATA'):
        if os.environ.get(key):host_paths.append(Path(os.environ[key])/'WatermarkRemover-AI')
    before={str(path):path.exists() for path in host_paths}
    result=subprocess.run([str(launcher),'--check'],cwd=Path(os.environ.get('RUNNER_TEMP') or os.getcwd()),
                          timeout=180,check=False)
    after={str(path):path.exists() for path in host_paths}
    print('App-specific host-path presence before/after (monitor-only):',before,after,flush=True)
    if result.returncode:raise RuntimeError(f'Actual upstream Qt desktop --check failed with code {result.returncode}')
    assert (args.stage.resolve()/'Data').exists()
    unexpected = args.stage.resolve()/'App/WatermarkRemoverAI/data'
    if unexpected.exists() and any(unexpected.iterdir()):
        raise RuntimeError('Upstream application wrote settings into the App binary folder, not root Data')
    print('AUTOMATED-RUNTIME-TESTED actual Qt desktop --check through compiled PortableApps root launcher')
    print('NOT VERIFIED: model inference, other user accounts, Qt global caches, shell registrations')

if __name__=='__main__':main()
