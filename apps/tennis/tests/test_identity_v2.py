import pandas as pd,pytest
from tennis_identity_v2 import build,find_aliases


def frame(rows):
    cols=['circuit','period','tourney_id','winner_id','winner_name','winner_ioc','winner_hand','loser_id','loser_name','loser_ioc','loser_hand']
    return pd.DataFrame(rows,columns=cols)


def base_rows(n=40):
    return [['WTA',f'2026-01-{i%28+1:02d}',f't{i}','wta:1','Éa Star','FRA','R','wta:%d'%(100+i),'Opp %d'%i,None,None] for i in range(n)]


def test_one_off_alias_is_merged_and_original_kept(tmp_path):
    df=frame(base_rows()+[['WTA','2026-01-15','tx','wta:999','Ea Star','FRA',None,'wta:500','Z',None,None]])
    src=tmp_path/'m.parquet';df.to_parquet(src)
    report=build(src,tmp_path/'v')
    out=pd.read_parquet(tmp_path/'v/canonical/matches.parquet')
    assert report['aliases_merged']==1 and out.winner_id.iloc[-1]=='wta:1' and out.winner_id_original.iloc[-1]=='wta:999'


def test_same_tournament_week_or_short_base_is_rejected():
    clash=frame(base_rows()+[['WTA','2026-01-01','t0','wta:999','Ea Star','FRA',None,'wta:500','Z',None,None]])
    assert find_aliases(clash)[0]=={}
    short=frame(base_rows(10)+[['WTA','2026-01-05','tx','wta:999','Ea Star','FRA',None,'wta:500','Z',None,None]])
    assert find_aliases(short)[0]=={}


def test_existing_output_is_never_overwritten(tmp_path):
    src=tmp_path/'m.parquet';frame(base_rows()).to_parquet(src);(tmp_path/'v').mkdir()
    with pytest.raises(ValueError):build(src,tmp_path/'v')
