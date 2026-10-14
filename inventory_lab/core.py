"""Original, standard-library-only inventory simulator; currency is integer cents."""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
import random
import statistics

POLICIES = ('fixed_periodic', 'rolling_mean', 'seasonal_buffer')

@dataclass(frozen=True)
class Config:
    seed: int = 7
    skus: int = 24
    days: int = 180
    warmup: int = 56
    lead_days: int = 4
    review_days: int = 7
    daily_budget_cents: int = 1800000
    order_fee_cents: int = 250
    holding_bps: int = 5  # daily basis points of acquisition value
    shortage_cents: int = 900
    demand_scale: float = 1.0
    service_target: float = .95

    def validate(self):
        for name in ('seed', 'skus', 'days', 'warmup', 'lead_days', 'review_days',
                     'daily_budget_cents', 'order_fee_cents', 'holding_bps', 'shortage_cents'):
            if type(getattr(self, name)) is not int:
                raise ValueError(f'{name} must be an integer')
        if not 1 <= self.skus <= 50 or self.days < 1 or self.warmup < 28:
            raise ValueError('Require 1–50 SKUs, positive days and at least 28 warmup days')
        if self.lead_days < 1 or self.review_days < 1:
            raise ValueError('Lead and review days must be positive')
        if min(self.daily_budget_cents, self.order_fee_cents, self.holding_bps, self.shortage_cents) < 0:
            raise ValueError('Budgets and costs must be nonnegative')
        if not math.isfinite(self.demand_scale) or self.demand_scale < 0:
            raise ValueError('Demand scale must be finite and nonnegative')
        if not math.isfinite(self.service_target) or not 0 <= self.service_target <= 1:
            raise ValueError('Service target must be between zero and one')


def generate(config):
    """Distinct seeded streams for each SKU; no external/private data."""
    config.validate()
    catalog, demands = [], {}
    for index in range(config.skus):
        rng = random.Random(config.seed * 100003 + index)
        sku = f'SKU-{index + 1:03d}'
        base = rng.uniform(1.5, 12)
        unit_cost = rng.randint(250, 2500)
        catalog.append(dict(sku=sku, unit_cost_cents=unit_cost,
                            lead_days=config.lead_days + index % 3))
        series = []
        for day in range(config.warmup + config.days):
            weekly = (0.7, 0.8, 0.95, 1.0, 1.25, 1.5, 0.8)[day % 7]
            trend = 1 + .001 * day
            mean = base * weekly * trend * config.demand_scale
            # Gaussian count approximation, rounded/clipped. Some intermittent SKUs.
            value = max(0, int(rng.gauss(mean, math.sqrt(mean) * 1.15) + .5))
            if index % 6 == 0 and rng.random() < .35:
                value = 0
            series.append(value)
        demands[sku] = series
    validate_data(config, catalog, demands)
    return catalog, demands


def validate_data(config, catalog, demands):
    config.validate()
    ids = [row['sku'] for row in catalog]
    if len(ids) != config.skus or len(set(ids)) != len(ids):
        raise ValueError('Catalog has duplicate keys or wrong SKU count')
    if set(ids) != set(demands):
        raise ValueError('Demand has orphan or missing SKU keys')
    for row in catalog:
        for field in ('unit_cost_cents', 'lead_days'):
            if type(row.get(field)) is not int or row[field] < 1:
                raise ValueError(f'Invalid or missing {field}')
        values = demands[row['sku']]
        if len(values) != config.warmup + config.days:
            raise ValueError('Incomplete daily series: no implicit zero filling')
        if any(type(value) is not int or value < 0 for value in values):
            raise ValueError('Demand must contain nonnegative integer counts')


def estimate(history, policy, protection):
    """History ends today. Only predict tomorrow and later."""
    if policy == 'fixed_periodic':
        raise ValueError('Fixed policy uses its frozen training estimate')
    recent = history[-28:]
    mean = statistics.mean(recent)
    if policy == 'rolling_mean':
        return math.ceil(mean * protection)
    if policy != 'seasonal_buffer':
        raise ValueError('Unknown policy')
    total = 0.0
    for ahead in range(1, protection + 1):
        target_weekday = (len(history) + ahead - 1) % 7
        matches = [history[i] for i in range(max(0, len(history)-28), len(history))
                   if i % 7 == target_weekday]
        total += statistics.mean(matches) if matches else mean
    # A heuristic 1.28-sigma buffer, not a calibrated service-level guarantee.
    return math.ceil(total + 1.28 * statistics.pstdev(recent) * math.sqrt(protection))


def simulate(config, catalog, demands, policy):
    validate_data(config, catalog, demands)
    if policy not in POLICIES:
        raise ValueError('Unknown policy')
    histories = {sku: values[:config.warmup] for sku, values in demands.items()}
    rates = {sku: statistics.mean(values) for sku, values in histories.items()}
    on_hand = {row['sku']: math.ceil(rates[row['sku']] * (row['lead_days'] + config.review_days - 1))
               for row in catalog}
    pipeline = {row['sku']: [] for row in catalog}
    records = []
    for day in range(config.days):
        cash = config.daily_budget_cents
        candidates, day_rows = [], {}
        for row in catalog:
            sku, cost, lead = row['sku'], row['unit_cost_cents'], row['lead_days']
            opening = on_hand[sku]
            receipts = sum(qty for due, qty in pipeline[sku] if due == day)
            pipeline[sku] = [(due, qty) for due, qty in pipeline[sku] if due > day]
            demand = demands[sku][config.warmup + day]
            fulfilled = min(demand, opening + receipts)
            closing = opening + receipts - fulfilled
            on_hand[sku] = closing
            histories[sku].append(demand)  # latent demand is observable in this benchmark
            position = closing + sum(qty for _, qty in pipeline[sku])
            review = day % config.review_days == 0
            target = 0
            requested = 0
            if review:
                protection = lead + config.review_days - 1
                target = (math.ceil(rates[sku] * protection) if policy == 'fixed_periodic'
                          else estimate(histories[sku], policy, protection))
                requested = max(0, target - position)
                # Same deterministic scarcity allocator for every policy.
                coverage = position / max(rates[sku], .001)
                candidates.append((coverage, sku, cost, lead, requested))
            day_rows[sku] = dict(seed=config.seed, policy=policy, day=day, sku=sku,
                opening=opening, receipts=receipts, demand=demand, fulfilled=fulfilled,
                lost=demand-fulfilled, closing=closing, target=target, requested=requested,
                ordered=0, purchase_cents=0, fee_cents=0,
                holding_cents=closing*cost*config.holding_bps/10000,
                shortage_cents=(demand-fulfilled)*config.shortage_cents,
                budget_blocked=0, pipeline_units=sum(qty for _, qty in pipeline[sku]))
        for _, sku, cost, lead, requested in sorted(candidates):
            affordable = max(0, (cash - config.order_fee_cents) // cost)
            ordered = min(requested, affordable)
            rec = day_rows[sku]
            rec['budget_blocked'] = int(ordered < requested)
            if ordered:
                spend = ordered * cost + config.order_fee_cents
                cash -= spend
                pipeline[sku].append((day + lead, ordered))
                rec.update(ordered=ordered, purchase_cents=ordered*cost,
                           fee_cents=config.order_fee_cents)
                rec['pipeline_units'] += ordered
        for row in catalog:
            rec = day_rows[row['sku']]
            rec['daily_cash_remaining_cents'] = cash
            records.append(rec)
    return records


def fingerprint(config, catalog, demands):
    payload = dict(config=asdict(config), catalog=catalog, demands=demands)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
