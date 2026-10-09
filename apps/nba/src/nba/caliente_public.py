"""Parse logged-out public Caliente prices, never click or create a bet slip."""
from html.parser import HTMLParser
import math,re


class Node:
    def __init__(self,tag='',attrs=(),parent=None):
        self.tag,self.attrs,self.parent=tag,dict(attrs),parent
        self.children=[]
    def classes(self):return self.attrs.get('class','').split()
    def text(self):return ' '.join(c if isinstance(c,str) else c.text() for c in self.children).strip()
    def descendants(self):
        for c in self.children:
            if isinstance(c,Node):yield c;yield from c.descendants()


class Tree(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.root=Node();self.current=self.root
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs,self.current);self.current.children.append(n)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.current=n
    def handle_endtag(self,tag):
        n=self.current
        while n.parent is not None:
            if n.tag==tag:self.current=n.parent;break
            n=n.parent
    def handle_data(self,data):self.current.children.append(data)


def prices(html,event_id,receipt):
    if not str(event_id).isdecimal():raise ValueError('numeric operator event required')
    tree=Tree();tree.feed(html);rows=[];seen={}
    for n in tree.root.descendants():
        if n.tag!='button' or n.attrs.get('name')!='add-to-slip' or 'ev-'+str(event_id) not in n.classes():continue
        ancestor=n.parent;in_event_markets=False
        while ancestor:
            if 'selections-for-event' in ancestor.classes() and ancestor.attrs.get('data-ev_id')==str(event_id):
                in_event_markets=True;break
            ancestor=ancestor.parent
        if not in_event_markets:continue
        classes=n.classes();mid=next((c[4:] for c in classes if re.fullmatch(r'mkt-\d+',c)),None)
        sid=next((c[5:] for c in classes if re.fullmatch(r'seln-\d+',c)),None)
        decimals=[c.text() for c in n.descendants() if c.tag=='span' and {'price','dec'}<=set(c.classes())]
        if not mid or not sid or len(decimals)!=1:raise ValueError('ambiguous market, selection or decimal price')
        value=float(decimals[0])
        if not math.isfinite(value) or not 1<value<=1000:raise ValueError('invalid price')
        market_type=None;ancestor=n.parent
        while ancestor:
            market_type=next((c[9:] for c in ancestor.classes() if c.startswith('mkt-sort-')),market_type)
            if market_type:break
            ancestor=ancestor.parent
        row=dict(book='caliente_mx',jurisdiction='MX',operator_event_id=str(event_id),market_id=mid,selection_id=sid,
            label=n.attrs.get('title','').strip(),decimal=value,market_type_raw=market_type,
            button_disabled='disabled' in n.attrs or any('suspended' in c or 'disabled' in c for c in classes),
            first_received_at_utc=receipt['first_received_at_utc'],source_updated_at_utc=None,raw_sha256=receipt['raw_sha256'],
            period_verified=False,player_id=None,rules_verified=False,contract_verified=False,actionable=False)
        if sid in seen:
            if any(seen[sid][k]!=v for k,v in row.items() if k!='label'):
                raise ValueError('conflicting selection revisions in one body')
            if row['label'] not in seen[sid]['labels_observed']:seen[sid]['labels_observed'].append(row['label'])
        else:
            row['labels_observed']=[row['label']];rows.append(row);seen[sid]=row
    return dict(state='captured' if rows else 'no_public_selections',quotes=rows,individual_props_verified=0,
        wager_acceptance_verified=False,actionable=False)
