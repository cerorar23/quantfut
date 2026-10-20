"""Reviewed forecast emission cannot turn a matching name into a live-status proof."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest

spec=importlib.util.spec_from_file_location('reviewed_forecasts',Path(__file__).resolve().parents[1]/'scripts/reviewed_forecasts.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

@pytest.mark.parametrize('short,full',[('M. Kecmanovic','Miomir Kecmanovic'),('T. A. Tirante','Thiago Agustin Tirante'),('F. Diaz Acosta','Facundo Diaz Acosta'),('B. Van De Zandschulp','Botic Van De Zandschulp')])
def test_all_initials_and_complete_surname_match(short,full):
 assert module.abbreviated_matches(short,full)

@pytest.mark.parametrize('short,full',[('M. Kecmanovic','James Kecmanovic'),('T. Tirante','Thiago Agustin Tirante'),('F. Acosta','Facundo Diaz Acosta'),('Boulter','Katie Boulter')])
def test_no_fuzzy_or_incomplete_identity_acceptance(short,full):
 assert not module.abbreviated_matches(short,full)

def test_duplicate_canonical_ids_are_not_silently_chosen():
 model=SimpleNamespace(names={'wta:1':'Katie Boulter','wta:2':'Katie Boulter'})
 with pytest.raises(ValueError,match='ambiguous'):module.canonical_id(model,'Katie Boulter')

def fixture(monkeypatch,status='',live='0',received='2026-10-19T04:20:00Z'):
 proof=dict(official_schedule_earliest='2026-10-19T06:30:00Z')
 monkeypatch.setattr(module,'verify_review',lambda *a:proof)
 review=dict(circuit='ATP',date='2026-10-19',provider_tournament_id='11851',players=['Miomir Kecmanovic','James Duckworth'])
 row=dict(tournament_key=11851,event_date='2026-10-19',tournament_season='2026',event_type_type='Atp Singles',
  event_first_player='M. Kecmanovic',event_second_player='J. Duckworth',event_status=status,event_live=live,event_time='06:30',first_player_key=1,second_player_key=2)
 return review,[(row,dict(received_at=received))]

def test_fresh_future_calendar_remains_research_only(monkeypatch):
 review,rows=fixture(monkeypatch)
 row,receipt,proof,start=module.eligible_event(review,rows,'2026-10-19T04:25:00Z')
 assert start=='2026-10-19T06:30:00+00:00' and row['event_status']==''

@pytest.mark.parametrize('status,live',[('Finished','0'),('Set 1','1'),('Cancelled','0'),('Retired','0'),('unknown','0'),('','1')])
def test_live_or_terminal_cannot_receive_new_prematch_forecast(monkeypatch,status,live):
 review,rows=fixture(monkeypatch,status,live)
 with pytest.raises(ValueError,match='Provider reports'):module.eligible_event(review,rows,'2026-10-19T04:25:00Z')

@pytest.mark.parametrize('received',['2026-10-19T03:00:00Z','2026-10-19T04:26:00Z'])
def test_stale_and_future_observation_rejected(monkeypatch,received):
 review,rows=fixture(monkeypatch,received=received)
 with pytest.raises(ValueError,match='not available or stale'):module.eligible_event(review,rows,'2026-10-19T04:25:00Z')

def test_duplicate_provider_fixture_rejected(monkeypatch):
 review,rows=fixture(monkeypatch)
 with pytest.raises(ValueError,match='Unique'):module.eligible_event(review,rows+rows,'2026-10-19T04:25:00Z')

def test_elapsed_provider_time_or_time_before_official_bound_rejected(monkeypatch):
 review,rows=fixture(monkeypatch);rows[0][0]['event_time']='04:24'
 with pytest.raises(ValueError,match='estimate elapsed'):module.eligible_event(review,rows,'2026-10-19T04:25:00Z')

def test_pdf_cell_rejects_names_from_another_column(monkeypatch):
 class Page:
  mediabox=SimpleNamespace(width=100,height=100)
  def extract_text(self,visitor_text):
   visitor_text('Miomir Kecmanovic',[1,0,0,1,10,80],[1,0,0,1,0,0],None,10)
   visitor_text('vs',[1,0,0,1,10,70],[1,0,0,1,0,0],None,10)
   visitor_text('James Duckworth',[1,0,0,1,80,60],[1,0,0,1,0,0],None,10)
 monkeypatch.setattr(module,'PdfReader',lambda path:SimpleNamespace(pages=[Page()]))
 text=module.cell_text('mock.pdf',[0,.1,.5,.5])
 assert 'miomir kecmanovic' in text and 'vs' in text and 'duckworth' not in text
