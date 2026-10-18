import json,time
import numpy as np
from model import *
for ci in ['HN','WC','JX']:
    c=json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8'))
    m=Model(c); r=solve(m,'profit','P3'); w=solve(m,'welfare','P3',seeds=[r]); p4=solve(m,'profit','P4',seeds=[r,w])
    dump(ROOT/'smoke'/f'{ci}.json',[r,w,p4])
    for x in [r,w,p4]: print(ci,x['objective'],x['policy'],round(x['objective_value']),x['feasible'],round(x['eta'],5),round(x['maxlf'],5),x['meta'],flush=True)
