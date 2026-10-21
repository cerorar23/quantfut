import json
from tennis_markets_v2.demo_budget import DemoCapture
from tennis_markets_v2.account_identity import is_shared_key

def test_shared_account_alias_is_detected_without_disclosing_value():
 assert is_shared_key('"test-key"',{'ODDS_API_KEY':'test-key'})
 assert not is_shared_key('other-test-key',{'ODDS_API_KEY':'test-key'})
 assert not is_shared_key('test-key',{})

def test_confirmed_lower_cost_releases_only_known_surplus(tmp_path):
 def transport(path,params):
  if path=='sports':return b'[]',{'x-requests-last':'0','x-requests-remaining':'500','x-requests-used':'0'}
  return b'{}',{'x-requests-last':'1','x-requests-remaining':'499','x-requests-used':'1'}
 c=DemoCapture(tmp_path,'test-only',transport);c.request('sports')
 _,receipt=c.request('sports/tennis_wta_test/events/e1/odds',dict(bookmakers='book',markets='h2h,totals,spreads'))
 row=c.db.execute('SELECT cost,actual_cost FROM charges WHERE id=?',(receipt['snapshot_id'],)).fetchone()
 assert row==(1,1)
 assert c.db.execute('SELECT estimated,confirmed FROM confirmed_refunds').fetchone()==(3,1)
 assert c.cap==500 and c.reserve==0

def test_transport_failure_does_not_release_uncertain_reservation(tmp_path):
 def transport(path,params):
  if path=='sports':return b'[]',{'x-requests-last':'0','x-requests-remaining':'500','x-requests-used':'0'}
  raise RuntimeError('simulated failure')
 c=DemoCapture(tmp_path,'test-only',transport);c.request('sports')
 import pytest
 with pytest.raises(RuntimeError):c.request('sports/tennis_wta_test/events/e1/odds',dict(bookmakers='book',markets='h2h,totals,spreads'))
 assert c.db.execute('SELECT sum(cost) FROM charges').fetchone()[0]==3
 assert c.db.execute('SELECT count(*) FROM confirmed_refunds').fetchone()[0]==0 and c.remaining is None
