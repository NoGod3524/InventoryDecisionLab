-- Grain: one policy × independent synthetic seed. Money is cents.
SELECT seed, policy,
       SUM(demand) AS demand_units,
       SUM(fulfilled) AS fulfilled_units,
       CASE WHEN SUM(demand)=0 THEN NULL ELSE 1.0*SUM(fulfilled)/SUM(demand) END AS fill_rate,
       SUM(CASE WHEN lost>0 THEN 1 ELSE 0 END) AS stockout_sku_days,
       AVG(closing) AS mean_units_per_sku,
       SUM(CASE WHEN ordered>0 THEN 1 ELSE 0 END) AS orders,
       SUM(purchase_cents)/100.0 AS purchase_dollars,
       SUM(holding_cents)/100.0 AS holding_dollars,
       SUM(fee_cents)/100.0 AS order_dollars,
       SUM(shortage_cents)/100.0 AS shortage_dollars,
       SUM(holding_cents+fee_cents+shortage_cents)/100.0 AS modeled_cost_dollars,
       SUM(budget_blocked) AS constrained_sku_reviews
FROM policy_day
GROUP BY seed, policy
ORDER BY seed, policy;
