"""Predeclared 23 Nov protocol targets; research only, never live probabilities."""
from market_turning_feature_lab import series, feature_row
from market_turning_walkforward import fit, predict, metrics
from market_turning_conditional_ablations import episode_block_skill_ci, year_block_brier_skill_ci

TARGETS = {
    "tactical_rebound": (20, 7, 5, False),
    "cyclical_bottom": (60, 10, 8, False),
    "top_reversal": (20, 7, 5, True),
}
KEYS = ("drawdown_126_pct", "vix_percentile_126", "vix_1m_3m_ratio",
        "rsi_weekly_14", "mfi_daily_14", "hyg_lqd_change_5_pct")

def eligible(closes, i, target):
    if i < 125:
        return False
    _, stress, _, top = TARGETS[target]
    past = closes[i-125:i+1]
    return closes[i] >= min(past)*(1+stress/100) if top else closes[i] <= max(past)*(1-stress/100)

def outcome(closes, i, target):
    horizon, _, gain, top = TARGETS[target]
    if not eligible(closes, i, target) or i+horizon >= len(closes):
        return None
    anchor = closes[i]
    hit = False
    for price in closes[i+1:i+horizon+1]:
        if (price > anchor*1.03 if top else price < anchor*.97):
            return False
        if (price <= anchor*(1-gain/100) if top else price >= anchor*(1+gain/100)):
            hit = True
            if target != "cyclical_bottom":
                return True
    return hit

def evaluate_protocol(raw, observations=None):
    histories = {k: series(raw,k) for k in ("SPY", "^VIX", "^VVIX", "^COR1M", "^VIX3M", "HYG", "LQD")}
    spy = histories["SPY"]
    closes = [row["close"] for row in spy]
    if observations is None:
        observations = []
        for i in range(125,len(spy)-20):
            features = feature_row(histories,spy[i]["date"])
            if features is not None:
                observations.append({"index":i,"date":spy[i]["date"],"features":features})
    result = {}
    for target, (horizon, _, _, top) in TARGETS.items():
        episodes = {}
        previous = -1000
        block = -1
        for i in range(125, len(closes)-horizon):
            if eligible(closes, i, target):
                if i-previous > 20:
                    block += 1
                episodes[i] = block
                previous = i
        samples = []
        keys = (("runup_126_pct",)+KEYS[1:]) if top else KEYS
        for row in observations:
            i = row["index"]
            if i not in episodes:
                continue
            features = dict(row["features"])
            if top:
                features["runup_126_pct"] = 100*(closes[i]/min(closes[i-125:i+1])-1)
            if any(features.get(k) is None for k in keys):
                continue
            samples.append({**row, "features": features, "label": int(outcome(closes,i,target))})
        full, base, price_only, years, blocks = [], [], [], [], []
        vvix_samples = [r for r in samples if r['features'].get('vvix_percentile_126') is not None]
        vvix_control, vvix_augmented, vvix_years, vvix_blocks = [], [], [], []
        vvix_last = -1000
        last = -1000
        for start in range(1133, len(closes)-horizon, 252):
            train = [r for r in samples if r["index"] < start-horizon-20]
            if len(train)<150:
                continue
            models = fit(train,keys), fit(train,keys[:1])
            if any(m is None for m in models):
                continue
            prevalence = sum(r["label"] for r in train)/len(train)
            for r in samples:
                i = r["index"]
                if not start<=i<start+252 or i-last<horizon:
                    continue
                last=i
                y=r["label"]
                full.append((predict(models[0],r["features"],keys),y))
                price_only.append((predict(models[1],r["features"],keys[:1]),y))
                base.append((prevalence,y))
                years.append(int(r["date"][:4]))
                blocks.append(episodes[i])
        # Separate paired experiment: both variants use identical VVIX-complete
        # training and test rows; do not change the primary benchmark universe.
        augmented_keys = keys + ("vvix_percentile_126",)
        for start in range(1133, len(closes)-horizon, 252):
            train = [r for r in vvix_samples if r["index"] < start-horizon-20]
            if len(train)<150:
                continue
            control_model = fit(train,keys)
            augmented_model = fit(train,augmented_keys)
            if control_model is None or augmented_model is None:
                continue
            for r in vvix_samples:
                i = r["index"]
                if not start<=i<start+252 or i-vvix_last<horizon:
                    continue
                vvix_last=i
                y=r["label"]
                vvix_control.append((predict(control_model,r["features"],keys),y))
                vvix_augmented.append((predict(augmented_model,r["features"],augmented_keys),y))
                vvix_years.append(int(r["date"][:4]))
                vvix_blocks.append(episodes[i])
        result[target] = {"horizon_sessions":horizon,"eligible_sessions":len(episodes),
            "vvix_incremental_experiment":{
                "complete_samples":len(vvix_samples),
                "control":metrics(vvix_control),
                "augmented":metrics(vvix_augmented),
                "paired_episode_ci":episode_block_skill_ci(vvix_augmented,vvix_control,vvix_blocks),
                "paired_year_ci":year_block_brier_skill_ci(vvix_augmented,vvix_control,vvix_years),
                "live_vote_authorized":False},
            "complete_samples":len(samples),"model":metrics(full),"baseline":metrics(base),
            "price_only":metrics(price_only),
            "vs_baseline_episode_ci":episode_block_skill_ci(full,base,blocks),
            "vs_baseline_year_ci":year_block_brier_skill_ci(full,base,years),
            "vs_price_only_episode_ci":episode_block_skill_ci(full,price_only,blocks),
            "vs_price_only_year_ci":year_block_brier_skill_ci(full,price_only,years)}
    return {"research_only":True,"live_probability_authorized":False,
            "original_vintages_verified":False,"targets":result}
