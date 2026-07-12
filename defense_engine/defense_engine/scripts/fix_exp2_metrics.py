"""Rebuild EXP2_ALL_AGENTS metrics from merged 325 results."""
import json
from collections import defaultdict
from pathlib import Path

path = Path(r'C:\Users\LENOVO\defense_engine\data\experiments.json')
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

exp2 = data['EXP2_ALL_AGENTS']
results = exp2['results']
metrics = exp2['metrics']

LAYER_ORDER = ['source_governance', 'model_interaction', 'memory_control', 'tool_constraint', 'decision_supervision']

# ----- layer_stats -----
layer_stats = {}
for ln in LAYER_ORDER:
    blocked = 0
    total_runs = 0
    total_risk = 0.0
    total_trust = 0.0
    for r in results:
        ld = r.get('layer_details', {})
        layer_info = ld.get(ln, {})
        if layer_info:
            total_runs += 1
            if layer_info.get('action') == 'block' or not layer_info.get('passed', True):
                blocked += 1
            total_risk += layer_info.get('risk_score', 0)
            total_trust += layer_info.get('trust_level', 0)
    n = total_runs if total_runs > 0 else 1
    layer_stats[ln] = {
        'blocked': blocked,
        'total_runs': total_runs,
        'avg_risk': round(total_risk / n, 4),
        'block_rate': round(blocked / n, 4),
        'avg_trust': round(total_trust / n, 4),
    }
metrics['layer_stats'] = layer_stats

print('layer_stats:')
for ln in LAYER_ORDER:
    s = layer_stats[ln]
    print(f"  {ln}: blocked={s['blocked']}/{s['total_runs']} block_rate={s['block_rate']:.4f} avg_risk={s['avg_risk']:.4f}")

# ----- family_layer_stats -----
family_layer_stats = defaultdict(lambda: defaultdict(lambda: {'blocked': 0, 'total_runs': 0}))
for r in results:
    family = r.get('family', 'unknown')
    ld = r.get('layer_details', {})
    for ln in LAYER_ORDER:
        layer_info = ld.get(ln, {})
        if layer_info:
            family_layer_stats[family][ln]['total_runs'] += 1
            if layer_info.get('action') == 'block' or not layer_info.get('passed', True):
                family_layer_stats[family][ln]['blocked'] += 1

fls_dict = {}
for fam in sorted(family_layer_stats.keys()):
    fls_dict[fam] = {}
    for ln in LAYER_ORDER:
        stats = family_layer_stats[fam][ln]
        n = stats['total_runs'] if stats['total_runs'] > 0 else 1
        fls_dict[fam][ln] = {
            'blocked': stats['blocked'],
            'total_runs': stats['total_runs'],
            'block_rate': round(stats['blocked'] / n, 4),
        }
metrics['family_layer_stats'] = fls_dict
print(f'family_layer_stats: {len(fls_dict)} families')

# ----- risk_distribution (from actual risk scores) -----
low = mid = high = 0
for r in results:
    s = r.get('risk_score', 0)
    if s < 0.3:
        low += 1
    elif s < 0.7:
        mid += 1
    else:
        high += 1
metrics['risk_distribution'] = {'low': low, 'mid': mid, 'high': high}
print(f'risk_distribution: low={low} mid={mid} high={high}')

# ----- top_rules -----
rule_hits = defaultdict(int)
for r in results:
    ld = r.get('layer_details', {})
    for ln in LAYER_ORDER:
        layer_info = ld.get(ln, {})
        for rule_id in layer_info.get('matched_rules', []):
            rule_hits[rule_id] += 1
top_rules = sorted(
    [{'rule_id': k, 'rule_name': k, 'hits': v} for k, v in rule_hits.items()],
    key=lambda x: x['hits'], reverse=True
)[:10]
metrics['top_rules'] = top_rules
print(f"top_rules: {[(r['rule_id'], r['hits']) for r in top_rules[:5]]}")

# ----- Also recompute engine_risk_score -----
all_scores = [r.get('risk_score', 0) for r in results]
atk_scores = [r.get('risk_score', 0) for r in results if r.get('is_attack')]
metrics['engine_risk_score'] = round(sum(all_scores) / len(all_scores), 4)
metrics['attack_engine_risk_score'] = round(sum(atk_scores) / len(atk_scores), 4) if atk_scores else 0
print(f"engine_risk_score: {metrics['engine_risk_score']} (attack only: {metrics['attack_engine_risk_score']})")

# Save
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('\nSaved experiments.json')
