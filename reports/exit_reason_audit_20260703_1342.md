# MT5 Exit Reason Audit

- Created at: `2026-07-03T13:46:24.645705+00:00`
- Since: `2026-07-01T00:00:00+00:00`
- Closed deal rows: `65`
- Closed rows with archived MFE/MAE: `0`
- Note: older DB rows may lack archived MFE/MAE; new closes should retain it through `position_metrics_history`.

## Summary By Exit Reason

| exit_reason | trades | W/L | net | PF | avg_win | avg_loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sl_loss | 7 | 0/7 | -47.23 | 0.00 | +0.00 | -6.75 |
| bot_close_unknown | 9 | 7/2 | +3.06 | 1.34 | +1.71 | -4.47 |
| protective_sl_profit | 15 | 15/0 | +8.35 | inf | +0.56 | +0.00 |
| bot_client_close_original_comment | 34 | 34/0 | +29.68 | inf | +0.87 | +0.00 |

## Summary By Symbol

| symbol | trades | W/L | net | PF | avg_win | avg_loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| USDCHF | 1 | 0/1 | -9.32 | 0.00 | +0.00 | -9.32 |
| XAUUSD | 2 | 1/1 | -3.34 | 0.49 | +3.26 | -6.60 |
| EURUSD | 5 | 4/1 | -1.63 | 0.75 | +1.19 | -6.40 |
| USDCAD | 13 | 12/1 | -1.18 | 0.84 | +0.51 | -7.33 |
| GBPUSD | 12 | 11/1 | -1.01 | 0.89 | +0.76 | -9.38 |
| GBPJPY | 3 | 2/1 | -0.65 | 0.35 | +0.17 | -1.00 |
| USDJPY | 5 | 4/1 | +0.39 | 2.08 | +0.19 | -0.36 |
| NZDUSD | 6 | 5/1 | +4.41 | 1.51 | +2.60 | -8.58 |
| AUDUSD | 18 | 17/1 | +6.19 | 1.86 | +0.79 | -7.20 |

## Closed Deals

| closed_at | symbol | ticket | pnl | exit_reason | MFE pips | MAE pips | evidence | comment |
| --- | --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| 2026-07-01T06:11:04+00:00 | USDCHF | 9027605545 | -9.32 | sl_loss | n/a | n/a | broker_comment_sl_negative_pnl | [sl 0.80905] |
| 2026-07-01T08:31:32+00:00 | XAUUSD | 9029248068 | +3.26 | bot_close_unknown | n/a | n/a | deal_comment=mt5bot_close_ioc | mt5bot_close_ioc |
| 2026-07-01T14:50:50+00:00 | EURUSD | 9036796874 | +1.70 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T14:54:30+00:00 | EURUSD | 9036894446 | +0.88 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 1.13937] |
| 2026-07-01T14:56:26+00:00 | USDCAD | 9036937977 | +0.44 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T15:00:45+00:00 | USDCAD | 9037036946 | +0.35 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T15:05:03+00:00 | USDCAD | 9037174791 | +0.24 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T15:09:21+00:00 | USDCAD | 9037294105 | +0.37 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T15:13:40+00:00 | USDCAD | 9037400286 | +0.29 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T15:15:08+00:00 | USDCAD | 9037444981 | +0.14 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 1.42201] |
| 2026-07-01T16:42:10+00:00 | NZDUSD | 9040485569 | +2.70 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_ioc | mt5bot_ord_ioc |
| 2026-07-01T16:46:32+00:00 | NZDUSD | 9040801804 | +3.72 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_ioc | mt5bot_ord_ioc |
| 2026-07-01T16:49:06+00:00 | GBPJPY | 9040914441 | +0.18 | bot_close_unknown | n/a | n/a | deal_comment=mt5bot_close_ioc | mt5bot_close_ioc |
| 2026-07-01T16:50:51+00:00 | NZDUSD | 9040970397 | +3.70 | bot_close_unknown | n/a | n/a | deal_comment=mt5bot_close_ioc | mt5bot_close_ioc |
| 2026-07-01T18:47:04+00:00 | EURUSD | 9043963496 | +1.53 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T18:51:19+00:00 | EURUSD | 9044049629 | +0.66 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 1.13843] |
| 2026-07-01T21:48:59+00:00 | USDJPY | 9046911639 | +0.51 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 162.534] |
| 2026-07-01T22:26:30+00:00 | GBPUSD | 9047432988 | +1.15 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T22:30:44+00:00 | GBPUSD | 9047477972 | +0.90 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T22:35:04+00:00 | GBPUSD | 9047526885 | +0.56 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T22:39:22+00:00 | GBPUSD | 9047578403 | +0.29 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T22:43:08+00:00 | GBPUSD | 9047627211 | +0.22 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 1.32798] |
| 2026-07-01T22:55:46+00:00 | AUDUSD | 9047843757 | +0.66 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T22:56:10+00:00 | USDJPY | 9047850210 | +0.08 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 162.548] |
| 2026-07-01T23:00:06+00:00 | AUDUSD | 9047931323 | +0.54 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T23:04:24+00:00 | AUDUSD | 9047943095 | +0.35 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T23:08:43+00:00 | AUDUSD | 9047955539 | +0.39 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T23:10:08+00:00 | USDJPY | 9047960011 | +0.09 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 162.565] |
| 2026-07-01T23:13:02+00:00 | AUDUSD | 9047965623 | +0.37 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-01T23:50:00+00:00 | AUDUSD | 9048124259 | +0.33 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 0.68928] |
| 2026-07-02T00:21:50+00:00 | NZDUSD | 9048227131 | +1.35 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_ioc | mt5bot_ord_ioc |
| 2026-07-02T00:22:00+00:00 | NZDUSD | 9048227408 | +1.52 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 0.56707] |
| 2026-07-02T02:27:42+00:00 | USDJPY | 9048866150 | +0.07 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 162.573] |
| 2026-07-02T02:35:49+00:00 | GBPJPY | 9048924543 | +0.17 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 215.875] |
| 2026-07-02T02:52:37+00:00 | AUDUSD | 9049024862 | +0.48 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T02:53:27+00:00 | AUDUSD | 9049029384 | +0.48 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 0.68907] |
| 2026-07-02T03:42:54+00:00 | XAUUSD | 9049702128 | -6.60 | sl_loss | n/a | n/a | broker_comment_sl_negative_pnl | [sl 4038.62] |
| 2026-07-02T04:11:29+00:00 | NZDUSD | 9050160919 | -8.58 | bot_close_unknown | n/a | n/a | deal_comment=mt5bot_close_ioc | mt5bot_close_ioc |
| 2026-07-02T04:41:13+00:00 | GBPUSD | 9050662910 | +0.72 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T04:45:32+00:00 | GBPUSD | 9050733524 | +0.26 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T04:46:48+00:00 | EURUSD | 9050754991 | -6.40 | sl_loss | n/a | n/a | broker_comment_sl_negative_pnl | [sl 1.13833] |
| 2026-07-02T04:49:25+00:00 | GBPUSD | 9050800041 | +1.05 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T04:52:27+00:00 | GBPUSD | 9050844729 | +1.52 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 1.32873] |
| 2026-07-02T06:12:11+00:00 | AUDUSD | 9052018329 | +1.62 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T06:13:03+00:00 | USDCAD | 9052024633 | +0.41 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T06:16:32+00:00 | AUDUSD | 9052062418 | +0.96 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T06:17:25+00:00 | USDCAD | 9052070921 | +0.24 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T06:20:53+00:00 | AUDUSD | 9052100113 | +0.85 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T06:21:45+00:00 | USDCAD | 9052115711 | +0.25 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T06:25:12+00:00 | AUDUSD | 9052157147 | +0.86 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T06:26:05+00:00 | USDCAD | 9052165837 | +0.41 | bot_close_unknown | n/a | n/a | deal_comment=mt5bot_close_fok | mt5bot_close_fok |
| 2026-07-02T06:29:33+00:00 | AUDUSD | 9052223164 | +1.16 | bot_close_unknown | n/a | n/a | deal_comment=mt5bot_close_fok | mt5bot_close_fok |
| 2026-07-02T06:46:51+00:00 | USDJPY | 9052413751 | -0.36 | bot_close_unknown | n/a | n/a | deal_comment=mt5bot_close_fok | mt5bot_close_fok |
| 2026-07-02T08:09:05+00:00 | GBPUSD | 9053484489 | +0.90 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T08:09:25+00:00 | GBPUSD | 9053490884 | +0.80 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 1.32900] |
| 2026-07-02T17:19:50+00:00 | USDCAD | 9067080694 | +1.46 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T17:20:32+00:00 | USDCAD | 9067102857 | +1.55 | bot_close_unknown | n/a | n/a | deal_comment=mt5bot_close_fok | mt5bot_close_fok |
| 2026-07-02T18:29:54+00:00 | GBPUSD | 9069052903 | -9.38 | sl_loss | n/a | n/a | broker_comment_sl_negative_pnl | [sl 1.33638] |
| 2026-07-02T18:31:35+00:00 | AUDUSD | 9069094135 | +1.02 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T18:40:46+00:00 | AUDUSD | 9069286886 | +1.74 | bot_close_unknown | n/a | n/a | deal_comment=mt5bot_close_fok | mt5bot_close_fok |
| 2026-07-02T23:31:44+00:00 | AUDUSD | 9074064378 | +0.70 | bot_client_close_original_comment | n/a | n/a | deal_comment=mt5bot_ord_fok | mt5bot_ord_fok |
| 2026-07-02T23:36:08+00:00 | AUDUSD | 9074073871 | +0.88 | protective_sl_profit | n/a | n/a | broker_comment_sl_positive_pnl | [sl 0.69227] |
| 2026-07-03T02:38:13+00:00 | USDCAD | 9074782639 | -7.33 | sl_loss | n/a | n/a | broker_comment_sl_negative_pnl | [sl 1.41890] |
| 2026-07-03T03:33:12+00:00 | AUDUSD | 9075342570 | -7.20 | sl_loss | n/a | n/a | broker_comment_sl_negative_pnl | [sl 0.69117] |
| 2026-07-03T12:01:46+00:00 | GBPJPY | 9082174691 | -1.00 | sl_loss | n/a | n/a | broker_comment_sl_negative_pnl | [sl 215.192] |
