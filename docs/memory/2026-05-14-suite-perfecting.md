# 2026-05-14 Suite perfecting audit


## Step 1 - USDJPY M15 scoring mismatch resolved
- Decision: keep config/pro_jpy.yaml risk_pct at 1.5 instead of raising to 1.8.
- Reason: USDJPY exposure already exists twice in suite (USDJPY M15 and USDJPY Asia); raising risk before overlap/de-scoring would increase duplicated JPY/USD theme risk.
- Change: qa_score_review_readonly.py expected risk updated from 1.8 to 1.5 for USDJPY M15.
- Verification: python qa_score_review_readonly.py => OVERALL OK_MATCHES_CLAUDE_SCORE_TABLE.
- Verification: python qa_full_mt5.py => QA_STATIC_OK.
- Verification: python -m pytest -q => 22 passed in 0.40s; pytest emitted a Windows temp cleanup PermissionError after success, not a test failure.


## Steps 2-5 - Suite hardening completed
- Step 2 Portfolio overlap real: rewrote src/mt5_bot/portfolio_guard.py with PortfolioOverlapScore and score_portfolio_overlap(). It now detects exact-symbol duplication (e.g. XAUUSD M15 vs M5, USDJPY M15 vs Asia), same-currency/theme crowding, same-direction theme exposure, and returns block/risk_multiplier/score_penalty details.
- Step 3 De-scoring dynamic: src/mt5_bot/cli.py now applies score_portfolio_overlap() after a real BUY/SELL signal and before risk sizing. Exact/same-currency over-limit signals are converted to NONE with the overlap reason; soft overlap reduces risk via risk_multiplier (0.75 for same currency, 0.50 for same-direction theme).
- Step 4 Smoke test: added qa_suite_smoke.py. It verifies the launcher has 12 starts, all 12 core configs load with demo_only/trade_enabled_false/global guard/magic uniqueness, and then runs mt5_bot check for every config when MT5 env is available.
- Step 5 Journal/audit: src/mt5_bot/storage.py now creates trade_journal and record_trade_journal(). cli.py writes journal rows for candidates, blocks, dry-runs, and sent orders with signal reason, execution result, risk_pct, risk_multiplier, portfolio reason, R:R, spread, equity, ADX/ATR/RSI, and overlap reasons.
- Repo hygiene: .gitignore now excludes logs/, runtime logs, scratch/, sqlite files, and forexfactory cache. Existing tracked logs/cache were removed from the Git index with git rm --cached, preserving local files where present.
- Verification: qa_score_review_readonly.py => OVERALL OK_MATCHES_CLAUDE_SCORE_TABLE.
- Verification: qa_full_mt5.py => QA_STATIC_OK.
- Verification: qa_suite_smoke.py => SMOKE_OK all 12 configs passed MT5 check on MetaQuotes-Demo.
- Verification: python -m pytest -q => 24 passed in 0.41s; pytest still emits Windows temp cleanup PermissionError after success, not a suite failure.
- Safety: no live trading enabled; execution configs remain trade_enabled=false and checks used MT5 readiness only.
