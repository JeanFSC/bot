from mt5_bot.process_guard import (
    ProcessRow,
    audit_duplicate_trades,
    find_duplicate_singleton_groups,
    find_duplicate_supervisor_groups,
    find_duplicate_trade_groups,
    is_live_position_supervisor,
    parse_singleton_process,
    parse_trade_config,
)


def test_parse_trade_config_from_command_line():
    cmd = "python -m mt5_bot trade --config config\\pro_gold.yaml --trade-enabled"

    assert parse_trade_config(cmd) == "config\\pro_gold.yaml"


def test_find_duplicate_trade_groups_allows_normal_uv_pair():
    rows = [
        ProcessRow(1, None, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
        ProcessRow(2, 1, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
    ]

    assert find_duplicate_trade_groups(rows, expected_processes_per_trade=2) == []


def test_find_duplicate_trade_groups_flags_more_than_one_pair():
    rows = [
        ProcessRow(1, None, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
        ProcessRow(2, 1, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
        ProcessRow(3, None, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
        ProcessRow(4, 3, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
    ]

    groups = find_duplicate_trade_groups(rows, expected_processes_per_trade=2)

    assert len(groups) == 1
    assert groups[0].config_path == "config\\pro_gold.yaml"
    assert groups[0].process_count == 4


def test_find_duplicate_trade_groups_can_use_single_process_expectation():
    rows = [
        ProcessRow(1, None, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
        ProcessRow(2, None, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
    ]

    groups = find_duplicate_trade_groups(rows, expected_processes_per_trade=1)

    assert len(groups) == 1
    assert groups[0].process_count == 2


def test_is_live_position_supervisor_detects_continuous_service():
    cmd = "python -m mt5_bot.live_position_supervisor run-continuous --agent-config config/autonomous_agent.yaml"

    assert is_live_position_supervisor(cmd) is True


def test_parse_singleton_process_detects_heat_service():
    cmd = "python -m mt5_bot.portfolio_heat run-continuous --agent-config config/autonomous_agent.yaml"

    assert parse_singleton_process(cmd) == "mt5_bot.portfolio_heat run-continuous"


def test_find_duplicate_supervisor_groups_allows_normal_uv_chain():
    rows = [
        ProcessRow(1, None, "python -m mt5_bot.live_position_supervisor run-continuous"),
        ProcessRow(2, 1, "python -m mt5_bot.live_position_supervisor run-continuous"),
        ProcessRow(3, 2, "python -m mt5_bot.live_position_supervisor run-continuous"),
    ]

    assert find_duplicate_supervisor_groups(rows, expected_processes_per_singleton=3) == []


def test_find_duplicate_supervisor_groups_flags_multiple_services():
    rows = [
        ProcessRow(1, None, "python -m mt5_bot.live_position_supervisor run-continuous"),
        ProcessRow(2, 1, "python -m mt5_bot.live_position_supervisor run-continuous"),
        ProcessRow(3, 2, "python -m mt5_bot.live_position_supervisor run-continuous"),
        ProcessRow(4, None, "python -m mt5_bot.live_position_supervisor run-continuous"),
        ProcessRow(5, 4, "python -m mt5_bot.live_position_supervisor run-continuous"),
        ProcessRow(6, 5, "python -m mt5_bot.live_position_supervisor run-continuous"),
    ]

    groups = find_duplicate_supervisor_groups(rows, expected_processes_per_singleton=3)

    assert len(groups) == 1
    assert groups[0].process_count == 6


def test_find_duplicate_singleton_groups_flags_portfolio_heat_services():
    rows = [
        ProcessRow(1, None, "python -m mt5_bot.portfolio_heat run-continuous"),
        ProcessRow(2, 1, "python -m mt5_bot.portfolio_heat run-continuous"),
        ProcessRow(3, 2, "python -m mt5_bot.portfolio_heat run-continuous"),
        ProcessRow(4, None, "python -m mt5_bot.portfolio_heat run-continuous"),
        ProcessRow(5, 4, "python -m mt5_bot.portfolio_heat run-continuous"),
        ProcessRow(6, 5, "python -m mt5_bot.portfolio_heat run-continuous"),
    ]

    groups = find_duplicate_singleton_groups(rows, expected_processes_per_singleton=3)

    assert len(groups) == 1
    assert groups[0].process_name == "mt5_bot.portfolio_heat run-continuous"
    assert groups[0].process_count == 6


def test_audit_report_includes_expected_process_count(monkeypatch):
    monkeypatch.setattr(
        "mt5_bot.process_guard.collect_process_rows",
        lambda: [ProcessRow(1, None, "python -m mt5_bot trade --config config\\pro_gold.yaml")],
    )

    report = audit_duplicate_trades(expected_processes_per_trade=1)

    assert report["ok"] is True
    assert report["expected_processes_per_trade"] == 1


def test_audit_report_flags_duplicate_supervisor(monkeypatch):
    monkeypatch.setattr(
        "mt5_bot.process_guard.collect_process_rows",
        lambda: [
            ProcessRow(1, None, "python -m mt5_bot.live_position_supervisor run-continuous"),
            ProcessRow(2, None, "python -m mt5_bot.live_position_supervisor run-continuous"),
        ],
    )

    report = audit_duplicate_trades(expected_processes_per_trade=1, expected_processes_per_singleton=1)

    assert report["ok"] is False
    assert report["duplicate_supervisors"][0]["process_count"] == 2
    assert report["duplicate_singletons"][0]["process_count"] == 2
