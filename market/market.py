from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import islice
from random import Random
from typing import Optional, Tuple

from participants import Cluster, StakeDistribution


# @dataclass(kw_only=True) allows to initialize a Balance like
# balance = Balance(payed=10, received=20).
# We only allow key-value passing, because passing a list of numbers would just be confusing what they mean.
# and the order is not canonical.
@dataclass(kw_only=True)
class Balance:
    """
    A Balance keeps track of all payments and earnings that an individual market participant has accrued.
    We encapsulate this is in a dataclass to differentiate sources of earnings/payments.

    This is meant to capture all gains/losses of the participants compared to a situation where no
    bribery market existed.

    Note that not all of that data is needed for the simulation. Separating different costs within this balance
    serves mostly to be better able to analyze what is happening.
    """

    # NOTE: Entries without a value (i.e. type hints) in this are **not** just comments, because the @dataclass
    # actually parses this and generates code from it.

    payed: int = 0  # total amount paid to other (as bribes)
    received: int = 0  # total amount received from others (as bribes)
    capital_locked: int = 0  # current amount of capital that needs to be locked down in order to participate
    capital_cost: int = 0  # total accumulated capital cost.
    # capital_cost should increment by a certain fraction, representing an interest rate,
    # of the current value of capital_locked each time step.
    transaction_costs: int = 0  # total accumulated transaction costs.
    extra_slot_earnings: int = 0  # total extra earnings that the participant has gained from participating (or not)
    # in the market by gaining extra slots. Note that this does not include bribe payments.
    extra_slot_costs: int = 0  # total losses that the participant has incurred from other
    # participants "stealing" the slot.
    reputation: int = 0  # reputation value that the participant has from participating in the market
    reputation_factor: float | int = 1  # how much this participant values reputation. This is essentially
    # copied from the participant's data itself. We keep this copy around to simplify things.
    # (it also would allow making this dynamic)
    participated: bool = False  # did the participant ever enter the market?

    # NOTE: Any cut taken by the market maker is accounted for by transaction_costs

    # The following
    #   total_balance
    #   reputation_cost
    # are defined via properties below. We don't include these here with type-hints and comments,
    # because @dataclass analyzes the type-hints, which would complicate things.

    @property
    def total_balance(self) -> int | float:
        """
        returns the total amount that the participant has earned from the market.
        This is positive for gains, negative for losses.
        Note that even a participant that has never engaged with the market may have a non-zero value here:
        This happens if that participant has one of its slots stolen due the market.
        Also, it may happen that a participant gains a slot (randomly, essentially) by
        being in the winning A_miss - side of the bet, even if that participated never actually actively engaged.
        """
        return (self.received - self.payed - self.capital_cost - self.transaction_costs
                + self.extra_slot_earnings - self.extra_slot_costs - self.reputation_cost)

    @property
    def reputation_cost(self):
        return self.reputation * self.reputation_factor


class Bid:
    """
    class that represents a single standing bid by a market participant.
    This purely abstract class is supposed to be derived from with an implementation that is
    specific to the market mechanism.
    As such, this class solely acts to unify type annotations.

    Note that we shall assume that a given market participant can only ever have 1 standing bid to simplify the API.
    As such, a bid needs to be able to express both "I want to be bribed" and "I want to bribe" simultaneously.
    """
    pass


class Market(ABC):
    """
    The Market class is a base class, describing the API for a market mechanism.
    """
    # state: Any  # internal state of the market.

    # NOTE: participants includes clusters that have never placed a bid.
    # The reason is that those participants are affected by the market nonetheless.

    _participants: list[Cluster]  # list of participants in the market.
    # This is determined by stake_dist
    # access this via the participants @property

    balance_sheets: dict[Cluster, Balance]  # balance sheet of every participant.
    standing_bids: dict[Cluster, Bid | None]  # current bid by the given participant.
    # standing_bids[c] == None means that c never placed a bid.
    stake_dist: StakeDistribution  # Stake distribution object.
    # This is used to sample the two sides of the bidding market.

    EPOCH_SIZE: int = 32  # number of validators per bidding side that bid against each other per epoch.

    def make_payment(self, sender: Cluster, receiver: Cluster, amount: int):
        """
        Pays amount from sender to receiver.
        Both sender and receiver must be among the market participants.
        """
        assert sender in self.balance_sheets
        assert receiver in self.balance_sheets
        assert amount >= 0

        # We only allow payments between participants that have the participated flag set.
        # This is just a sanity check for correct usage.
        assert self.balance_sheets[sender].participated
        assert self.balance_sheets[receiver].participated

        self.balance_sheets[sender].payed += amount
        self.balance_sheets[receiver].received += amount

    def place_bid(self, bid: Bid, cluster: Cluster):
        """
        Call place_to_bid to have the given cluster place a bid.
        This replaces any previous bid that the cluster had active.

        Calling this automatically updates the balance sheet of the cluster using
        cost_for_bid unless bid is None.

        Note: derived classes may overwrite this method.
        """

        # This place_bid method just implements some common logic that a derived class may call via super()

        assert cluster in self.participants
        old_bid = self.standing_bids[cluster]
        self.standing_bids[cluster] = bid

        # flag the participant as having placed a bid.
        if bid is not None:
            self.balance_sheets[cluster].participated = True

        # process cost of placing bid
        transaction_cost, capital_cost, new_reputation = self.cost_for_bid(old_bid=old_bid, new_bid=bid)
        self.balance_sheets[cluster].transaction_costs += transaction_cost
        self.balance_sheets[cluster].capital_cost = capital_cost
        self.balance_sheets[cluster].reputation = new_reputation

    def __init__(self, stake_dist: StakeDistribution, *, epoch_size: Optional[int] = None,
                 initial_bids: dict[Cluster, Bid] = None,
                 initial_bid_func=None,
                 initial_balances: Optional[dict[Cluster, Balance]] = None,
                 pay_for_initial_bids: Optional[bool] = None):
        """
        Initialize an instance of market with the given StakeDistribution stake_dist.
        If initial_balances is not None, it is used to initialize the balances (by copy);
        otherwise the balances are initialized to a default of 0.

        The initial bids are initialized to None unless either
        initial_bid_func or initial_balances are set (only one is allowed):
            if initial_bids is not None, those are used to initialize the bids (by copy).
            if initial_bid_func is not None, we initialize the bids as initial_bid_func().
        The intended use case for the latter is using a type derived from Bid as a constructor.

        If pay_for_initial_bids is set, we place the initial bids via place_bid. This
        will modify the balances. If pay_for_initial_bids is not set, we directly overwrite the bids without
        modifying the balances.
        pay_for_initial_bids is True by default unless a non-None value if provided for initial_balances.
        In this case, we require the caller to set pay_for_initial_bids explicitly.

        (NOTE: if we initialize with a bid of None, place_bid is required to be a no-op.
        If initial_balances are requested, this can lead to unexpected results: e.g. initial_balances might
        set some value for reputation / capital_locked for a cluster c. If the bid for this cluster is None,
        the value for reputation and capital_locked are not zeroed. This should be avoided by the caller.)

        epoch_size overrides the default epoch_size.
        """

        if initial_bids is not None and initial_bid_func is not None:
            raise ValueError("both initial_bids and initial_bid_func was provided")

        if initial_balances is not None and pay_for_initial_bids is None:
            raise ValueError("A value for initial_balances was provided. "
                             "In this case, pay_for_initial_bids must be set explicitly")
        if pay_for_initial_bids is None:
            pay_for_initial_bids = True

        if epoch_size is not None:
            self.EPOCH_SIZE = epoch_size
        self.stake_dist = stake_dist
        self._participants = stake_dist.get_clusters()  # Use a property-setter to inform derived classes?

        # Initialize balance_sheets. We need to set self.balance_sheets[c] for every c
        # because calls to self.place_bide below would fail otherwise.
        if initial_balances is None:
            self.balance_sheets = {c: Balance() for c in self._participants}
        else:
            self.balance_sheets = initial_balances.copy()

        # self.standing_bids needs to be set before we potentially call self.place_bid.
        # The reason is that self.place_bid may look at the previously active bid
        # to compute transaction costs.
        # self.standing_bids[c] == None means that c has no active bid.
        self.standing_bids = {c: None for c in self._participants}

        # NOTE: self.place_bid(bid, c) is required to be a no-op if bid is None
        if initial_bid_func is not None:
            if pay_for_initial_bids:
                for c in self.participants:
                    self.place_bid(initial_bid_func(), c)
            else:
                self.standing_bids = {c: initial_bid_func() for c in self._participants}

        if initial_bids is not None:
            if pay_for_initial_bids:
                for c in self.participants:
                    self.place_bid(initial_bids[c], c)
            else:
                self.standing_bids = initial_bids.copy()

    @property
    def participants(self):
        return self._participants

    @abstractmethod
    def cost_for_bid(self, old_bid: Bid | None, new_bid: Bid | None) -> Tuple[int, int, int]:
        """
        This is called whenever a cluster places a new bid to replace the old one.
        It returns the cost for the cluster placing a bid as a 3-tuple
        (transaction_cost, capital_cost, new_reputation)
        If old_bid is None and new_bid is None, this function must return 0, 0, 0.
        (We do not guarantee to even call this).
        If old_bid is None, we have no previous bid.
        if new_bid is None, this means "withdraw" from the market (so returned capital_cost should be 0)
        For the returned values:
          - transaction_cost is the cost the cluster has to pay to actually place the bid.
          - capital_cost is the total amount of capital that the cluster needs to have locked down after having
            placed the bid.
          - new_reputation is the reputation value that the cluster has after placing the bid.

        Note that transaction_cost needs to be *added* to the previous value in balance of the cluster.
        By contrast, capital_cost and new_reputation *overwrite* the previous value.

        This function must be overwritten by a derived class.
        """
        if old_bid is None and new_bid is None:
            return 0, 0, 0
        ...

    @abstractmethod
    def get_best_bid(self, cluster: Cluster, randomness_source: Random) -> Bid:
        """
        Returns the best (or close-to-best) bid (in terms of *expected* net gains) for the provided
        cluster assuming that all other clusters do not change their standing bids.
        """
        ...

    def sample_sides(self, randomness_source: Optional[Random] = None) -> Tuple[list[Cluster], list[Cluster]]:
        """
        Samples the two sides of the bidding market in order (reveal, miss).
        random_source is used to select the randomness source for the sampling;
        by default, we use the randomness source from stake_dist itself via stake_dist.sample_cluster.
        """
        if randomness_source is None:
            reveal_side = list(islice(self.stake_dist.iterator, self.EPOCH_SIZE))
            miss_side = list(islice(self.stake_dist.iterator, self.EPOCH_SIZE))
        else:
            reveal_side = [self.stake_dist.sample_cluster(randomness_source=randomness_source)
                           for _ in range(self.EPOCH_SIZE)]
            miss_side = [self.stake_dist.sample_cluster(randomness_source=randomness_source)
                         for _ in range(self.EPOCH_SIZE)]
        return reveal_side, miss_side

    def get_auction_winner(self, *, reveal_side: list[Cluster] = None, miss_side: list[Cluster],
                           randomness_source: Optional[Random] = None) -> Tuple[str, dict[Cluster, int | float]]:
        """
        Determines the winner of the bidding auction according to the bribery market's rules.
        The bidding is between the reveal_side and the miss_side.
        If both sides are set to None, we sample them freshly.
        randomness_source is taken as a source of randomness, if needed. A value of None selects
        a default.

        The first returned value is either "miss" or "reveal"
        The second returned value is a dict Cluster -> amount that needs to be paid to the last-slot-proposer.
        """

        # This method just does some common argument pre-processing and hands off to _determine_auction_winner.

        # Take a default randomness source if None was provided.
        # Note that we don't overwrite randomness_source itself, but rather create a new variable.
        # The reason for that is that None has a special meaning for self.sample_sides
        # (notably take stake_dist.sample_cluster), which is subtly different from using Random(),
        # so we need to preserve that.
        real_randomness_source: Random
        if randomness_source is None:
            real_randomness_source = Random()
        else:
            real_randomness_source = randomness_source

        if reveal_side is None and miss_side is None:
            # Note: We use randomness_source, not real_randomness_source here.
            reveal_side, miss_side = self.sample_sides(randomness_source=randomness_source)
        # handle the cases where only one of reveal_side and miss_side was None.
        if reveal_side is None:
            raise ValueError("reveal_side was None, but miss_side was not. We do not support this at the moment")
        if miss_side is None:
            raise ValueError("miss_side was None, but reveal_side was not. We do not support this at the moment")

        # sanity check. Maybe delete this, if it is too slow?
        assert all(c in self.participants for c in reveal_side)
        assert all(c in self.participants for c in miss_side)
        return self._determine_auction_winner(reveal_side, miss_side, real_randomness_source)

    @abstractmethod
    def _determine_auction_winner(self, reveal_side: list[Cluster], miss_side: list[Cluster],
                                  randomness_source: Random) -> Tuple[str, dict[Cluster, int | float]]:
        """
        actual implementation of get_auction_winner.
        This needs to be overridden in a base class.

        Returns either the string literal "miss" or "reveal" as the first returned value
        The second returned value is a dict of payments {cluster -> amount paid}
        for the amounts that are paid to the last slot proposer.

        NOTE: randomness_source may be assumed to be not None.
        """

    def get_balance_sheet(self, cluster: Cluster) -> Balance:
        """
        returns the balance sheet of the given cluster.
        """
        return self.balance_sheets[cluster]


class DummyMarket(Market):
    """
    Dummy implementation of Market that just serves testing purposes.
    For this, bids are actually "empty" messages without any semantics.
    This means we can use the (empty) Bid class directly without deriving from it.
    """

    def cost_for_bid(self, old_bid: Bid | None, new_bid: Bid | None) -> Tuple[int, int, int]:
        """
        Placing a bid does nothing, but costs the bidder 1 unit of transaction cost
        and puts the capital cost at 10 and the reputation loss at 5.
        Withdrawing costs 1 and leaves the reputation loss at 1.
        """
        if old_bid is None and new_bid is None:
            return 0, 0, 0
        if new_bid is None:
            return 1, 0, 1
        return 1, 10, 5

    def get_best_bid(self, cluster: Cluster, *, randomness_source: Random) -> Bid:
        return Bid()

    def _determine_auction_winner(self, reveal_side: list[Cluster], miss_side: list[Cluster],
                                  randomness_source: Random) -> Tuple[str, dict[Cluster, int | float]]:
        # Just answer at random
        return randomness_source.choice(("miss", "reveal")), {}
