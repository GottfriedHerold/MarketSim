from market import Balance


def test_import():
    """
    Just makes sure that pytest actually runs this and imports the market package
    """
    pass


def test_balance():
    # other values set to 0.
    b = Balance(received=20, payed=10, capital_cost=4)
    assert b.total_balance == 6
    b.received += 5
    assert b.total_balance == 11
    b.payed += 20
    assert b.total_balance == -9
    assert b.reputation_factor == 1  # NOTE: 1==1.0 in Python

    b.reputation = 4  # reputation is a cost for us, so needs to be subtracted
    assert b.total_balance == -13
    b.reputation_factor = 2.5
    assert b.total_balance == -19  # increase the penalty from 4 to 4*2.5 (a difference of 6)

    # locked capital does not incur cost directly.
    # It only incurs a cost in the form of capital_cost
    # by interest_rate * capital_locked.

    b.capital_locked = 100
    assert b.total_balance == -19

    b.capital_cost += 2
    assert b.total_balance == -21

    b.extra_slot_earnings += 26
    assert b.total_balance == +5

    b.extra_slot_costs += 9
    assert b.total_balance == -4

    b.transaction_costs += 3
    assert b.total_balance == -7

    # We could have setters for (some of) the fields that automatically set this
    # if they are touched.
    # We don't want this behaviour, as we actually
    # want to set this flag when a bid is placed.
    assert not b.participated

