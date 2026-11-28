"""Generate the policies table: the insurance contracts that claims are made against.

Each row is one yearly policy bought by a business. This is the clean "truth"
version. Real-world messiness is added later by the mess-maker.
"""

import numpy as np
import pandas as pd
from faker import Faker

from claim_severity.config import DataGeneration

POLICY_TERM_DAYS = 365

# How risky each industry is (1.0 = average). Riskier businesses claim more often and pay more.
INDUSTRY_HAZARD = {
    "construction": 1.6,
    "trucking": 1.5,
    "manufacturing": 1.3,
    "healthcare": 1.1,
    "hospitality": 1.0,
    "retail": 0.9,
    "professional_services": 0.6,
}

# Yearly premium (USD) for an average-risk business with 10 employees.
BASE_PREMIUM = {
    "commercial_auto": 6_000,
    "general_liability": 3_000,
    "workers_compensation": 5_000,
    "commercial_property": 4_000,
}

# (choices, probabilities): each list of probabilities adds up to 1.0
STATES = (
    ["CA", "TX", "FL", "NY", "IL", "PA", "OH", "GA", "NC", "MI"],
    [0.18, 0.15, 0.12, 0.11, 0.08, 0.08, 0.08, 0.07, 0.07, 0.06],
)
COVERAGE_LIMITS = ([500_000, 1_000_000, 2_000_000, 5_000_000], [0.25, 0.45, 0.20, 0.10])
DEDUCTIBLES = ([1_000, 2_500, 5_000, 10_000, 25_000], [0.20, 0.30, 0.25, 0.15, 0.10])


def generate_policies(gen: DataGeneration, rng: np.random.Generator) -> pd.DataFrame:
    """Return one row per policy, numbered in the order the policies started."""
    n = gen.n_policies
    fake = Faker("en_US")
    fake.seed_instance(int(rng.integers(0, 2**32)))  # Faker follows our seed too

    product_line = rng.choice(
        list(gen.product_line_mix), size=n, p=list(gen.product_line_mix.values())
    )
    industry = rng.choice(list(INDUSTRY_HAZARD), size=n)
    hazard = pd.Series(industry).map(INDUSTRY_HAZARD).to_numpy()

    # Most businesses are small and a few are large (lognormal). Always at least 1 employee.
    employee_count = np.maximum(1, rng.lognormal(mean=np.log(20), sigma=1.0, size=n).round())

    # A policy can start up to one year before start_date, so it still covers early claims.
    first_start = pd.Timestamp(gen.start_date) - pd.Timedelta(days=POLICY_TERM_DAYS - 1)
    span_days = (pd.Timestamp(gen.end_date) - first_start).days
    effective_date = first_start + pd.to_timedelta(rng.integers(0, span_days + 1, size=n), unit="D")

    # Premium grows with size and risk, plus some noise for pricing differences.
    base = pd.Series(product_line).map(BASE_PREMIUM).to_numpy()
    premium = base * (employee_count / 10) ** 0.8 * hazard * rng.lognormal(0, 0.25, size=n)

    policies = pd.DataFrame(
        {
            "insured_name": [fake.company() for _ in range(n)],
            "product_line": product_line,
            "industry": industry,
            "state": rng.choice(STATES[0], size=n, p=STATES[1]),
            "employee_count": employee_count.astype(int),
            "effective_date": effective_date,
            "expiry_date": effective_date + pd.Timedelta(days=POLICY_TERM_DAYS),
            "annual_premium": premium.round(2),
            "coverage_limit": rng.choice(COVERAGE_LIMITS[0], size=n, p=COVERAGE_LIMITS[1]),
            "deductible": rng.choice(DEDUCTIBLES[0], size=n, p=DEDUCTIBLES[1]),
        }
    )

    # Real systems hand out policy numbers in order, so sort by start date first.
    policies = policies.sort_values("effective_date", kind="stable", ignore_index=True)
    policies.insert(0, "policy_id", [f"POL-{i:06d}" for i in range(1, n + 1)])
    return policies
