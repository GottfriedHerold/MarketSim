from market import Balance, Market, Bid
from participants import StakeDistribution, make_stake_distribution_from_map
from market.market import DummyMarket

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

def _test_market(market: type):

    d = {20: (3, 1), 10: (5, 2), 100: 1}
    stake_dist: StakeDistribution = make_stake_distribution_from_map(d)

    m: Market = market(stake_dist=stake_dist)
    assert m.stake_dist is stake_dist  # by reference, not copy
    assert len(m.standing_bids) == 5+3+1
    assert m.participants == stake_dist.get_clusters()
    assert all(m.standing_bids[c] is None for c in m.participants)

    class Bid2(Bid):
        pass

    m = market(stake_dist=stake_dist, epoch_size=100, initial_bid_func=Bid2)
    assert m.EPOCH_SIZE == 100
    assert all(type(m.standing_bids[c]) is Bid2 for c in m.participants)

    reveal_side, miss_side = m.sample_sides()
    assert len(reveal_side) == 100
    assert len(miss_side) == 100
    assert all(c in m.participants for c in reveal_side)
    assert all(c in m.participants for c in miss_side)

    initial_balances = {c: Balance(payed=5) for c in stake_dist.get_clusters()}

    m = market(stake_dist=stake_dist, initial_balances=initial_balances, pay_for_initial_bids=True)
    assert m.EPOCH_SIZE == 32
    assert all(m.standing_bids[c] is None for c in m.participants)
    assert all(m.balance_sheets[c].payed==5 for c in m.participants)

    some_participant = m.participants[0]
    some_bid = Bid2()
    some_bid.x = 1  # arbitrary attribute
    m.place_bid(some_bid, some_participant)
    assert m.standing_bids[some_participant].x == 1

    assert m.cost_for_bid(None, None) == (0, 0, 0)

def test_market():
    _test_market(DummyMarket)

    d = {20: (3, 1), 10: (5, 2), 100: 1}
    stake_dist: StakeDistribution = make_stake_distribution_from_map(d)
    m = DummyMarket(stake_dist)
    assert all(x is None for x in m.standing_bids.values())
    participants = m.participants
    some_participant = participants[0]
    m.place_bid(Bid(), some_participant)
    assert type(m.standing_bids[some_participant]) is Bid
    assert m.balance_sheets[some_participant].capital_cost == 10
    assert m.balance_sheets[some_participant].reputation == 5
    assert m.balance_sheets[some_participant].transaction_costs == 1
    assert m.balance_sheets[some_participant].participated is True
    m.place_bid(None, some_participant)
    assert m.balance_sheets[some_participant].capital_cost == 0
    assert m.balance_sheets[some_participant].reputation == 1
    assert m.balance_sheets[some_participant].transaction_costs == 2
    assert m.balance_sheets[some_participant].participated is True

