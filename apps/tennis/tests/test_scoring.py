import numpy as np
import pytest
from tennis_engine.scoring import hold,tiebreak,set_distribution,match_distribution,match_win,Rules,market,price


@pytest.mark.parametrize('p',[.25,.5,.65,.9])
def test_hold_complement(p):
    assert hold(p)+hold(1-p)==pytest.approx(1,abs=1e-12)
    assert hold(p,True)+hold(1-p,True)==pytest.approx(1,abs=1e-12)


@pytest.mark.parametrize('target',[7,10])
def test_tiebreak_symmetry(target):
    assert tiebreak(.65,.60,0,target)+tiebreak(.60,.65,1,target)==pytest.approx(1,abs=1e-12)
    assert tiebreak(.6,.6,0,target)==pytest.approx(.5,abs=1e-12)


@pytest.mark.parametrize('rules',[Rules(),Rules(5,deciding_tiebreak=10),Rules(no_ad=True)])
def test_match_mass_and_symmetry(rules):
    a=match_win(.65,.6,rules)
    assert a+match_win(.6,.65,rules)==pytest.approx(1,abs=1e-12)
    if rules.best_of==3:
        d=match_distribution(.65,.6,rules)
        assert sum(d.values())==pytest.approx(1,abs=1e-12)
        assert market(d,'winner',selection='A')['win']==pytest.approx(a,abs=1e-12)
        over=market(d,'games_total',22.5,'over')
        under=market(d,'games_total',22.5,'under')
        assert over['win']+under['win']==pytest.approx(1,abs=1e-12)
        handicap=market(d,'games_handicap',0.,'A')
        assert sum(handicap.values())==pytest.approx(1)


def simulate(p,q,count=4000):
    """Independent point-by-point simulation, including the tie-break service order."""
    rng=np.random.default_rng(127)
    winners=[]
    for _ in range(count):
        server=int(rng.integers(2));sa=sb=0
        while max(sa,sb)<2:
            ga=gb=0
            while max(ga,gb)<6 or abs(ga-gb)<2:
                if ga==gb==6:
                    a=b=k=0
                    first=server
                    while max(a,b)<7 or abs(a-b)<2:
                        serve=first if k==0 else (1-first if ((k-1)//2)%2==0 else first)
                        a_won=rng.random()<(p if serve==0 else 1-q)
                        a+=a_won;b+=not a_won;k+=1
                    ga+=a>b;gb+=b>a;server=1-first
                    break
                a=b=0
                while max(a,b)<4 or abs(a-b)<2:
                    a_won=rng.random()<(p if server==0 else 1-q)
                    a+=a_won;b+=not a_won
                ga+=a>b;gb+=b>a;server=1-server
            sa+=ga>gb;sb+=gb>ga
        winners.append(sa>sb)
    return np.mean(winners)


def test_point_simulation_agrees_with_exact_match():
    assert simulate(.64,.60)==pytest.approx(match_win(.64,.60),abs=.03)


def test_push_and_return_are_not_confused_with_probability_gap():
    assert price({'win':.4,'push':.2,'loss':.4},2.)['expected_return']==pytest.approx(0)
    assert price({'win':.4,'push':.2,'loss':.4})['fair_decimal_odds']==pytest.approx(2)
    with pytest.raises(ValueError): market({},'games_handicap',-.25,'A')
    with pytest.raises(ValueError): match_win(.6,.6,first_server=2)
    for p in (0,1,float('nan')):
        with pytest.raises(ValueError): hold(p)


def test_best_of_five_joint_distribution_respects_format_and_winner():
    rules=Rules(5,deciding_tiebreak=10)
    d=match_distribution(.67,.62,rules)
    assert all(max(sa,sb)==3 and min(sa,sb)<=2 for sa,sb,*_ in d)
    assert market(d,'winner',selection='A')['win']==pytest.approx(match_win(.67,.62,rules),abs=1e-12)
