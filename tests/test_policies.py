"""Fire drills for the policies table: right shape, valid values, repeatable, realistic."""

import dataclasses

import numpy as np
import pandas as pd
import pytest

from claim_severity.config import load_settings
from claim_severity.data_generation.policies import (
    INDUSTRY_HAZARD,
    POLICY_TERM_DAYS,
    STATES,
    generate_policies,
)

N_POLICIES = 2_000  # small enough to be fast, big enough for averages to settle


# ── Helpers ───────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def gen():
    """The real generation settings, shrunk to a small, fast size."""
    return dataclasses.replace(load_settings().data_generation, n_policies=N_POLICIES)


@pytest.fixture(scope="module")
def policies(gen):
    """One table, built once and shared by every test in this file (read-only)."""
    return generate_policies(gen, np.random.default_rng(42))


# ── Shape ─────────────────────────────────────────────────────────
def test_one_row_per_policy(policies):
    assert len(policies) == N_POLICIES


def test_expected_columns_in_order(policies):
    assert list(policies.columns) == [
        "policy_id",
        "insured_name",
        "product_line",
        "industry",
        "state",
        "employee_count",
        "effective_date",
        "expiry_date",
        "annual_premium",
        "coverage_limit",
        "deductible",
    ]


# ── IDs ───────────────────────────────────────────────────────────
def test_policy_ids_are_unique_and_well_formed(policies):
    assert policies["policy_id"].is_unique
    assert policies["policy_id"].str.fullmatch(r"POL-\d{6}").all()
    assert policies["policy_id"].iloc[0] == "POL-000001"


def test_policies_are_numbered_in_start_date_order(policies):
    assert policies["effective_date"].is_monotonic_increasing


# ── Valid values ──────────────────────────────────────────────────
def test_categories_come_from_the_allowed_lists(policies, gen):
    assert set(policies["product_line"]) <= set(gen.product_line_mix)
    assert set(policies["industry"]) <= set(INDUSTRY_HAZARD)
    assert set(policies["state"]) <= set(STATES[0])


def test_every_policy_lasts_one_year(policies):
    term = policies["expiry_date"] - policies["effective_date"]
    assert (term == pd.Timedelta(days=POLICY_TERM_DAYS)).all()


def test_start_dates_fall_in_the_allowed_window(policies, gen):
    earliest = pd.Timestamp(gen.start_date) - pd.Timedelta(days=POLICY_TERM_DAYS - 1)
    assert policies["effective_date"].min() >= earliest
    assert policies["effective_date"].max() <= pd.Timestamp(gen.end_date)


def test_counts_and_money_are_positive(policies):
    assert (policies["employee_count"] >= 1).all()
    assert (policies["annual_premium"] > 0).all()


# ── Reproducible ──────────────────────────────────────────────────
def test_same_seed_gives_identical_table(gen, policies):
    again = generate_policies(gen, np.random.default_rng(42))
    pd.testing.assert_frame_equal(policies, again)


def test_different_seed_gives_different_table(gen, policies):
    other = generate_policies(gen, np.random.default_rng(7))
    assert not policies.equals(other)


# ── Realistic (the hidden recipe works) ───────────────────────────
def test_product_line_shares_follow_the_settings(policies, gen):
    shares = policies["product_line"].value_counts(normalize=True)
    for line, expected in gen.product_line_mix.items():
        assert shares[line] == pytest.approx(expected, abs=0.04)


def test_riskier_industries_pay_more(policies):
    # Remove the size effect, then compare the riskiest and safest industries.
    size_adjusted = policies["annual_premium"] / policies["employee_count"] ** 0.8
    median_by_industry = size_adjusted.groupby(policies["industry"]).median()
    assert median_by_industry["construction"] > median_by_industry["professional_services"]
