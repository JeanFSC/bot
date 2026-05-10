"""
broker_profile.py - Load real broker specs from MT5 diagnostic JSON.

Replaces hardcoded _PIP_VALUE_PER_LOT and _DEFAULT_SLIPPAGE_PIPS in
backtest_engine.py with values measured against the user's actual broker.

Usage:
    profile = BrokerProfile.auto_detect()        # tries data/diag/symbol_specs.json
    profile = BrokerProfile.from_json(path)      # explicit path
    profile = BrokerProfile.empty()              # no profile, use hardcoded fallbacks

Then pass to BacktestParams(broker_profile=profile).

Falls back to hardcoded defaults for any symbol or field missing from the profile.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


_DEFAULT_DIAG_PATH = Path("data/diag/symbol_specs.json")


@dataclass
class BrokerProfile:
    """Per-symbol broker specs (pip_value, slippage, contract_size).

    All maps are optional; lookup falls back to hardcoded defaults when missing.
    """
    pip_values: dict[str, float] = field(default_factory=dict)
    slippage_pips: dict[str, float] = field(default_factory=dict)
    contract_sizes: dict[str, float] = field(default_factory=dict)
    source: str = "hardcoded"

    @classmethod
    def empty(cls) -> "BrokerProfile":
        """Return an empty profile (always falls back to hardcoded)."""
        return cls(source="hardcoded")

    @classmethod
    def from_json(cls, path: str | Path) -> "BrokerProfile":
        """Load broker specs from a diag_symbol_specs.json file.

        Expected format: list of objects each with at least:
          - symbol
          - pip_value_per_lot_broker_calc (or pip_value_per_lot)
          - spread_pips_estimate (optional)
          - trade_contract_size (optional)
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Broker profile not found: {p}")

        rows = json.loads(p.read_text())
        if not isinstance(rows, list):
            raise ValueError(f"Broker profile must be a JSON list: {p}")

        pip_values: dict[str, float] = {}
        slippage_pips: dict[str, float] = {}
        contract_sizes: dict[str, float] = {}

        for row in rows:
            symbol = row.get("symbol")
            if not symbol:
                continue
            pv = row.get("pip_value_per_lot_broker_calc")
            if pv is None:
                pv = row.get("pip_value_per_lot")
            if pv is not None and pv > 0:
                pip_values[symbol] = float(pv)
            sp = row.get("spread_pips_estimate")
            if sp is not None and sp > 0:
                slippage_pips[symbol] = float(sp)
            cs = row.get("trade_contract_size")
            if cs is not None and cs > 0:
                contract_sizes[symbol] = float(cs)

        return cls(
            pip_values=pip_values,
            slippage_pips=slippage_pips,
            contract_sizes=contract_sizes,
            source=str(p),
        )

    @classmethod
    def auto_detect(cls, path: Optional[str | Path] = None) -> "BrokerProfile":
        """Return profile from path (or default) if it exists, else empty."""
        target = Path(path) if path else _DEFAULT_DIAG_PATH
        if target.exists():
            return cls.from_json(target)
        return cls.empty()

    def pip_value(self, symbol: str, fallback: float) -> float:
        return self.pip_values.get(symbol.upper(), fallback)

    def slippage(self, symbol: str, fallback: float) -> float:
        return self.slippage_pips.get(symbol.upper(), fallback)

    def has_symbol(self, symbol: str) -> bool:
        return symbol.upper() in self.pip_values

    def __len__(self) -> int:
        return len(self.pip_values)

    def summary(self) -> str:
        if not self.pip_values:
            return "(empty profile - using hardcoded fallbacks)"
        lines = [f"Broker profile from {self.source} ({len(self.pip_values)} symbols):"]
        for sym in sorted(self.pip_values):
            pv = self.pip_values[sym]
            sp = self.slippage_pips.get(sym, "?")
            lines.append(f"  {sym:<10} pip_value={pv:>8.4f}  slippage={sp}")
        return "\n".join(lines)
