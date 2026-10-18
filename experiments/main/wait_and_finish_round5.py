"""Continue the same local computation pipeline after its active main process."""
import psutil,time,json,subprocess,sys
from model import ROOT
matches=[p for p in psutil.process_iter(['cmdline','create_time']) if any('run_round5.py'==str(x).split('\\')[-1] for x in p.info['cmdline'] or []) and '--workers' in (p.info['cmdline'] or [])]
if matches:
    p=max(matches,key=lambda p:p.info['create_time']);print('Waiting for active computation',p.pid,flush=True)
    while p.is_running():
        try:p.wait(timeout=30)
        except psutil.TimeoutExpired:continue
manifest=json.loads((ROOT/'round5_manifest.json').read_text(encoding='utf-8'));assert manifest['groups']==1026 and manifest['states']==len(set(manifest['mapping'].values()))
result=subprocess.run([sys.executable,'-u','finish_round5.py'],cwd=ROOT);sys.exit(result.returncode)
