"""Frozen-origin temporal research evaluation; no odds or financial claims."""
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit
from .ingest import save_json
from .model import training_rows, train, ServeModel
from .scoring import Rules, match_win, match_distribution, market


def elo_ratings(df):
    overall=defaultdict(lambda:1500.)
    surface=defaultdict(lambda:1500.)
    # No match_num assumption: all observations in one source period update together.
    for _,block in df.groupby('period',sort=True):
        delta,ds=defaultdict(float),defaultdict(float)
        for row in block.itertuples():
            a,b,s=row.winner_id,row.loser_id,row.surface
            p=1/(1+10**((overall[b]-overall[a])/400))
            ps=1/(1+10**((surface[(b,s)]-surface[(a,s)])/400))
            delta[a]+=24*(1-p);delta[b]-=24*(1-p)
            ds[(a,s)]+=24*(1-ps);ds[(b,s)]-=24*(1-ps)
        for key,value in delta.items(): overall[key]+=value
        for key,value in ds.items(): surface[key]+=value
    return overall,surface


def scores(y,p):
    y,p=np.array(y),np.clip(np.array(p),1e-8,1-1e-8)
    return {'n':len(y),'log_loss':float(-np.mean(y*np.log(p)+(1-y)*np.log1p(-p))),
            'brier':float(np.mean((p-y)**2)),'accuracy':float(np.mean((p>=.5)==y))}


def evaluate(root,output,circuit,test_year=2026):
    if test_year<2025: raise ValueError('Use a predeclared contemporary held-out year')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    cutoff=f'{test_year}-01-01'
    train(root,output/'model',circuit,cutoff)
    training=training_rows(root,circuit,cutoff)
    overall,surface=elo_ratings(training)
    model=ServeModel(output/'model',uncertainty=False)
    df=pd.read_parquet(Path(root)/'canonical/matches.parquet')
    test=df.loc[df.circuit.eq(circuit)&df.eligible_model&df.source_group.eq('tour')&df.period.ge(cutoff)&df.period.lt(f'{test_year+1}-01-01')].copy()
    rng=np.random.default_rng(20261016)
    results=[]
    for i,row in enumerate(test.itertuples()):
        # Random presentation prevents winner-first labels from inflating accuracy.
        y=int(rng.integers(2))
        a,b=(row.winner_id,row.loser_id) if y else (row.loser_id,row.winner_id)
        pred=model.predict(a,b,row.surface,uncertainty=False)
        final_tb=10 if row.tourney_level=='G' else 7
        rules=Rules(best_of=int(row.best_of),deciding_tiebreak=final_tb)
        prob=match_win(pred['p'],pred['q'],rules)
        global_elo=1/(1+10**((overall[b]-overall[a])/400))
        blended=1/(1+10**(((overall[b]-overall[a])+(surface[(b,row.surface)]-surface[(a,row.surface)]))/800))
        results.append({'match_id':row.match_id,'period':row.period,'surface':row.surface,'a':a,'b':b,'y':y,
                        'model_probability':prob,'elo_probability':global_elo,'surface_elo_probability':blended})
        if (i+1)%1000==0: print(f'{circuit}: evaluated {i+1}/{len(test)}',flush=True)
    if not results: raise ValueError('No held-out matches')
    observations=pd.DataFrame(results)
    observations.to_parquet(output/'heldout_predictions.parquet',index=False)
    metrics={key:scores(observations.y,observations[col]) for key,col in [('serve_return_markov','model_probability'),('elo','elo_probability'),('blended_surface_elo','surface_elo_probability')]}
    # Paired source-period block bootstrap, not independent market/row resampling.
    best_baseline=min(('elo_probability','surface_elo_probability'),key=lambda k:scores(observations.y,observations[k])['log_loss'])
    def losses(p):
        p=np.clip(p,1e-8,1-1e-8);y=observations.y.to_numpy()
        return -(y*np.log(p)+(1-y)*np.log1p(-p))
    paired=losses(observations.model_probability)-losses(observations[best_baseline])
    blocks=pd.DataFrame({'period':observations.period,'loss':paired}).groupby('period').loss.agg(['sum','count'])
    differences=[]
    for _ in range(1000):
        draw=rng.integers(len(blocks),size=len(blocks))
        chosen=blocks.iloc[draw]
        differences.append(chosen['sum'].sum()/chosen['count'].sum())
    report={'circuit':circuit,'test_year':test_year,'metrics':metrics,
            'model_log_loss_minus_best_elo':{'baseline':best_baseline,'mean':float(paired.mean()),'period_block_ci95':np.quantile(differences,[.025,.975]).tolist()},
            'origin':cutoff,'training_latest_period':training.period.max(),'test_first_period':test.period.min(),'test_last_period':test.period.max(),
            'protocol':'Frozen pre-year model and Elo; no within-test updates or hyperparameter selection; 35-day training embargo.',
            'probability_method':'MAP serve probabilities passed through Markov. Uncertainty is not integrated in this initial held-out comparison.',
            'limitations':['Retrospective research, historical publication time unverified.','Tournament date may be a period label, not actual start time.','No odds, CLV, ROI or operational accuracy claims.','Scores restricted to conventional completed matches.','Baseline choice reported on this test; not a model-selection result.'],
            'production_approved':False}
    save_json(output/'evaluation.json',report)
    return report


def observed_markets(row,a_is_winner):
    import re
    sets=[tuple(map(int,re.match(r'(\d+)-(\d+)',token).groups())) for token in row.score.split()]
    ga=sum(a for a,b in sets);gb=sum(b for a,b in sets)
    if not a_is_winner: ga,gb=gb,ga
    return {'over_22_5_games':int(ga+gb>22.5),'A_minus_3_5_games':int(ga-gb>3.5),
            'any_tiebreak':int(any({a,b}=={6,7} for a,b in sets)),
            'first_set_A':int((sets[0][0]>sets[0][1])==a_is_winner)}


def evaluate_markets(root,output):
    """Validate fixed illustrative lines; no bookmaker prices or line selection."""
    output=Path(output)
    summary=json.loads((output/'evaluation.json').read_text())
    model=ServeModel(output/'model',uncertainty=False)
    source=pd.read_parquet(Path(root)/'canonical/matches.parquet').set_index('match_id',verify_integrity=True)
    held=pd.read_parquet(output/'heldout_predictions.parquet')
    history=training_rows(root,summary['circuit'],summary['origin'])
    history=history.loc[history.source_group.eq('tour')]
    frequency=defaultdict(lambda:defaultdict(lambda:[1.,2.]))
    for row in history.itertuples():
        a=observed_markets(row,True);b=observed_markets(row,False)
        for key in a:
            count=frequency[(row.surface,row.best_of)][key]
            count[0]+=.5*(a[key]+b[key]);count[1]+=1
    records=[]
    for i,match in enumerate(held.itertuples()):
        row=source.loc[match.match_id]
        pred=model.predict(match.a,match.b,row.surface,uncertainty=False)
        rules=Rules(int(row.best_of),deciding_tiebreak=10 if row.tourney_level=='G' else 7)
        dist=match_distribution(pred['p'],pred['q'],rules)
        specs={'over_22_5_games':('games_total',22.5,'over'),'A_minus_3_5_games':('games_handicap',-3.5,'A'),
               'any_tiebreak':('tiebreak',None,'yes'),'first_set_A':('first_set',None,'A')}
        actual=observed_markets(row,match.a==row.winner_id)
        for key,(kind,line,selection) in specs.items():
            count=frequency[(row.surface,row.best_of)][key]
            records.append({'match_id':match.match_id,'market':key,'y':actual[key],
                            'probability':market(dist,kind,line,selection)['win'],'frequency_baseline':count[0]/count[1]})
        if (i+1)%500==0: print(f"{summary['circuit']}: joint market evaluation {i+1}/{len(held)}",flush=True)
    data=pd.DataFrame(records)
    data.to_parquet(output/'heldout_markets.parquet',index=False)
    results={key:{'model':scores(group.y,group.probability),'training_frequency':scores(group.y,group.frequency_baseline)} for key,group in data.groupby('market')}
    report={'circuit':summary['circuit'],'test_year':summary['test_year'],'metrics':results,
            'scope':'Fixed illustrative half lines, completed matches, frozen-origin MAP probabilities; no bookmaker quotes or EV.',
            'production_approved':False}
    save_json(output/'market_evaluation.json',report)
    return report
