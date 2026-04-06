"""Property-based tests for configuration validation.

# Feature: codex-dev-team, Property 13: Configuration requires all env vars
"""
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from config import load_config, Settings

_ALL_VARS = list(Settings.model_fields.keys())


@settings(max_examples=100)
@given(
    present=st.frozensets(
        st.sampled_from(_ALL_VARS), min_size=0, max_size=len(_ALL_VARS) - 1
    )
)
def test_missing_env_vars_raise_validation_error(present):
    """Property 13: Configuration requires all env vars
    For any subset of required env vars that is missing at least one,
    load_config() should raise ValidationError.

    # Feature: codex-dev-team, Property 13: Configuration requires all env vars
    Validates: Requirements 6.3
    """
    env = {var: "dummy-value" for var in present}
    cleared = {var: "" for var in _ALL_VARS if var not in present}
    with patch.dict(os.environ, {**cleared, **env}, clear=False):
        saved = {}
        for var in _ALL_VARS:
            if var not in present:
                saved[var] = os.environ.pop(var, None)
        try:
            with pytest.raises(ValidationError):
                load_config()
        finally:
            for var, val in saved.items():
                if val is not None:
                    os.environ[var] = val
                else:
                    os.environ.pop(var, None)


@settings(max_examples=100)
@given(
    values=st.fixed_dictionaries(
        {var: st.text(min_size=1, alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00")) for var in _ALL_VARS}
    )
)
def test_all_env_vars_present_succeeds(values):
    """Property 13 (complement): When all required env vars are present,
    load_config() should succeed and return all values.

    # Feature: codex-dev-team, Property 13: Configuration requires all env vars
    Validates: Requirements 6.3
    """
    with patch.dict(os.environ, values):
        result = load_config()

    assert set(result.keys()) == set(_ALL_VARS)
    for var, val in values.items():
        assert result[var] == val
