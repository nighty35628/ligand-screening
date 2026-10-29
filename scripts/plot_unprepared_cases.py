"""Plot frozen holdout screening results; no model fitting or data filtering."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]/'results/unprepared-20261029'
CASES = [('double_perovskites_gap', 'Double-perovskite band gap', 'Band gap (eV)'),
         ('citrine_thermal_conductivity', 'Thermal conductivity', 'Thermal conductivity (W/m K)')]
with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.labelcolor': '#242830', 'text.color': '#242830',
                     'svg.fonttype': 'none'}):
    fig, axes = plt.subplots(1, 2, figsize=(10.3, 3.7), layout='constrained')
    for axis, (name, title, unit) in zip(axes, CASES):
        result = json.loads((ROOT/name/'verification.json').read_text())
        budgets = [1, 3, 5]
        selected = [result['screening'][str(k)]['selected_best'] for k in budgets]
        random = [result['screening'][str(k)]['random_expected_best'] for k in budgets]
        axis.plot(budgets, selected, '-o', color='#2459B6', lw=2, label='Model-selected: best found')
        axis.plot(budgets, random, '--s', color='#696F78', lw=1.7, label='Random: exact expected best')
        axis.axhline(result['target_range'][1], color='#A65322', lw=1.4, ls=':', label='Best in held-out pool')
        axis.set(title=title, xlabel='Number of candidates selected', ylabel=unit,
                 xticks=budgets, ylim=(0, result['target_range'][1]*1.12), xlim=(.7, 5.3))
        axis.grid(axis='y', alpha=.15)
        if name == 'citrine_thermal_conductivity':
            axis.legend(loc='upper left', bbox_to_anchor=(.01, .84), frameon=False, fontsize=8.5)
        else:
            axis.legend(loc='lower right', frameon=False, fontsize=8.5)
        axis.annotate(f'{selected[-1]:.3g}', (5, selected[-1]), xytext=(-5, 9),
                      textcoords='offset points', ha='right')
    fig.savefig(ROOT/'screening.png', dpi=170, facecolor='white')
    fig.savefig(ROOT/'screening.svg', facecolor='white')
    (ROOT/'figure-provenance.json').write_text(json.dumps({
        'source': ['double_perovskites_gap/verification.json', 'citrine_thermal_conductivity/verification.json'],
        'definition': 'Maximum reference label among the top k predicted candidates. Random curve is the exact expected maximum of k uniformly selected distinct candidate rows.',
        'label_origin': 'Left: GLLB-SC calculation. Right: published experimental conductivity.',
        'uncertainty': 'One frozen composition-group holdout per task; no confidence intervals inferred.',
        'transformation': 'None; plotted directly from verified result JSON.',
        'matplotlib_version': matplotlib.__version__}, indent=2))
