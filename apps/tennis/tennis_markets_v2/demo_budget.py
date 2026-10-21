"""Separate demo-only accounting reconciles confirmed charges, never guesses."""
from tennis_engine.operations import Capture,now

class DemoCapture(Capture):
 def __init__(self,root,key,transport=None):
  super().__init__(root,key,cap=500,account_reserve=0,transport=transport)
  self.db.execute('CREATE TABLE IF NOT EXISTS confirmed_refunds(snapshot_id TEXT PRIMARY KEY,estimated INTEGER,confirmed INTEGER,recorded_at TEXT)')
  self.db.commit()

 def request(self,path,params=None):
  payload,receipt=super().request(path,params)
  actual=int(receipt['headers']['x-requests-last']);identity=receipt['snapshot_id']
  current=self.db.execute('SELECT cost,state,actual_cost FROM charges WHERE id=?',(identity,)).fetchone()
  # Release only a surplus confirmed by the provider's valid successful receipt.
  if current[1]=='captured' and current[2]==actual and current[0]>actual:
   with self.db:
    self.db.execute('INSERT INTO confirmed_refunds VALUES(?,?,?,?)',(identity,current[0],actual,now()))
    self.db.execute('UPDATE charges SET cost=? WHERE id=?',(actual,identity))
  return payload,receipt
