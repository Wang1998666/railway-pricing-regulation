"""Audit all saved designs and continue independently detected improving blocks."""
import json
from model import ROOT
import local_review_audit
import polish_audit_failures

def main():
    for _ in range(4):
        local_review_audit.main()
        if not json.loads((ROOT/'local_audit.json').read_text(encoding='utf-8'))['failures']:return
        polish_audit_failures.main()
    raise RuntimeError('An improving block remains after the declared repair limit')
if __name__=='__main__':main()
