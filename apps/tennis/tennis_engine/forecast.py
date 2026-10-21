from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.special import expit
from .model import ServeModel
from .scoring import Rules, match_distribution, market, price


def forecast(model_path,player_a,player_b,surface,best_of=3,deciding_tiebreak=7,samples=24):
    if not 8<=samples<=256: raise ValueError('Use 8 to 256 integration samples')
    model=ServeModel(model_path)
    a,b=model.resolve(player_a),model.resolve(player_b)
    pred=model.predict(a,b,surface)
    rng=np.random.default_rng(20261016)
    # Antithetic posterior draws reduce integration noise while retaining covariance.
    z=rng.multivariate_normal([0,0],pred['covariance'],size=(samples+1)//2)
    z=np.concatenate([z,-z],axis=0)[:samples]
    draws=expit(np.asarray(pred['logits'])+z)
    rules=Rules(best_of=best_of,deciding_tiebreak=deciding_tiebreak)
    integrated=defaultdict(float)
    winner_samples=[]
    for p,q in draws:
        dist=match_distribution(float(p),float(q),rules)
        winner_samples.append(market(dist,'winner',selection='A')['win'])
        for key,value in dist.items(): integrated[key]+=value/len(draws)
    markets={}
    for label,kind,line,selection in [
        ('winner_A','winner',None,'A'),('winner_B','winner',None,'B'),
        ('first_set_A','first_set',None,'A'),('any_tiebreak','tiebreak',None,'yes'),
        ('over_22_5_games','games_total',22.5,'over'),('under_22_5_games','games_total',22.5,'under'),
        ('A_minus_3_5_games','games_handicap',-3.5,'A'),('B_plus_3_5_games','games_handicap',3.5,'B'),
        ('over_2_5_sets','sets_total',2.5,'over'),('A_minus_1_5_sets','sets_handicap',-1.5,'A')]:
        markets[label]=price(market(integrated,kind,line,selection))
    sets=defaultdict(float)
    for (sa,sb,*_),value in integrated.items(): sets[f'{sa}-{sb}']+=value
    return {'status':'local_research_forecast; not an executed or published betting recommendation',
            'players':{'a':{'id':a,'name':model.names[a]},'b':{'id':b,'name':model.names[b]}},
            'surface':surface,'rules':vars(rules),'model':model.summary,'serve':pred,
            'integration_samples':len(draws),'winner_A_parameter_interval_90':np.quantile(winner_samples,[.05,.95]).tolist(),
            'market_probabilities':markets,'set_score_distribution':dict(sets),
            'joint_mass':sum(integrated.values()),'offered_odds':None,
            'limits':['Completed standard singles only; no retirement/void pricing.','Gaussian Laplace approximation and finite posterior integration.','Intervals describe parameter uncertainty under the model, not guaranteed coverage.','No live calendar or bookmaker snapshot is attached.','22.5 and handicap lines are illustrative queries; no bookmaker quote is implied.']}
