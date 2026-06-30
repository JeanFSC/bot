from mt5_bot.process_guard import (
    ProcessRow,
    audit_duplicate_trades,
    find_duplicate_trade_groups,
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

    assert find_duplicate_trade_groups(rows) == []


def test_find_duplicate_trade_groups_flags_more_than_one_pair():
    rows = [
        ProcessRow(1, None, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
        ProcessRow(2, 1, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
        ProcessRow(3, None, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
        ProcessRow(4, 3, "python -m mt5_bot trade --config config\\pro_gold.yaml"),
    ]

    groups = find_duplicate_trade_groups(rows)

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


def test_audit_report_includes_expected_process_count(monkeypatch):
    monkeypatch.setattr(
        "mt5_bot.process_guard.collect_process_rows",
        lambda: [ProcessRow(1, None, "python -m mt5_bot trade --config config\\pro_gold.yaml")],
    )

    report = audit_duplicate_trades(expected_processes_per_trade=1)

    assert report["ok"] is True
    assert report["expected_processes_per_trade"] == 1
