"""Local COPT adapter for the identical finite-menu linear integer master."""
from types import SimpleNamespace
import numpy as np
import coptpy as cp
_environment=None
def milp(c,integrality,bounds,constraints,options):
    global _environment
    if _environment is None:_environment=cp.Envr()
    model=_environment.createModel();model.setParam(cp.COPT.Param.Logging,0);model.setParam(cp.COPT.Param.Threads,1);model.setParam(cp.COPT.Param.TimeLimit,float(options.get('time_limit',180)));model.setParam(cp.COPT.Param.RelGap,0.);model.setParam(cp.COPT.Param.AbsGap,1e-9);model.setParam(cp.COPT.Param.FeasTol,1e-9);model.setParam(cp.COPT.Param.DualTol,1e-9)
    convert=lambda a:np.nan_to_num(np.asarray(a,float),nan=0.,posinf=cp.COPT.INFINITY,neginf=-cp.COPT.INFINITY)
    assert np.all(np.asarray(integrality)==1)
    model.loadMatrix(np.asarray(c,float),constraints.A.tocsc(),convert(constraints.lb),convert(constraints.ub),convert(bounds.lb),convert(bounds.ub),np.repeat(cp.COPT.BINARY,len(c)))
    assert model.getAttr(cp.COPT.Attr.ObjSense)==cp.COPT.MINIMIZE
    if options.get('mip_start') is not None:model.setMipStart(model.getVars(),np.asarray(options['mip_start'],float))
    model.solve();status=model.status;has=bool(model.getAttr(cp.COPT.Attr.HasMipSol));x=np.asarray(model.getValues()) if has else None;bound=float(model.bestbnd)
    result=SimpleNamespace(success=status==cp.COPT.OPTIMAL,status=0 if status==cp.COPT.OPTIMAL else (2 if status==cp.COPT.INFEASIBLE else 1),x=x,mip_dual_bound=bound,fun=float(model.objval) if has else None,backend='COPT',raw_status=status)
    del model
    return result
