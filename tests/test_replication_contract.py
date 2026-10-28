"""Contract checks for longer horizons and independently seeded initial states."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from ead_dc_fl.matched_experiments import canonical_sha256,file_sha256,load_matched_experiment

class ReplicationContracts(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.settings={'local_epochs':1,'warm_start_rounds':3}
  client=self.root/'clients.json';client.write_text(json.dumps({'clients':[{'client_id':0,'architecture':'small'}]}))
  self.manifest={'schema':'matched_development_v1','seed':123,'rounds':12,
   'training_settings':self.settings,'input_sha256':{'clients.json':file_sha256(client)},
   'initial_models':{},'architectures':['small'],'client_manifest':'clients.json',
   'participation':{str(i):{'small':[0]} for i in range(1,13)}}
  self.write(self.manifest)
 def write(self,m):
  m=copy.deepcopy(m);m['experiment_id']=canonical_sha256({k:v for k,v in m.items() if k!='experiment_id'})
  (self.root/'manifest.json').write_text(json.dumps(m))
 def test_long_horizon_and_new_seed_load(self):
  self.assertEqual(load_matched_experiment(self.root,123,12,self.settings,root=self.root)['rounds'],12)
 def test_seed_and_horizon_must_match(self):
  for seed,rounds in [(42,12),(123,4)]:
   with self.assertRaises(ValueError):load_matched_experiment(self.root,seed,rounds,self.settings,root=self.root)
 def test_missing_later_round_rejected(self):
  m=copy.deepcopy(self.manifest);del m['participation']['12'];self.write(m)
  with self.assertRaises(ValueError):load_matched_experiment(self.root,123,12,self.settings,root=self.root)
 def test_registered_input_change_rejected(self):
  (self.root/'clients.json').write_text('{}')
  with self.assertRaises(ValueError):load_matched_experiment(self.root,123,12,self.settings,root=self.root)
if __name__=='__main__':unittest.main()
