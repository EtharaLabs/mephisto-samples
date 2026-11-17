"""Public-only candidate ladder. No import of private estimators or truth.

All candidates are fixed before measurement; none uses query labels or score feedback.
Floor setters are naive_constant, target_encoding_alone, history_rf and closed_rf.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from threadpoolctl import threadpool_limits

LANES = ('adjustment_magnitude','allocation_key_profile','challenge_flag','method_tier','review_rank','uncertain_tax_reserve')
VIEWS = ('invoices','allocation_drivers','tax_audits','comparables','settlements','tax_positions')
METHODS = ('naive_constant','target_encoding_alone','history_rf','closed_rf','closed_ridge',
           'closed_extra','hgb_plain','hgb_asof','engineered_ridge','local_kernel','residual_kernel','local_kernel_80')
FLOOR_METHODS = METHODS[:4]


def read(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n' for r in rows))


def rank(values):
    order = {v:i+1 for i,v in enumerate(sorted(set(values),reverse=True))}
    return np.array([order[v] for v in values])


def expanded(x, lane):
    if lane == 0:
        return np.column_stack((x,x[:,0]*x[:,1],np.sin(4*x[:,2]),x[:,3]**2))
    if lane == 2:
        return np.column_stack((x,x[:,0]*x[:,4],x[:,1]*(1-x[:,3])))
    if lane == 4:
        return np.column_stack((x,np.sin(2*np.pi*x[:,5]),np.cos(2*np.pi*x[:,5]),x[:,0]*x[:,3]))
    return np.column_stack((x,x[:,0]*x[:,3],x[:,2]**2))


def local(x,y,z,w,k):
    result = []
    for point in z:
        d = np.sum((x-point)**2,axis=1)
        ix = np.argsort(d,kind='stable')[:k]
        ww = np.exp(-2*d[ix]/max(d[ix[-1]],0.001))*w[ix]
        result.append(np.average(y[ix],axis=0,weights=ww))
    return np.array(result)


def regression(kind,x,y,z,w):
    if kind == 'ridge':
        return Ridge(alpha=1.0).fit(x,y,sample_weight=w).predict(z)
    if kind == 'rf':
        return RandomForestRegressor(n_estimators=100,random_state=91,n_jobs=1).fit(x,y,sample_weight=w).predict(z)
    if kind == 'extra':
        return ExtraTreesRegressor(n_estimators=160,min_samples_leaf=5,random_state=91,n_jobs=1).fit(x,y,sample_weight=w).predict(z)
    if y.ndim == 2:
        return np.column_stack([regression('hgb',x,y[:,j],z,w) for j in range(y.shape[1])])
    return HistGradientBoostingRegressor(max_iter=140,max_leaf_nodes=15,min_samples_leaf=25,l2_regularization=3,random_state=91,early_stopping=False).fit(x,y,sample_weight=w).predict(z)


def predict(workspace, method):
    workspace = Path(workspace)
    metadata = json.loads((workspace/'dataset_metadata.json').read_text())
    history, queries = read(workspace/'history/review.jsonl'), read(workspace/'queries.jsonl')
    assert max(r['period'] for r in history) < min(r['period'] for r in queries)
    register = {p.stem:json.loads(p.read_text()) for p in sorted((workspace/'register').glob('*.json'))}
    output = [dict(record_id=q['record_id']) for q in queries]
    for lane, view in enumerate(VIEWS):
        fields = metadata['features'][view]
        rows = [r for p in sorted((workspace/view).glob('*.jsonl')) for r in read(p)]
        snapshots = {(r['pair_id'],r['period']):r for r in rows if r['kind']=='snapshot'}
        def design(rr):
            return np.array([[r[k] for k in fields]+[float(register[r['pair_id']]['jurisdiction_band']==b) for b in range(4)] for r in rr])
        def scale(r):
            return r['charge_base'] if lane == 0 else r['tax_exposure'] if lane == 5 else 1.0
        for period in sorted({q['period'] for q in queries}):
            ids = [i for i,q in enumerate(queries) if q['period']==period]
            snaps = [snapshots[queries[i]['pair_id'],period] for i in ids]
            z = design(snaps)
            if method in ('naive_constant','target_encoding_alone','history_rf'):
                yy = np.array([h[LANES[lane]] for h in history],dtype=float)
                if lane in (0,5) and method != 'naive_constant':
                    yy /= np.array([scale(snapshots[h['pair_id'],h['period']]) for h in history])
                if method == 'history_rf':
                    x = design([snapshots[h['pair_id'],h['period']] for h in history])
                    pred = regression('rf',x,yy,z,np.ones(len(x)))
                elif method == 'naive_constant':
                    pred = np.tile(np.mean(yy,axis=0),(len(ids),1)) if yy.ndim==2 else np.repeat(np.mean(yy),len(ids))
                else:
                    grouped = [[j for j,h in enumerate(history) if h['pair_id']==s['pair_id']] for s in snaps]
                    pred = np.array([np.mean(yy[group],axis=0) if group else np.mean(yy,axis=0) for group in grouped])
                if lane == 4:
                    pred = rank(-pred)
            else:
                cases = [r for r in rows if r['kind']=='closed' and r['booked_period']<period]
                use_asof = method not in ('closed_rf','closed_ridge','closed_extra','hgb_plain')
                if use_asof:
                    cases = [dict(r,**r.get('as_booked',{})) if r.get('restated_period',-1)>=period else r for r in cases]
                x = design(cases)
                y = np.array([r['outcome'] for r in cases])
                w = np.exp(-np.array([period-r['booked_period'] for r in cases])/8) if use_asof else np.ones(len(cases))
                if method in ('local_kernel','local_kernel_80'):
                    pred = local(x,y,z,w,60 if method=='local_kernel' else 80)
                elif method in ('engineered_ridge','residual_kernel'):
                    xx,zz = expanded(x,lane),expanded(z,lane)
                    if lane in (2,5):
                        target = y if lane==2 else (y>0).astype(int)
                        model = LogisticRegression(C=1.0,max_iter=500,random_state=91).fit(xx,target,sample_weight=w)
                        pred = model.predict_proba(zz)[:,1]
                        if lane==5:
                            pos = y>0
                            sev = regression('ridge',xx[pos],np.log(y[pos]),zz,w[pos])
                            if method=='residual_kernel':
                                reg = Ridge(alpha=1).fit(xx[pos],np.log(y[pos]),sample_weight=w[pos])
                                sev += local(x[pos],np.log(y[pos])-reg.predict(xx[pos]),z,w[pos],60)
                            pred *= np.exp(sev)
                    else:
                        reg = Ridge(alpha=1).fit(xx,y,sample_weight=w)
                        pred = reg.predict(zz)
                        if method=='residual_kernel':
                            pred += local(x,y-reg.predict(xx),z,w,60)
                else:
                    kind = {'closed_rf':'rf','closed_ridge':'ridge','closed_extra':'extra'}.get(method,'hgb')
                    pred = regression(kind,x,y,z,w)
                if lane==2:
                    # An empirically calibrated prevalence threshold from closed cases.
                    pred = (pred >= np.quantile(pred,1-np.average(y,weights=w))).astype(int)
                if lane==4:
                    pred = rank(pred*np.array([s['settlement_base'] for s in snaps])-np.array([s['paid_on_account'] for s in snaps]))
            if lane in (0,5):
                pred = [round(max(0,float(v))*(1.0 if method == 'naive_constant' else scale(s)),2) for v,s in zip(pred,snaps)]
            elif lane==1:
                pred = np.maximum(pred,0)
                pred /= np.maximum(1,pred.sum(axis=1))[:,None]
                pred = (np.floor(pred*1e8)/1e8).tolist()
            elif lane==2:
                pred = [int(v>=0.5) for v in pred]
            elif lane==3:
                pred = np.clip(np.rint(pred),0,3).astype(int).tolist()
            else:
                pred = [int(v) for v in pred]
            for i,v in zip(ids,pred):
                output[i][LANES[lane]] = v
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--method',choices=METHODS,default='residual_kernel')
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        write(args.output,predict(args.workspace,args.method))


if __name__ == '__main__':
    main()
