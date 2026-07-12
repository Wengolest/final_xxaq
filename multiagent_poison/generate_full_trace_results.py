import json
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

root = Path(r'e:\wangan\autogen')
trace_root = root / 'benchmark_workspace_full_trace_strict'
out_dir = root / 'web-attack-results' / 'public' / 'data'
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'full_trace_results.json'

trials = []
for trace_file in sorted(trace_root.glob('*/trace/agent_trace.json')):
    with trace_file.open('r', encoding='utf-8') as f:
        trace = json.load(f)
    scenario = trace.get('scenario') or {}
    result = trace.get('result') or trace.get('verdict') or {}
    raw_messages = trace.get('raw_messages') or []
    parsed_messages = trace.get('parsed_messages') or []
    trial_dir = Path(trace.get('trial_dir') or trace_file.parents[1])
    trial_name = trial_dir.name
    attack_result = {
        'experiment_id': 'benchmark_workspace_full_trace_strict',
        'agent_id': trace.get('orchestrator_type') or 'central_orchestrator',
        'agent_name': 'Full MAS' if trace.get('use_full_mas') else 'Single Agent',
        'attack_id': trial_name,
        'gateway_part_name': result.get('confused_deputy_agent') or result.get('confused_deputy') or '',
        'eval_tier': 'full_trace',
        'bench_pass': bool(result.get('success', False)),
        'timestamp': trace.get('timestamp'),
        'attack_family': scenario.get('category') or scenario.get('name') or 'unknown',
        'delivery_mode': scenario.get('modality') or 'unknown',
        'poisoner_type': scenario.get('error_template') or scenario.get('payload_type') or 'unknown',
        'jailbreak_converter_used': bool(result.get('metadata_poisoned', False)),
        'target_kind': 'multi_agent_system',
        'repo_slug': 'wangan/autogen',
        'repo_folder': str(trace_root),
        'readme_vertical': scenario.get('name') or '',
        'agent_intro': trace.get('orchestrator_type') or '',
        'agent_tags': [x for x in [scenario.get('category'), scenario.get('modality'), scenario.get('payload_type')] if x],
        'prompt_sent': trace.get('user_message') or '',
        'agent_reply': '\n\n'.join(m.get('content', '') for m in raw_messages[-3:]),
        'parallel_manifest': json.dumps({
            'expected_marker': trace.get('expected_marker'),
            'markers_found': result.get('markers_found') or [],
            'message_count': len(raw_messages),
            'parsed_message_count': len(parsed_messages),
            'metadata_poisoned': result.get('metadata_poisoned', False),
            'control_flow_hijacked': result.get('control_flow_hijacked', False),
            'payload_executed': result.get('payload_executed', False),
            'unsafe_code_detected': result.get('unsafe_code_detected', False),
        }, ensure_ascii=False),
        'pilot_note': result.get('notes') or '',
        'final_label': 'success' if result.get('success') else 'failed',
        'scorer_type': 'rule',
        'rule_final_label': 'success' if result.get('success') else 'failed',
        'llm_final_label': None,
        'llm_attack_success': bool(result.get('success', False)),
        'llm_refusal_detected': bool(result.get('refused', False)),
        'llm_risk_score': 1.0 if result.get('success') else 0.0,
        'llm_rationale': f"scenario={scenario.get('name', '')}; confused_deputy={result.get('confused_deputy_agent') or result.get('confused_deputy') or ''}",
        'pyrit_scorer_success': bool(result.get('success', False)),
        'attack_success': bool(result.get('success', False)),
        'refusal_detected': bool(result.get('refused', False)),
        'task_deviation': bool(result.get('control_flow_hijacked', False)),
        'defense_enabled': False,
        'defense_profile': 'none',
        'benchmark_included': True,
        'error': trace.get('error') or '',
    }
    trials.append({
        'trial_name': trial_name,
        'trace_path': str(trace_file),
        'markdown_trace_path': str(trace_file.with_suffix('.md')),
        'trace': trace,
        'attack_result': attack_result,
    })

summary = {
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'source_dir': str(trace_root),
    'total_trials': len(trials),
    'success_count': sum(1 for t in trials if t['attack_result']['attack_success']),
    'refusal_count': sum(1 for t in trials if t['attack_result']['refusal_detected']),
    'payload_executed_count': sum(1 for t in trials if (t['trace'].get('result') or {}).get('payload_executed')),
    'metadata_poisoned_count': sum(1 for t in trials if (t['trace'].get('result') or {}).get('metadata_poisoned')),
    'control_flow_hijacked_count': sum(1 for t in trials if (t['trace'].get('result') or {}).get('control_flow_hijacked')),
    'scenario_counts': dict(Counter((t['trace'].get('scenario') or {}).get('name', 'unknown') for t in trials)),
    'category_counts': dict(Counter((t['trace'].get('scenario') or {}).get('category', 'unknown') for t in trials)),
    'modality_counts': dict(Counter((t['trace'].get('scenario') or {}).get('modality', 'unknown') for t in trials)),
}

payload = {
    'schema_version': 1,
    'summary': summary,
    'attack_results': [t['attack_result'] for t in trials],
    'trials': trials,
}
with out_file.open('w', encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
print(out_file)
print(json.dumps(summary, ensure_ascii=False, indent=2))
