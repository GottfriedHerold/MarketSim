from dataclasses import dataclass
from participants import Cluster
from .market import Bid
from .market import Market
from random import Random
from typing import Tuple, Optional, Iterable


@dataclass(kw_only=True, init=True)
class EqualSecondPriceBid(Bid):
    """
    Bid class for the equal second price auction class `EqualSecondPriceMarket`    
    """

    willing_to_pay: int | float = 0
    "how much the participant is willing to pay to be included in the next committee"

    willing_to_receive_bribes: bool = False
    "whether the participant is willing to receive bribes from the market and misbehave in the protocol"

    reputation_value: int | float = 0
    
    @property
    def minimum_gain(self) -> int | float:
        "minimum amount by which the bribes from the miss side have to exceed the reveal side in order to sway towards missing the slot"
        return self.reputation_value

    # from an economic point of view, this should be the same as willing_to_pay. So we force everyone to do just that.
    @property
    def valuation_of_own_slots(self) -> int | float:
        return self.willing_to_pay

    # @dataclass(kw_only=True, init=True) automatically generates this:

    # def __init__(self,
    #             *,
    #             willing_to_pay: int | float = 0,
    #             willing_to_receive_bribes: bool = False,
    #             minimum_gain: int | float = 0,
    #             valuation_of_own_slots: int | float = 0):
    #  self.willing_to_pay = willing_to_pay
    #  self.willing_to_receive_bribes = willing_to_receive_bribes
    #  self.minimum_gain = minimum_gain
    #  self.valuation_of_own_slots = valuation_of_own_slots


class EqualSecondPriceMarket(Market):
    """
    EqualSecondPriceMarket is a market that roughly works as follows:
    - Every participant commits to a maximum they are willing to individually pay.
    - Determine the maximum that both sides are (collectively) willing to pay: each participant either pays zero or the same amount as everyone else who pays.
    - Then the side that pays more "wins" and has to pay the maximum amount y the losing side would be collectively willing to pay.
    - Then on the winning side, each participant either pays zero or the same amount as everyone else who pays.

    Note that there may be multiple ways to achieve a payment of x by the winners (under the constraint that everyone either pays 0 or some amount x/N, where N is the number of payers).
    We choose the (unique) one that maximizes N.
    """

    # Gotti: don't overwrite __init__. You can call it and extend it as follows:

    #  def __init__(self, stake_dist: StakeDistribution, *, epoch_size: Optional[int] = None, initial_bids: Optional[dict[Cluster, Bid | None]] = None, initial_bid_func=None, initial_balances: Optional[dict[Cluster, Balance]] = None, pay_for_initial_bids: Optional[bool] = None):
    #     super().__init__()
    # Market.__init__(...) this will work but it is not the correct way to do it. Better use super

    # super().__init__(stake_dist, epoch_size=epoch_size, initial_bids=initial_bids, initial_bid_func=initial_bid_func, initial_balances=initial_balances, pay_for_initial_bids=pay_for_initial_bids)

    standing_bids: dict[Cluster, EqualSecondPriceBid | None]

    @staticmethod
    def maximum_bid_by_side(maximum_individual_payments: list[int | float]):
        """
        Given a list of maximum payments (typically the list of all payments from either the reveal or miss side of the bidders),
        this function determines the maximum amount that this side is willing to pay *collectively* according the market rules.
        """

        maximum_individual_payments_sorted = sorted(
            maximum_individual_payments, reverse=True)
        # candidate_total_payments[i] is the maximum amount that that can be payed if the first i+1 people are the ones that pay and the rest pay 0.
        candidate_total_payments = [
            maximum_individual_payments_sorted[i] * (i + 1)
            for i in range(len(maximum_individual_payments))
        ]
        return max(candidate_total_payments)

    def _determine_auction_winner(
            self, reveal_side: list[Cluster], miss_side: list[Cluster],
            randomness_source: Random, last_slot_proposer: Cluster
    ) -> Tuple[str, dict[Cluster, int | float]]:
        """
        _dtermine_auction_winner is called by the Market class when it decides which side to win the auction.
        It is supposed to return a tuple of two elements: 
            The first one is either "reveal" or "miss".
            The second one is a dict {cluster -> amount that cluster needs to actually pay}
        """

        last_proposer_bid: Optional[EqualSecondPriceBid] = self.standing_bids[
            last_slot_proposer]

        if last_proposer_bid is None:  # this means the last slots proposer does not participate in the auction at all.
            return 'reveal', {}

        if not last_proposer_bid.willing_to_receive_bribes:  # this means the last proposer is not willing to receive bribes.
            return 'reveal', {}

        # The proposer's choice of reveal vs. miss affects the proposer itself by directly assigning some slots to itself.
        # Note that these do include the slot the lost slot proposer may intentionally miss, hence the own_slots_gained_by_revealing starts at 1.

        payments: dict[Cluster, int | float] = {}
        # After the last slot proposer has decided what to do, we define how much each participant will pay.

        # Add the last proposer's bid to the list of bids to account for the fact that the last proposer gains one more slot in the reveal side
        # due to the fact they don't (intentionally) miss the slot.
        
        reveal_side_bids = [self.standing_bids[c] for c in reveal_side] + [last_proposer_bid]
        miss_side_bids = [self.standing_bids[c] for c in miss_side]

        # Remove duplicates from reveal_side and miss_side.
       
        # Note: The lenghts of these are possibly smaller than the above, because None-bids are filtered out (rather than replaced by 0)
        reveal_side_bid_values = [bid.willing_to_pay for bid in reveal_side_bids if bid is not None]  
        miss_side_bid_values = [bid.willing_to_pay for bid in miss_side_bids if bid is not None]

        maximum_miss_side_collective_bid = self.maximum_bid_by_side(miss_side_bid_values)
        maximum_reveal_side_collective_bid = self.maximum_bid_by_side(reveal_side_bid_values + [last_proposer_bid.valuation_of_own_slots])
        # For now, we assume the last_proposer_bid.valuation_of_own_slots behaves as a bid. Comment above and uncomment below otherwise.
        # maximum_reveal_side_bids = self.maximum_bid_by_side(reveal_side_bid_values) + last_proposer_bid.valuation_of_own_slots

        should_reveal: bool = maximum_reveal_side_collective_bid + last_proposer_bid.minimum_gain > maximum_miss_side_collective_bid

        #TODO: fix: it may be the case there are different ways to achieve the maximun.

        if should_reveal:
            for c in reveal_side:
                if self.standing_bids[c] is not None:
                    payments[c] = self.standing_bids[c].willing_to_pay
                else:
                    payments[c] = 0
            return "reveal", payments
            # This is just the list of who should pay what. Need to be excecuted by the Market
        else:
            for c in miss_side:
                if self.standing_bids[c] is not None:
                    payments[c] = self.standing_bids[c].willing_to_pay
                else:
                    payments[c] = 0
            return "miss", payments
        # TODO: This is just the list of who should pay what. Need to be excecuted by the Market
