"""Run a bounded matched batch sequentially; never overwrite incomplete output."""
import argparse,json,subprocess,sys,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--matched-experiment',type=Path,required=True)
p.add_argument('--scenarios',nargs='+',choices=['benign','gaussian','targeted'],default=['benign','gaussian','targeted'])
a=p.parse_args();m=json.loads((a.matched_experiment/'manifest.json').read_text())
seed,rounds=m['seed'],m['rounds'];runner=Path(__file__).with_name('run_matched_replication.py')
runner_hash=hashlib.sha256(runner.read_bytes()).hexdigest()
for scenario in dict.fromkeys(a.scenarios):
 attack='targeted' if scenario=='targeted' else 'gaussian'
 arm='benign' if scenario=='benign' else 'attack'
 sigma=0.5 if scenario=='gaussian' else 0.0
 for ead,kd in [('off','off'),('on','off'),('off','on'),('on','on')]:
  name=(f"matched_fedavg_{m['experiment_id'][:12]}_replication_predict3_{attack}"
        f"_sigma{str(sigma).replace('.','p')}_{arm}_original_ead_{ead}_kd_{kd}_seed{seed}_rounds{rounds}")
  directory=Path('outputs/development')/name
  if directory.exists():
   report=directory/'report.json'
   if not report.is_file():raise SystemExit(f'Incomplete directory, inspect before continuing: {directory}')
   r=json.loads(report.read_text())
   if (r.get('status')!='completed' or len(r.get('rounds',[]))!=rounds
       or r.get('matched_experiment_id')!=m['experiment_id'] or r.get('script_sha256')!=runner_hash):
    raise SystemExit(f'Existing output is incomplete or different; preserved: {directory}')
   print(f'REUSE COMPLETED: {directory}',flush=True);continue
  cmd=[sys.executable,'-u',str(runner),'--seed',str(seed),'--rounds',str(rounds),
       '--matched-experiment',str(a.matched_experiment),'--mode','original','--ead',ead,
       '--kd',kd,'--aggregation','fedavg','--attack',attack,'--arm',arm,'--sigma',str(sigma)]
  print('RUN:', ' '.join(cmd),flush=True);subprocess.run(cmd,check=True)
print('MATCHED BATCH: COMPLETE')
