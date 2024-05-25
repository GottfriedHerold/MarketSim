from typing import Optional, Dict
from random import Random

from .market import Cluster, Market, Bid


# Arbitrary constant. This is the default value in terms of MEV + issuance that
# gaining a single proposer slot is worth. For the sake of our market analysis, this is essentially
# the (ETH-denominated) monetary "unit" we care about. Setting this to 100 means that
# Balance is measured in centi-proposer-slots.
# We could (should?) set it to 1, but then we would need to use floats when considering monetary values smaller
# than this.
DEFAULT_PROPOSER_SLOT_VALUE = 100

class Runner:
    """
    This class actually run our simulation.
    """

    # Having an amount x of capital locked incurs a cost
    # (essentially an opportunity cost from not being able to freely engage in DeFi)
    # of x * locked_capital_cost_per_epoch
    #
    # This value needs to be set to some reasonable value such as the expected return from staking.
    #
    # NOTE: In principle, there are tricks to design a bribery market in a way that
    # allows locked capital to engage in DeFi, although in a limited way.
    # cf. the notes on Settlement from https://notes.ethereum.org/Q8QrXyUOT9Kk0MLtUcesgQ
    # NOTE2: capital locked is denominated in ETH, so the holder may still get value from
    # just holding it. Typically, this is a significant part of the reason why stakers stake in the first place.
    #
    # For that reason, the ETH-denominated expected revenue from staking (over simply holding) ETH is reasonable
    locked_capital_cost_per_epoch: float
    market: Market
    randomness_source: Random  # defaults to Random()
    last_slot_proposer: Cluster

    def __init__(self, market: Market, *, locked_capital_cost_per_epoch: float,
                 randomness_source: Random = None, initial_last_slot_proposer: Optional[Cluster] = None):
        """
        initialize an instance of Runner, which holds the state of our simulation (including a market state).
        Note that the separation of the Runner's state and the Market's state is somewhat fuzzy and not really
        a "programming" question -- from a coding perspective, there is no reason to separate those.
        It is rather a modelling one:
        The Market class models what a market maker is able to choose and how the actual auctions work,
        the Runner class models the (assumptions about the) dynamics of the participants' behaviour
        and the general economy.

        the parameters have the following meaning:
        market is mandatory and should have a type (derived from) Market.
        locked_capital_cost_per_epoch is used to set the per-epoch interest rate on capital cost.
        (TODO: Using None should take a default value)
        initial_last_slot_proposer is the initial last-slot proposer. If set to None, it is sampled randomly.
        randomness_source is the source of randomness used in the simulation. None selects a default.
        Note that when derandomizing everything, a randomness source must be provided to each of
        the Runner class, the Market class and the Stake Distribution class separately.
        We do not forward the randomness source from Runner to Market. This is not ideal, but simplifies the API.
        Note that we do not deep-copy the randomness source, so one may use the same (stateful) randomness source for
        each of these. This then behaves as a single randomness source for the whole simulation.
        """

        self.market = market

        # Will cause an error if we don't set a default value for locked_capital_cost_per_epoch
        if hasattr(type(self), "locked_capital_cost_per_epoch"):
            if locked_capital_cost_per_epoch is None:
                raise ValueError("Must set locked_capital_cost_per_epoch")

        if locked_capital_cost_per_epoch is not None:
            self.locked_capital_cost_per_epoch = locked_capital_cost_per_epoch  #

        # randomness source:
        if randomness_source is None:
            self.randomness_source = Random()
        else:
            self.randomness_source = randomness_source

        # if no initial_last_slot_proposer is given, choose one randomly
        if initial_last_slot_proposer is None:
            self.last_slot_proposer = next(market.stake_dist.new_cluster_sampler(self.randomness_source))
        else:
            self.last_slot_proposer = initial_last_slot_proposer

        assert initial_last_slot_proposer in self.market.participants






    def get_proposer_slot_gains(self, proposers: list[Cluster]) -> list[int]:
        """
        This method determines the (direct) values that the winning a proposer slots have for a given cluster via
        both MEV and issuance.
        The proposers argument is a list of proposers for the epoch.
        The returned list is a list (of the same length) for those.

        Note: In a simple model, the returned list is just a constant list
        [DEFAULT_PROPOSER_SLOT_VALUE, DEFAULT_PROPOSER_SLOT_VALUE, ...]
        that does not depend on the proposers at all.
        This is in fact the default implementation that we give here.

        The reason that we pass the list of proposers here is that in principle:
            - MEV may depend on the slot within the epoch. Notably, the amount of MEV at the beginning of an epoch
              might be higher (due to a preceding missed slot -- we might need that information).
            - MEV per slot may be different if a given cluster controls multiple slots in a row.
        We just currently do not model these subtleties.

        NOTE: The price that a participant might be willing to pay to become a proposer might be different
        from the value returned here. The reason is that the last proposer of a slot has power to influence the
        next epochs' proposers (this is what this market is about).
        This part of a slot's value is NOT the job of this method.
        """
        return [DEFAULT_PROPOSER_SLOT_VALUE] * len(proposers)

    def process_epoch(self, market: Market):
        """
        Process one single epoch of the simulation.
        """
        raise NotImplementedError


