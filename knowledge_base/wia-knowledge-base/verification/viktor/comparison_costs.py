"""Offline price illustrations and archived Viktor-message inventory; no APIs or tokens."""
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
CREDIT_USD = Decimal('0.0025')
FEE = Decimal('1.055')
INPUT_TOKENS, OUTPUT_TOKENS = 10000, 1000
RECALLED_MONTHLY_BASELINE = Decimal('1000')
MODELS = {
    'Gemini 3.1 Flash Lite illustration': (Decimal('0.25'), Decimal('1.50')),
    'Claude Sonnet 4.6 illustration': (Decimal('3'), Decimal('15')),
}
RAILWAY_RATES = {'ram_gb_month': Decimal('10'), 'cpu_vcpu_month': Decimal('20'),
                 'volume_gb_month': Decimal('0.15'), 'egress_gb': Decimal('0.05')}

def amount(value):
    return float(value.quantize(Decimal('0.000001')))

scenarios = []
for clients in [15, 20, 30, 40]:
    runs = clients * 30  # illustrative one analysis/client/day, not an agreed schedule
    costs = {}
    for model, (price_in, price_out) in MODELS.items():
        per_run = (Decimal(INPUT_TOKENS) * price_in + Decimal(OUTPUT_TOKENS) * price_out) / 1000000
        costs[model] = {'inference_usd': amount(per_run * runs),
                        'with_standard_credit_purchase_fee_usd': amount(per_run * runs * FEE)}
    scenarios.append({'clients': clients, 'illustrative_monthly_runs': runs,
                      'openrouter': costs,
                      'viktor_quick_task_credit_equivalent_usd': {
                          'at_100_credits_per_run': amount(CREDIT_USD * 100 * runs),
                          'at_300_credits_per_run': amount(CREDIT_USD * 300 * runs)},
                      'unconditional_15_minute_per_client_runs_30_days': clients * 96 * 30})

messages = {}
raw_files = list((ROOT / 'frontend/corpus/slack/raw').glob('*.json'))
for source in raw_files:
    content = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(content, list):
        continue
    def scan(items):
        for message in items:
            if not isinstance(message, dict):
                continue
            if message.get('user') == 'U0BPF0MBD45' and message.get('text'):
                key = (source.stem, message.get('ts'))
                messages[key] = {
                    'archive': str(source.relative_to(ROOT)).replace('\\', '/'),
                    'channel_archive_key': source.stem, 'message_ts': message.get('ts'),
                    'author_id': message['user'],
                    'occurred_at_utc': datetime.fromtimestamp(float(message['ts']), timezone.utc).isoformat(),
                    'opening_excerpt': message['text'][:180],
                    'underlying_claims_independently_verified': False,
                }
            for key in ['replies', 'thread_replies', 'thread_messages']:
                if isinstance(message.get(key), list):
                    scan(message[key])
    scan(content)

report = {
    'research_date': '2026-10-20', 'offline_only': True,
    'not_a_benchmark_or_account_bill': True,
    'retained_implementation_candidates': ['selective_hybrid', 'viktor_led'],
    'selected_candidate': None,
    'candidate_evaluation_performed': False,
    'user_reported_baseline': {
        'approximate_monthly_viktor_spend_usd': amount(RECALLED_MONTHLY_BASELINE),
        'basis': 'User recollection; invoice, plan, allowance and usage not verified',
        'workload': 'Team DMs, call preparation and proactive analysis; not equivalent to the prepared-prompt scenarios',
        'gross_reduction_sensitivity_not_a_forecast': [
            {'percentage': percent, 'gross_usd_before_incremental_kb_expenses':
             amount(RECALLED_MONTHLY_BASELINE * Decimal(percent) / 100)}
            for percent in [10, 25, 50]],
        'net_savings': 'Measured Viktor cash-spend reduction minus incremental OpenRouter, Railway and operating costs',
    },
    'assumptions': {'days': 30, 'analyses_per_client_per_day': 1,
                    'input_tokens_per_analysis': INPUT_TOKENS, 'output_tokens_per_analysis': OUTPUT_TOKENS,
                    'viktor_current_plan_credit_usd_equivalent': str(CREDIT_USD),
                    'viktor_quick_task_credits': [100, 300],
                    'openrouter_standard_credit_purchase_fee': '5.5%',
                    'equal_output_quality_not_established': True,
                    'excluded': ['hosting', 'connector resources/provider fees', 'backfill', 'embeddings',
                                 'additional reasoning tokens', 'retries', 'taxes', 'minimum purchase fees',
                                 'existing Viktor subscriptions and other workspace workloads'],
                    'hybrid_cost': 'OpenRouter work actually performed + incremental Viktor work actually performed; avoid duplicate work'},
    'pricing_sources': {
        'viktor_plan_credit_rate': 'https://viktor.com/docs/plans-and-credits',
        'viktor_quick_tasks': 'https://viktor.com/help/category/credits/how-credits-work',
        'fast_model': 'https://openrouter.ai/google/gemini-3.1-flash-lite',
        'strong_model': 'https://openrouter.ai/anthropic/claude-sonnet-4.6',
        'openrouter_fee': 'https://openrouter.ai/pricing',
        'railway': 'https://docs.railway.com/pricing/plans'},
    'scenarios': scenarios,
    'railway_resource_sensitivities': {
        'not_tested_capacity_or_a_total_project_quote': True,
        'rates_usd': {k: str(v) for k, v in RAILWAY_RATES.items()},
        'pro_monthly_minimum_applied_toward_usage_usd': 20,
        'shared_account_allocation_requires_actual_bill': True,
        'excludes': ['AI', 'provider fees', 'separate backups/object storage', 'taxes', 'human operation'],
        'examples': [
            {'combined_average_ram_gb': ram, 'combined_average_vcpu': cpu,
             'volume_gb': volume, 'egress_gb': egress,
             'illustrative_monthly_usage_usd': amount(
                 Decimal(str(ram)) * RAILWAY_RATES['ram_gb_month']
                 + Decimal(str(cpu)) * RAILWAY_RATES['cpu_vcpu_month']
                 + Decimal(volume) * RAILWAY_RATES['volume_gb_month']
                 + Decimal(egress) * RAILWAY_RATES['egress_gb'])}
            for ram, cpu, volume, egress in [(2.5, 0.25, 20, 10), (5, 0.5, 50, 25)]],
    },
    'archived_viktor': {'raw_channel_files_examined': len(raw_files),
                        'message_count': len(messages),
                        'by_channel': dict(Counter(k[0] for k in messages)),
                        'scope': 'Preserved local archive only; not live access, complete history, or measured correctness',
                        'messages': list(messages.values())},
    'paid_agent_runs_started': 0, 'messages_sent': 0,
}
(OUT / 'comparison_costs.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'scenarios': scenarios,
                  'archived_viktor_messages': len(messages),
                  'paid_agent_runs_started': 0}, indent=2))
