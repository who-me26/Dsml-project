"""
A/B Test Hypothesis Analysis: Old landing page vs New landing page
Dataset: ab_data.csv  (user_id, timestamp, group, landing_page, converted)
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, proportion_confint
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

ALPHA = 0.05

# ---------------------------------------------------------------- 1. Load
df = pd.read_csv("ab_data.csv")
print("Raw shape:", df.shape)

# ---------------------------------------------------------------- 2. Clean
# (a) control must see old_page, treatment must see new_page
mismatch = ~(((df.group == "control") & (df.landing_page == "old_page")) |
             ((df.group == "treatment") & (df.landing_page == "new_page")))
print("Mismatched group/page rows removed:", mismatch.sum())
df = df[~mismatch]

# (b) users appearing more than once -> keep first visit only
dups = df.user_id.duplicated().sum()
print("Duplicate user_id rows removed:", dups)
df = df.drop_duplicates(subset="user_id", keep="first")
print("Clean shape:", df.shape)

# ---------------------------------------------------------------- 3. Summary
summary = df.groupby("group")["converted"].agg(["count", "sum", "mean"])
summary.columns = ["users", "conversions", "conversion_rate"]
print("\n", summary)

n_c, x_c = summary.loc["control", ["users", "conversions"]].astype(int)
n_t, x_t = summary.loc["treatment", ["users", "conversions"]].astype(int)
p_c, p_t = x_c / n_c, x_t / n_t
diff = p_t - p_c

# ---------------------------------------------------------------- 4. Hypotheses
# H0: p_new <= p_old   (new page is no better)
# H1: p_new >  p_old   (new page converts better)   -> one-sided test
z, p_one = proportions_ztest([x_t, x_c], [n_t, n_c], alternative="larger")
_, p_two = proportions_ztest([x_t, x_c], [n_t, n_c], alternative="two-sided")

# Chi-square cross-check
chi2, p_chi, _, _ = stats.chi2_contingency(
    pd.crosstab(df.group, df.converted), correction=False)

# 95% CI for the difference (unpooled)
se = np.sqrt(p_c*(1-p_c)/n_c + p_t*(1-p_t)/n_t)
ci = (diff - 1.96*se, diff + 1.96*se)

# Power: smallest effect detectable with 80% power
mde = NormalIndPower().solve_power(effect_size=None, nobs1=n_c, alpha=ALPHA,
                                   power=0.8, ratio=n_t/n_c)

# Bootstrap-free simulation check (permutation test)
rng = np.random.default_rng(42)
conv = df.converted.values
labels = (df.group == "treatment").values
obs = conv[labels].mean() - conv[~labels].mean()
sims = np.empty(10000)
for i in range(10000):
    perm = rng.permutation(labels)
    sims[i] = conv[perm].mean() - conv[~perm].mean()
p_perm = (sims >= obs).mean()

print(f"\nControl (old) rate   : {p_c:.4%}")
print(f"Treatment (new) rate : {p_t:.4%}")
print(f"Difference           : {diff:.4%}")
print(f"95% CI of difference : [{ci[0]:.4%}, {ci[1]:.4%}]")
print(f"z-statistic          : {z:.4f}")
print(f"p-value (one-sided)  : {p_one:.4f}")
print(f"p-value (two-sided)  : {p_two:.4f}")
print(f"Chi-square p-value   : {p_chi:.4f}")
print(f"Permutation p-value  : {p_perm:.4f}")
print(f"Min detectable effect (80% power, Cohen's h): {mde:.4f}")
print("\nDecision:", "REJECT H0" if p_one < ALPHA else "FAIL TO REJECT H0",
      f"at alpha = {ALPHA}")

# ---------------------------------------------------------------- 5. Plots
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
rates = [p_c*100, p_t*100]
errs = [1.96*np.sqrt(p_c*(1-p_c)/n_c)*100, 1.96*np.sqrt(p_t*(1-p_t)/n_t)*100]
ax[0].bar(["Control\n(old page)", "Treatment\n(new page)"], rates,
          yerr=errs, capsize=8, color=["#4C72B0", "#DD8452"])
ax[0].set_ylabel("Conversion rate (%)")
ax[0].set_title("Conversion rate with 95% CI")
for i, r in enumerate(rates):
    ax[0].text(i, r/2, f"{r:.2f}%", ha="center", color="white", fontweight="bold")

ax[1].hist(sims*100, bins=50, color="lightgray", edgecolor="gray")
ax[1].axvline(obs*100, color="red", lw=2, label=f"Observed = {obs*100:.3f} pp")
ax[1].set_title("Permutation test: difference under H0")
ax[1].set_xlabel("Difference in conversion rate (percentage points)")
ax[1].legend()
plt.tight_layout()
plt.savefig("images/ab_test_results.png", dpi=150)

# ---------------------------------------------------------------- 6. Save
results = dict(
    users_control=n_c, users_treatment=n_t,
    conv_control=round(p_c, 6), conv_treatment=round(p_t, 6),
    difference=round(diff, 6), ci_low=round(ci[0], 6), ci_high=round(ci[1], 6),
    z=round(z, 4), p_one_sided=round(p_one, 4), p_two_sided=round(p_two, 4),
    p_chi_square=round(p_chi, 4), p_permutation=round(p_perm, 4),
    min_detectable_effect_h=round(mde, 4),
    mismatched_removed=int(mismatch.sum()), duplicates_removed=int(dups),
)
json.dump(results, open("results.json", "w"), indent=2)
