"""Regularized binomial serve/return model with a declared Laplace approximation.

Exponential time weights form a power likelihood, not an exact dynamic state model.
"""
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import minimize
from scipy.special import expit, logit
from scipy.sparse.linalg import splu
from .ingest import save_json

SURFACES=('Hard','Clay','Grass','Carpet')


def terms(a,b,surface):
    if a==b or surface not in SURFACES: raise ValueError('Invalid players or surface')
    keys=[('intercept',1.,.6),('serve|'+a,1.,.35),('return|'+b,-1.,.35),
          ('serve_surface|'+a+'|'+surface,1.,.18),('return_surface|'+b+'|'+surface,-1.,.18)]
    if surface!='Hard': keys.append(('surface|'+surface,1.,.25))
    return keys


def training_rows(root,circuit,cutoff,since='2018-01-01'):
    df=pd.read_parquet(Path(root)/'canonical/matches.parquet')
    # Tournament-week dates cannot establish the order of matches inside an event.
    end=(pd.Timestamp(cutoff)-pd.Timedelta(days=35)).strftime('%Y-%m-%d')
    return df.loc[df.circuit.eq(circuit)&df.eligible_model&df.period.ge(since)&df.period.lt(end)].copy()


def fit(df,circuit,cutoff,output,half_life_days=365.):
    if circuit not in ('ATP','WTA') or not np.isfinite(half_life_days) or half_life_days<=0:
        raise ValueError('Supported circuit and positive half life required')
    if any((Path(output)/name).exists() for name in ('model.json','precision.npz','training_receipt.json')):
        raise ValueError('Model output already exists; use a new version directory')
    if len(df)<100: raise ValueError('Insufficient matches for fitting')
    exposure={}
    surface_exposure={}
    for side,prefix in [('winner','w'),('loser','l')]:
        group=df.groupby(side+'_id')[prefix+'_svpt'].sum()
        for pid,n in group.items(): exposure[pid]=exposure.get(pid,0)+float(n)
        for (pid,s),n in df.groupby([side+'_id','surface'])[prefix+'_svpt'].sum().items():
            surface_exposure[(pid,s)]=surface_exposure.get((pid,s),0)+float(n)
    keys=['intercept']+['surface|'+s for s in SURFACES[1:]]
    for pid,n in sorted(exposure.items()):
        if n>=300: keys.extend(['serve|'+pid,'return|'+pid])
    for (pid,s),n in sorted(surface_exposure.items()):
        if n>=900: keys.extend(['serve_surface|'+pid+'|'+s,'return_surface|'+pid+'|'+s])
    index={k:i for i,k in enumerate(keys)}
    rows,cols,values=[],[],[]
    ns,ys,weights=[],[],[]
    dates=pd.to_datetime(df.period)
    rowweights=np.exp2(-(pd.Timestamp(cutoff)-dates).dt.days.to_numpy()/half_life_days)
    for match,w in zip(df.itertuples(),rowweights):
        for a,b,prefix in [(match.winner_id,match.loser_id,'w'),(match.loser_id,match.winner_id,'l')]:
            i=len(ns)
            for key,value,_ in terms(a,b,match.surface):
                if key in index:
                    rows.append(i);cols.append(index[key]);values.append(value)
            ns.append(getattr(match,prefix+'_svpt'))
            ys.append(getattr(match,prefix+'_1stWon')+getattr(match,prefix+'_2ndWon'))
            weights.append(w)
    X=sparse.csr_matrix((values,(rows,cols)),shape=(len(ns),len(keys)))
    n,y,w=map(np.asarray,(ns,ys,weights))
    means=np.zeros(len(keys));means[0]=logit(.62 if circuit=='ATP' else .58)
    sigmas=np.array([.6 if k=='intercept' else .25 if k.startswith('surface|') else .18 if '_surface|' in k else .35 for k in keys])
    precision=1/sigmas**2

    def objective(beta):
        eta=X@beta
        residual=w*(n*expit(eta)-y)
        penalty=beta-means
        f=np.sum(w*(n*np.logaddexp(0,eta)-y*eta))+.5*np.dot(precision*penalty,penalty)
        g=X.T@residual+precision*penalty
        return f,g

    result=minimize(objective,means,jac=True,method='L-BFGS-B',options={'maxiter':350,'ftol':1e-11,'gtol':1e-5,'maxcor':20})
    if not result.success: raise RuntimeError('Optimizer did not converge: '+str(result.message))
    probabilities=expit(X@result.x)
    H=(X.T@X.multiply((w*n*probabilities*(1-probabilities))[:,None])+sparse.diags(precision)).tocsc()
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    sparse.save_npz(output/'precision.npz',H)
    names={}
    for side in ['winner','loser']:
        for pid,group in df.groupby(side+'_id'):
            names[pid]=group.iloc[-1][side+'_name']
    summary={'kind':'binomial serve-return MAP; Gaussian priors; Laplace uncertainty; recency power likelihood',
             'circuit':circuit,'cutoff':cutoff,'embargo_days':35,'first_source_period':df.period.min(),
             'last_source_period':df.period.max(),'matches':len(df),'serve_observations':len(n),'parameters':len(keys),
             'half_life_days':half_life_days,'optimizer_success':bool(result.success),'iterations':int(result.nit),
             'priors':{'global_sd':.35,'player_surface_sd':.18,'surface_population_sd':.25},
             'historical_availability':'not established; retrospective research only','retirements':'conditional on conventional completed matches',
             'dynamic_limit':'Recency-weighted static skills, not a latent random-walk state-space model'}
    save_json(output/'model.json',{'summary':summary,'keys':keys,'coefficients':result.x.tolist(),'names':names})
    return summary


def train(root,output,circuit,cutoff,since='2018-01-01'):
    df=training_rows(root,circuit,cutoff,since)
    summary=fit(df,circuit,cutoff,output)
    path=Path(root)/'canonical/matches.parquet'
    summary['canonical_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    save_json(Path(output)/'training_receipt.json',summary)
    return summary


class ServeModel:
    def __init__(self,path,uncertainty=True):
        data=json.loads((Path(path)/'model.json').read_text(encoding='utf-8'))
        self.summary,self.names=data['summary'],data['names']
        self.beta=np.array(data['coefficients'])
        self.index={key:i for i,key in enumerate(data['keys'])}
        self.factor=splu(sparse.load_npz(Path(path)/'precision.npz').tocsc()) if uncertainty else None

    def resolve(self,value):
        if value in self.names: return value
        found=[pid for pid,name in self.names.items() if name.casefold()==value.casefold()]
        if len(found)!=1:
            raise ValueError('Player name absent or ambiguous; use a canonical ID: '+value)
        return found[0]

    def design(self,a,b,surface):
        vector=np.zeros(len(self.beta));unknown={}
        for key,value,sd in terms(a,b,surface):
            if key in self.index: vector[self.index[key]]=value
            else: unknown[key]=(value,sd)
        return vector,unknown

    def predict(self,a,b,surface,uncertainty=True):
        v1,u1=self.design(a,b,surface);v2,u2=self.design(b,a,surface)
        matrix=np.stack([v1,v2])
        eta=matrix@self.beta
        result={'p':float(expit(eta[0])),'q':float(expit(eta[1])),'unknown_effects':len(set(u1)|set(u2))}
        if uncertainty:
            if self.factor is None: raise ValueError('Model loaded without uncertainty precision')
            covariance=matrix@self.factor.solve(matrix.T)
            for key in set(u1)|set(u2):
                a1,sd1=u1.get(key,(0.,0.));a2,sd2=u2.get(key,(0.,0.))
                sd=max(sd1,sd2)
                covariance+=sd*sd*np.outer([a1,a2],[a1,a2])
            covariance=(covariance+covariance.T)/2
            eigen,vectors=np.linalg.eigh(covariance)
            covariance=(vectors*np.maximum(eigen,0))@vectors.T
            result.update(logits=eta.tolist(),covariance=covariance.tolist())
        return result
