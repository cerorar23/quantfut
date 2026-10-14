from datetime import date
import importlib.util
from pathlib import Path

import pytest

from qf.ingest import fotmob_history as fm
from qf.ingest.sofascore_history import normalize_bundle
from qf.ingest.fotmob_import import Matcher


@pytest.mark.parametrize('league',['cl.primera','br.serie_b'])
def test_retired_archives_are_rejected_before_normalization_or_matching(league):
    with pytest.raises(ValueError,match='retired_league'):
        fm.collect_fixtures({},league,'2026',date(2024,1,1),date(2026,10,13))
    with pytest.raises(ValueError,match='retired_league'):
        fm.normalize_match({'league_id':league},{},'2026-10-13T12:00:00Z')
    with pytest.raises(ValueError,match='retired_league'):
        normalize_bundle(league,b'invalid original',{})
    with pytest.raises(ValueError,match='retired_league'):
        Matcher({'teams':[],'leagues':[],'aliases':[],'matches':[]},[{'league_id':league}])


def test_resumed_manifest_cannot_download_a_retired_match(tmp_path):
    class Downloader:
        root=tmp_path
        def fetch(self,*args):
            pytest.fail('A retired fixture must not make a network request')
    manifest={'start':'2024-01-01','end':'2026-10-13','complete':True,'errors':[],
              'fixtures':[{'league_id':'br.serie_b','fotmob_match_id':'123'},
                          {'league_id':'cl.primera','fotmob_match_id':'456'}]}
    result=fm.download_details(Downloader(),manifest,workers=1)
    assert result['download_complete'] and result['matches']==0
    assert fm.supported_manifest(dict(manifest,fixtures=[{'league_id':'br.serie_a'}]))['fixtures']==[{'league_id':'br.serie_a'}]


def test_purge_reaches_nested_children_and_rejects_new_fk_cycles():
    spec=importlib.util.spec_from_file_location('retire_leagues',
        Path(__file__).resolve().parents[1]/'scripts/retire_chile_brasil_b.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    fks=[{'child':'raw','parent':'matches'},
         {'child':'players','parent':'raw'},
         {'child':'parley_patas','parent':'parley_tickets'},
         {'child':'parley_results','parent':'parley_patas'}]
    order=module.table_order(fks)
    assert order.index('matches')<order.index('raw')<order.index('players')
    assert order.index('parley_tickets')<order.index('parley_patas')<order.index('parley_results')
    with pytest.raises(ValueError,match='cycle_requires_review'):
        module.table_order(fks+[{'child':'raw','parent':'players'}])
