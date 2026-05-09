import bot_controller
assert len(bot_controller.BOTS) == 12
n = bot_controller.count_bots()
assert isinstance(n, int) and n >= 0
print('CONTROLLER_QA_OK bots=', len(bot_controller.BOTS), 'processes=', n)
