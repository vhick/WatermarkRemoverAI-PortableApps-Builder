"""Functional compiled-launcher fixture smoke test, without any destructive host mutations.

Uses a separate synthetic upstream PE to assert forwarded args, portable variables,
spaces/Unicode path handling, no host environment changes, and relocation.
"""
import json
import base64
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''
using System;
using System.IO;
using System.Text;
class Program {
 static int Main(string[] args) {
  var result = "{\"data\":\"" + Environment.GetEnvironmentVariable("WMR_DATA_DIR").Replace("\\", "\\\\") +
   "\",\"torch\":\"" + Environment.GetEnvironmentVariable("TORCH_HOME").Replace("\\", "\\\\") +
   "\",\"args_b64\":\"" + Convert.ToBase64String(Encoding.UTF8.GetBytes(String.Join(";",args))) + "\"}";
  File.WriteAllText(Path.Combine(Environment.GetEnvironmentVariable("WMR_DATA_DIR"), "probe.json"), result, Encoding.UTF8);
  return 0;
 }
}
'''

def main():
    if os.name != 'nt':
        raise RuntimeError('Real Windows required for compiled PE smoke test')
    compiler = Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    stage = ROOT / 'work/stage/WatermarkRemoverAIPortable'
    if not stage.is_dir():
        raise RuntimeError('Stage not built')
    with tempfile.TemporaryDirectory(prefix='wmrai launcher ') as td:
        base = Path(td)
        fake = base/'spaces 字符 portable'
        fake.mkdir()
        shutil.copy2(stage/'WatermarkRemoverAIPortable.exe', fake)
        app = fake/'App/WatermarkRemoverAI'
        app.mkdir(parents=True)
        src = base/'Probe.cs'
        src.write_text(PROBE,encoding='utf-8')
        subprocess.run([str(compiler),'/nologo','/target:winexe','/platform:x64','/out:'+str(app/'WatermarkRemover-AI.exe'),str(src)],check=True)
        args = ['--check','hello world','escaped "quotes"','中文']
        inherited = os.environ.get('WMR_DATA_DIR')
        env = os.environ.copy()
        env['WMR_DATA_DIR'] = str(base/'host profile do-not-touch')
        for directory in [fake, base/'moved portable 字符']:
            if directory != fake:
                shutil.move(str(fake),str(directory))
            test = subprocess.run([str(directory/'WatermarkRemoverAIPortable.exe'),*args],cwd=base,
                                  env=env,timeout=30,check=True)
            payload = json.loads((directory/'Data/probe.json').read_text(encoding='utf-8-sig'))
            assert Path(payload['data']).resolve() == (directory/'Data').resolve(),payload
            assert Path(payload['torch']).resolve() == (directory/'Data/models/torch').resolve(),payload
            assert base64.b64decode(payload['args_b64']).decode('utf-8') == ';'.join(args), payload
        assert not (base/'host profile do-not-touch').exists(), 'Fixture wrote to host state'
        assert os.environ.get('WMR_DATA_DIR') == inherited, 'Host process environment modified'
    print('AUTOMATED-RUNTIME-TESTED: compiled launcher, args, Unicode path, relocation, portable environment')

if __name__ == '__main__':
    main()
