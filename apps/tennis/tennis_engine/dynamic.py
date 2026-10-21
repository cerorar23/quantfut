"""Exploratory Gaussian state filter for serve/return skills.

Each source period is updated as one block. Gaussian random-walk variance grows
with elapsed time. A block Laplace MAP is computed, then its covariance is
projected to a diagonal approximation; cross-effect uncertainty is not retained.
This is an experimental assumed-density filter, not full Bayesian inference.
"""
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import minimize
from scipy.special import expit,logit
from .ingest import save_json
from .scoring import Rules,match_win
from .evaluate import scores,elo_ratings


def context_from_row(row,server_is_winner=True):
    a,b=('winner','loser') if server_is_winner else ('loser','winner')
    return {'server_age':getattr(row,a+'_age',None),'returner_age':getattr(row,b+'_age',None),
            'server_hand':getattr(row,a+'_hand',None),'returner_hand':getattr(row,b+'_hand',None),
            'indoor':getattr(row,'indoor',None)}


def context_terms(context):
    c=context or {};out={}
    for role in ('server','returner'):
        age=c.get(role+'_age')
        try: age=float(age)
        except (ValueError,TypeError): age=float('nan')
        if np.isfinite(age) and 12<=age<=65:
            out['context|'+role+'_age']=float(np.clip((age-25)/10,-2,4))
        else:out['context|'+role+'_age_missing']=1.
        hand=c.get(role+'_hand')
        if isinstance(hand,str) and hand.upper() in ('L','R'):
            out['context|'+role+'_left']=float(hand.upper()=='L')
        else:out['context|'+role+'_hand_missing']=1.
    indoor=str(c.get('indoor','')).strip().lower()
    if indoor in ('true','1','1.0','i','indoor'):out['context|indoor']=1.
    elif indoor in ('false','0','0.0','o','outdoor'):out['context|indoor']=0.
    else:out['context|indoor_missing']=1.
    return out


class DynamicServe:
    def __init__(self,circuit,with_context=False,process_sd_per_year=.20):
        if circuit not in ('ATP','WTA') or not 0<=process_sd_per_year<=1:raise ValueError('Invalid state configuration')
        self.circuit=circuit;self.with_context=with_context;self.process_sd=process_sd_per_year
        self.states={};self.last_updated_period=None;self.periods=0;self.matches=0;self.iterations=0

    def design(self,a,b,surface,context=None):
        if a==b or surface not in ('Hard','Clay','Grass','Carpet'):raise ValueError('Invalid players/surface')
        out={'intercept':1.,'serve|'+a:1.,'return|'+b:-1.,
             'serve_surface|'+a+'|'+surface:1.,'return_surface|'+b+'|'+surface:-1.}
        if surface!='Hard':out['surface|'+surface]=1.
        if self.with_context:out.update(context_terms(context))
        return {k:v for k,v in out.items() if v}

    def prior(self,key,at):
        at=pd.Timestamp(at)
        if key in self.states:
            mean,var,last=self.states[key];last=pd.Timestamp(last)
            if at<last:raise ValueError('Cannot project state backwards')
            # Only player skills diffuse; contextual coefficients stay static.
            diffusion=self.process_sd if key.startswith(('serve|','return|','serve_surface|','return_surface|')) else 0.
            return mean,var+diffusion**2*(at-last).days/365.25
        mean=float(logit(.62 if self.circuit=='ATP' else .58)) if key=='intercept' else 0.
        sd=.6 if key=='intercept' else .1 if key.startswith('context|') else .18 if '_surface|' in key else .25 if key.startswith('surface|') else .35
        return mean,sd**2

    def predict(self,a,b,surface,at,context_a=None,context_b=None):
        result=[]
        for server,returner,c in ((a,b,context_a),(b,a,context_b)):
            terms=self.design(server,returner,surface,c)
            priors={k:self.prior(k,at) for k in terms}
            mean=sum(terms[k]*priors[k][0] for k in terms)
            variance=sum(terms[k]**2*priors[k][1] for k in terms)
            result.append((float(expit(mean)),mean,variance))
        return {'p':result[0][0],'q':result[1][0],
                'logit_variances_diagonal':[result[0][2],result[1][2]],
                'probability_method':'MAP logits; diagonal filtering approximation; not posterior-integrated'}

    def update(self,frame,period):
        if frame.empty:return
        if self.last_updated_period and pd.Timestamp(period)<=pd.Timestamp(self.last_updated_period):
            raise ValueError('Each source period must be assimilated once in increasing order')
        if not frame.period.eq(period).all():raise ValueError('One exact source period per block required')
        designs=[];n=[];y=[]
        for row in frame.sort_values('match_id').itertuples():
            for a,b,prefix,winning in ((row.winner_id,row.loser_id,'w',True),(row.loser_id,row.winner_id,'l',False)):
                designs.append(self.design(a,b,row.surface,context_from_row(row,winning)))
                n.append(float(getattr(row,prefix+'_svpt')))
                y.append(float(getattr(row,prefix+'_1stWon')+getattr(row,prefix+'_2ndWon')))
        n=np.asarray(n);y=np.asarray(y)
        if not (np.isfinite(n+y).all() and (n>0).all() and (y>=0).all() and (y<=n).all()):
            raise ValueError('Invalid binomial observations')
        keys=sorted({k for d in designs for k in d});index={k:i for i,k in enumerate(keys)}
        rr=[];cc=[];vv=[]
        for i,d in enumerate(designs):
            for key,v in d.items():rr.append(i);cc.append(index[key]);vv.append(v)
        X=sparse.csr_matrix((vv,(rr,cc)),shape=(len(n),len(keys)))
        priors=[self.prior(k,period) for k in keys]
        means=np.array([p[0] for p in priors]);precision=1/np.array([p[1] for p in priors])
        scale=1/np.sqrt(precision);Z=X.multiply(scale).tocsr();offset=X@means
        # Optimize in prior-standardized coordinates to avoid badly conditioned
        # precisions after some skills accumulate much more data than others.
        def objective(theta):
            eta=offset+Z@theta
            return (float(np.sum(n*np.logaddexp(0,eta)-y*eta)+.5*np.dot(theta,theta)),
                    Z.T@(n*expit(eta)-y)+theta)
        fitted=minimize(objective,np.zeros(len(keys)),jac=True,method='L-BFGS-B',
                        options={'maxiter':500,'ftol':1e-10,'gtol':1e-5})
        if not fitted.success:raise RuntimeError('State block did not converge: '+str(fitted.message))
        beta=means+scale*fitted.x
        p=expit(X@beta)
        diagonal=np.asarray(X.power(2).T@(n*p*(1-p))).ravel()+precision
        for key,mean,var in zip(keys,beta,1/diagonal):self.states[key]=[float(mean),float(var),str(period)]
        self.last_updated_period=str(period);self.periods+=1;self.matches+=len(frame);self.iterations+=int(fitted.nit)

    def save(self,path,source_sha256,cutoff):
        save_json(path,{'circuit':self.circuit,'context':self.with_context,'process_sd_per_year':self.process_sd,
                        'cutoff':cutoff,'canonical_sha256':source_sha256,'states':self.states,
                        'last_updated_period':self.last_updated_period,'periods':self.periods,
                        'training_matches':self.matches,'iterations':self.iterations,
                        'production_approved':False,'label':'Exploratory dynamic diagonal Gaussian filter'})


def experiment(canonical_root,baseline_root,output,circuit):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    source=Path(canonical_root)/'matches.parquet';data=pd.read_parquet(source)
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    protocol={'circuit':circuit,'source_sha256':sha,'created_before_fits':True,
              'years':[2025,2026],'process_sd_per_year':.20,'embargo_days':35,
              'variants':['dynamic_base','dynamic_context'],'production_approved':False,
              'scope':'Exploratory retrospective development; frozen-origin test years; source-time availability not proven',
              'uncertainty':'Diagonal assumed-density filter; cross-effect covariance discarded',
              'context':['age','hand','indoor','missingness'],'unsupported_context':['fatigue','travel','weather','injury']}
    save_json(output/'protocol.json',protocol)
    reports={};predictions=[]
    for year in (2025,2026):
        cutoff=f'{year}-01-01';end=(pd.Timestamp(cutoff)-pd.Timedelta(days=35)).strftime('%Y-%m-%d')
        history=data.loc[data.circuit.eq(circuit)&data.eligible_model&data.period.ge('2018-01-01')&data.period.lt(end)]
        baseline=pd.read_parquet(Path(baseline_root)/f'experiments/{circuit}_{year}/heldout_predictions.parquet')
        test=data.set_index('match_id').loc[baseline.match_id].reset_index()
        models={name:DynamicServe(circuit,name=='dynamic_context') for name in protocol['variants']}
        for number,(period,block) in enumerate(history.groupby('period',sort=True)):
            for model in models.values():model.update(block,period)
            if (number+1)%100==0:print(f'{circuit} {year}: {number+1} source periods assimilated',flush=True)
        rows=[]
        for i,(row,reference) in enumerate(zip(test.itertuples(),baseline.itertuples())):
            winner_first=reference.a==row.winner_id
            entry={'match_id':row.match_id,'period':row.period,'year':year,'y':int(reference.y),
                   'surface':row.surface,'a':reference.a,'b':reference.b,
                   'surface_elo_probability':float(reference.surface_elo_probability),
                   'static_markov_probability':float(reference.model_probability)}
            for name,model in models.items():
                points=model.predict(reference.a,reference.b,row.surface,cutoff,
                    context_from_row(row,winner_first),context_from_row(row,not winner_first))
                entry[name+'_probability']=match_win(points['p'],points['q'],
                    Rules(int(row.best_of),deciding_tiebreak=10 if row.tourney_level=='G' else 7))
                entry[name+'_p']=points['p'];entry[name+'_q']=points['q']
            rows.append(entry)
        frame=pd.DataFrame(rows);predictions.extend(rows)
        metrics={col:scores(frame.y,frame[col]) for col in frame if col.endswith('_probability')}
        reports[str(year)]={'n':len(frame),'metrics':metrics,'training_matches':len(history),
                            'training_last_period':history.period.max()}
        for name,model in models.items():model.save(output/f'{name}_{year}.json',sha,cutoff)
        print(json.dumps({'circuit':circuit,'year':year,'metrics':metrics}),flush=True)
    pd.DataFrame(predictions).to_parquet(output/'predictions.parquet',index=False)
    report={**protocol,'evaluations':reports}
    save_json(output/'report.json',report)
    return report
