"""Text/numerical/compilation verification only, as requested by the author."""
import json,re,hashlib,sys
from pathlib import Path
import fitz,numpy as np
HERE=Path(__file__).resolve().parent;P=HERE.parent;BACK=P/'archive/before_round7_20261015';R6=P/'experiments'/'policy_grid';R5=P/'experiments'/'main'
sys.path.insert(0,str(R5))
from analyze import groups,record
from model import Model
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=(P/'TRA-20261014-V3.tex').read_text(encoding='utf-8');old=(BACK/'TRA-20261014-V3.tex').read_text(encoding='utf-8')
assert t[t.index(r'\section{Model}'):t.index(r'\section{Case study}')]==old[old.index(r'\section{Model}'):old.index(r'\section{Case study}')]
assert all(s in t for s in ['Pricing authority \\sep Fare caps \\sep Participation floors','Price-cap regulation restricts','132 thousand CNY/day','68.9 seconds wall-clock','0.999754','largest active G/D multiplier is 1.20'])
assert 'Joint regulation changes the profit--welfare tradeoff without establishing universal complementarity.' not in t
abstract=re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',t,re.S)[1];assert len(abstract.split())<=200
log=(P/'TRA-20261014-V3.log').read_text(encoding='utf-8',errors='replace');assert not re.search(r'LaTeX Warning:.*(?:undefined|multiply defined)|^!',log,re.M)
over=re.findall(r'Overfull[^\n]*(?:\n[^\n]*)?',log);assert len(over)<=2,over
doc=fitz.open(P/'TRA-20261014-V3.pdf');texts=[p.get_text() for p in doc];assert not any('??' in s for s in texts)
g=next(g for g in groups('E2') if g['job']['id']=='WC_reference_none');w=record(g,'P3','welfare');b=record(g,'P0','profit');m=Model(json.loads((R5/'inputs/WC.json').read_text(encoding='utf-8')))
active=(np.array(w['N'])>0)&m.adjustable[:,None];peak=float(np.array(w['phi'])[:,:,0][active].max())
evidence=dict(profit_gain=w['profit']-b['profit'],welfare=w['welfare'],retention=w['eta'],peak_active_GD_multiplier=peak,certificate=w['meta']['certificate'])
assert evidence['certificate'] and w['eta']<1 and np.isclose(peak,1.2)
a=json.loads((R6/'round6_analysis.json').read_text(encoding='utf-8'))
assert abs(a['summary']['HN']['joint105_100']['welfare']/562172.20594*100-92.68)<.02
protected={name:sha(P/'Fig'/name) for name in ['case_fig03.pdf','case_fig05.pdf','case_fig05.tex']}
assert protected['case_fig03.pdf']=='caaf675da9225c98e7c17a730fbd08e23172b30646dc743a00fd9ae7ebb982c9'
assert protected['case_fig05.pdf']=='d9f0f6d91bcc2a68a7116d844cecf561ce0bea544a174b655a3e5cb3149df3b2'
assert protected['case_fig05.tex']=='15536f8a54372c168012d8eea034534d77db25dd35d82c5f4c3fb4698bc662bc'
runtime=json.loads((HERE/'runtime_summary.json').read_text(encoding='utf-8'))
checks=dict(passed=True,pdf_pages=len(doc),pdf_sha256=sha(P/'TRA-20261014-V3.pdf'),abstract_words=len(abstract.split()),model_section_unchanged=True,protected_figure_sha256=protected,undefined_references=False,overfull_warnings=over,new_main_experiments=0,visual_inspection='Not performed, as explicitly requested by the author.',WC_welfare_benchmark=evidence,runtime_scope=runtime)
(HERE/'delivery_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
response=f'''# Final response to the Section 4 review: round 7

15 October 2026. Final manuscript: TRA-20261014-V3.tex; compiled PDF: {len(doc)} pages.

The review confirms that Section 4 passes on accuracy and logic. This final pass implements the remaining editorial and reporting adjustments. No new main experiments were run. Visual inspection was omitted at the author's explicit request; the author will check the figures and layout.

## 1. Align Sections 1–2 with the regulatory findings

- Keywords now include **Pricing authority, Fare caps and Participation floors**, alongside railway service design, elastic travel demand and transport equity.
- The Introduction's income-composition paragraph is shortened. It explains class-specific monetary sensitivity while treating polarization as a parametric scenario, without the former extended K-shaped-recovery narrative.
- Section 2.4 adds a short price-cap paragraph connecting fare caps to the fare/frequency/objective/fiscal taxonomy in [Zhang, Lindsey and Yang (2018)](https://doi.org/10.1016/j.trb.2018.08.020). The distinction between a fare restriction and a participation outcome constraint is our application of that taxonomy, not a claim that the cited paper estimates the present railway participation floor.
- Section 2.2's gap statement now concerns participation under price and service controls. Sections 2.4–2.5 position the contribution around the comparison of pricing authority, caps and floors, supported by certified single-OD policy grids and explicitly scoped scenario evidence.
- Section 3's mathematical model and all numerical experiment records are unchanged.

## 2. Explain the WC welfare benchmark in Figure 17

Added an explanation in Section 4.6. The certified reference welfare design has profit/welfare gains of **852.5/769.6 thousand CNY/day**, retention **{w['eta']:.9f}**, and a largest active G/D fare multiplier of **1.20**. It dominates the strict-floor-only and cap-1.05-plus-strict-floor designs in both coordinates, but fails the strict floor of 1.00. Its peak fare also excludes it from tighter-cap domains.

Two qualifications are necessary when interpreting the review's wording: the star does not dominate *every* sampled outcome, since the central commercial profit gain is 1,788.8 thousand CNY/day; and retention is not its only restriction under caps of 1.00–1.05. Where it is feasible under looser regulation, commercial profit maximization need not select the welfare-optimal design. These points are now explicit in the manuscript.

The optional additional fine-floor experiments were not needed for this explanatory correction and were not run.

## 3. Make the abstract's joint-regulation result concrete

Replaced the vague tradeoff sentence with the HN result: adding a 1.05 cap to the strict floor raises welfare by approximately **132 thousand CNY/day** for a **4-thousand-CNY profit reduction**, reaching **93%** of the certified welfare optimum. The abstract contrasts this with WC, where the floor alone already reaches **95%**. The abstract contains {len(abstract.split())} words.

## 4. Name the regulatory instruments in the title

Adopted the optional title adjustment:

**Railway Product, Fare, and Frequency Design: Pricing Authority, Fare Caps, and Participation Floors**

This matches the main findings while income and road-cost shocks remain scenario dimensions.

## 5. Report measured runtime with an explicit scope

Added runtime alongside the computing environment in Section 4.2. The focused batch of **60 HN/WC certificates plus four JX variant re-solves** took **{runtime['batch_wall_seconds']:.1f} seconds wall-clock** with four worker processes. The median recorded certificate call took **{runtime['median_certificate_call_seconds']:.2f} seconds**, with a range of **{runtime['minimum_certificate_call_seconds']:.2f}–{runtime['maximum_certificate_call_seconds']:.2f} seconds**.

These are directly recorded incremental-batch timings, including warm starts and reuse of period columns within cap domains. They are not presented as a cold runtime for the entire study. The original full-study records include cache reuse and separate refinement/audit stages, so a single end-to-end cold runtime cannot be inferred by summing their per-state or per-certificate times. Existing environment and COPT/HiGHS/custom-search role descriptions are retained.

Evidence: `runtime_summary.json`, `../policy_grid/run_manifest.json`, and per-certificate `meta.seconds` in the ten certified grid files.

## 6. Separate the crowded HN Figure 17 labels

Shifted the blue cap-1.00 label left and the orange floor-1.00 label right/down. The local insets, certified data, plotted decisions, colors, benchmark and envelope are unchanged. The figure source is `figure17_round7.py`; its numerical input is the unchanged round-six `cap_floor_frontier.csv`.

No visual inspection or preview review was performed in this final pass, as requested. Compilation and text/reference checks pass. The only two overfull warnings are the existing protected model/layout warnings. Figure 3 and the original TikZ workflow retain their preserved hashes.

The current case-study revision is complete; remaining visual review is left to the author.
'''
(P/'REVIEW_RESPONSE_V3_round7_final_20261015_EN.md').write_text(response,encoding='utf-8')
readme='''# Final editorial pass: round 7

No new main experiments. Numerical results and the round-five/six engines remain unchanged. This package aligns the title, abstract, keywords, Introduction and literature positioning; explains the WC welfare benchmark; reports recorded supplementary-batch runtime; and separates two HN Figure 17 labels.

The author explicitly requested no visual inspection. Only source consistency, selected numerical values, mathematical-model preservation, references and compilation were checked. `delivery_checks.json` records this limitation rather than claiming visual approval.

Reproduce using Python 3.13.2:

1. Run `write_round7.py` to rebuild the final text and figure script from the saved final round-six snapshot.
2. Run `figure17_round7.py` to apply the two label-position changes to the unchanged certified grid.
3. From TRA-R2, run `latexmk -pdf -interaction=nonstopmode -halt-on-error TRA-20261014-V3.tex`.
4. Run `finalize_round7.py` for nonvisual delivery checks and the English response.

The immediately preceding manuscript, PDF and Figure 17 assets are saved in `../archive/before_round7_20261015/`. Older manuscript writers restore older editorial states and should not be run after the round-seven writer unless intentionally reverting. Runtime scope and the corrected WC benchmark evidence are recorded in the JSON audit files. The measured 68.9-second runtime is for the defined 60-certificate/four-JX-recheck batch, not a cold full-study run.
'''
(HERE/'README.md').write_text(readme,encoding='utf-8')
files=[p for p in HERE.glob('*') if p.is_file() and p.name!='artifact_manifest.json']+[P/'TRA-20261014-V3.tex',P/'TRA-20261014-V3.pdf',P/'Fig/round6_frontier.pdf',P/'Fig/round6_frontier.png',P/'REVIEW_RESPONSE_V3_round7_final_20261015_EN.md']
(HERE/'artifact_manifest.json').write_text(json.dumps({str(p.relative_to(P)):sha(p) for p in sorted(files)},indent=2),encoding='utf-8')
print(json.dumps(dict(passed=True,pages=len(doc),abstract_words=len(abstract.split()),visual_inspection='skipped at user request',new_main_experiments=0),indent=2))
