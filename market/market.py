from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import islice
from random import Random
from typing import Any, Optional, Tuple

from participants import Cluster, StakeDistribution


@dataclass(kw_only=True)
class Balance:
    """
    A Balance keeps track of all payments and earnings that an individual market participant has accrued.
    We encapsulate this is in a dataclass to differentiate sources of earnings/payments.

    Note that not all of that data is needed for the simulation. Separating different costs within this balance
    serves mostly to be able to analyze what is happening better.
    """

    # NOTE: The list here is **not** just a comment, because the @dataclass
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

    # The following
    #   total_balance
    #   reputation_cost
    # are defined via properties below. We don't include these here with type-hints and comments,
    # because @dataclass analyzes the type-hints, which would complicate things.

    @property
    def total_balance(self) -> int | float:
        """
        returns the total amount that the participant has earned from the market.
        This is positive for gains, negative from losses.
        Note that even a participant that has never engaged with the market may have a non-zero (negative) value here:
        This happens if that participant has one of its slots stolen due the market.
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

    # maybe get rid of that? It's available as balance_sheet.keys() or list(balance_sheet.keys()) anyway.
    participants: list[Cluster]  # list of participants in the market.

    balance_sheets: dict[Cluster, Balance]  # balance sheet of every participant.
    standing_bids: dict[Cluster, Bid]  # current bid by the given participant
    stake_dist: StakeDistribution  # Stake distribution object.
    # This is used to sample the two sides of the bidding market.
    EPOCH_SIZE: int = 32  # number of validators that bid against each other per epoch. This is a class variable.

    @abstractmethod
    def place_bid(self, bid: Bid, cluster: Cluster) -> Tuple[int, int, int]:
        """
        call to have the given cluster place a bid.
        Returns the tuple (transaction_cost, capital_cost, new_reputation).
        Here,
          - transaction_cost is the cost the cluster has to pay to actually place the bid.
          - capital_cost is the total amount of capital that the cluster needs to have locked down after having
            placed the bid.
          - new_reputation is the reputation value that the cluster has after placing the bid.

        Note that transaction_cost needs to be *added* to the previous value in balance of the cluster.
        By contrast, capital_cost and new_reputation *overwrite* the previous value.
        """
        ...

    @abstractmethod
    def get_best_bid(self, cluster: Cluster) -> Bid:
        """
        Returns the best (or close-to-best) bid (in terms of *expected* net gains) for the provided
        cluster assuming that all other clusters do not change their standing bids.
        """
        ...

    def sample_sides(self, randomness_source: Optional[Random] = None) -> Tuple[list[Cluster], list[Cluster]]:
        """
        Samples the two sides of the bidding market in order (reveal, miss).
        random_source is used to select the randomness source for the sampling;
        by default, we use the one stored in stake_dist itself.
        """
        if randomness_source is None:
            sampler = self.stake_dist.sample_cluster
        else:
            sampler = self.stake_dist.new_cluster_sampler(randomness_source=randomness_source)
        reveal_side = list(islice(sampler, self.EPOCH_SIZE))
        miss_side = list(islice(sampler, self.EPOCH_SIZE))
        return reveal_side, miss_side

    def get_balance_sheet(self, cluster: Cluster) -> Balance:
        """
        returns the balance sheet of the given cluster.
        """
        return self.balance_sheets[cluster]
