from mt5_bot.process_guard import ProcessRow, find_duplicate_trade_groups, parse_trade_config


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
