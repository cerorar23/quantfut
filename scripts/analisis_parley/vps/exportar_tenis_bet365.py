import gzip, json, os, csv, sys
b=os.path.expanduser("~/betsapi/data/tennis/prematch")
w=csv.writer(sys.stdout); w.writerow(["event","time","upd","league","market","sel","line","odds","hg","ag","hs","as_","nsets","status"])
for f in sorted(os.listdir(b)):
    try: d=json.load(gzip.open(os.path.join(b,f)))
    except Exception: continue
    ev=d["event"]; sp=((d.get("prematch") or {}).get("main") or {}).get("sp") or {}
    if not sp or ev.get("time_status")!="3": continue
    sc=ev.get("scores") or {}
    hg=sum(int(v["home"]) for v in sc.values()); ag=sum(int(v["away"]) for v in sc.values())
    hs=sum(int(v["home"])>int(v["away"]) for v in sc.values()); as_=sum(int(v["away"])>int(v["home"]) for v in sc.values())
    upd=(d["prematch"]["main"].get("updated_at"))
    base=[ev["id"],ev["time"],upd,(ev.get("league") or {}).get("name")]
    tail=[hg,ag,hs,as_,len(sc),ev["ss"]]
    for o in (sp.get("total_games_2_way") or {}).get("odds",[]): w.writerow(base+["total_games",o.get("header"),o["name"],o["odds"]]+tail)
    for o in (sp.get("match_handicap_(games)") or {}).get("odds",[]): w.writerow(base+["hcp_games",o.get("header"),o["name"],o["odds"]]+tail)
    for o in (sp.get("total_sets") or {}).get("odds",[]): w.writerow(base+["total_sets","",o["name"],o["odds"]]+tail)
    for o in (sp.get("to_win_match") or {}).get("odds",[]): w.writerow(base+["winner",o["name"],"",o["odds"]]+tail)
