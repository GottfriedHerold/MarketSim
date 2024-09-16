from dataclasses import dataclass
from participants import Cluster
from .market import Bid
from .market import Market
from random import Random
from typing import Tuple, Optional, Iterable


#  TODO: Rename classes
@dataclass(kw_only=True, init=True)
class MyBid(Bid):
    # TODO: Docstring
    willing_to_pay: int | float = 0
    "how much the participant is willing to pay to be included in the next committee"

    willing_to_receive_bribes: bool = False
    "whether the participant is willing to receive bribes from the market and misbehave in the protocol"

    minimum_gain: int | float = 0
    "minimum amount by which the bribes from the miss side have to exceed the reveal side in order to sway towards missing the slot"

    valuation_of_own_slots: int | float = 0
    "how much the last-slot proposer values getting slots in the next epoch on its own"

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





class MyMarket(Market):
    
    # Gotti: don't overwrite __init__. You can call it and extend it as follows:

  #  def __init__(self, stake_dist: StakeDistribution, *, epoch_size: Optional[int] = None, initial_bids: Optional[dict[Cluster, Bid | None]] = None, initial_bid_func=None, initial_balances: Optional[dict[Cluster, Balance]] = None, pay_for_initial_bids: Optional[bool] = None):
   #     super().__init__()
        # Market.__init__(...) this will work but it is not the correct way to do it. Better use super
        
    # super().__init__(stake_dist, epoch_size=epoch_size, initial_bids=initial_bids, initial_bid_func=initial_bid_func, initial_balances=initial_balances, pay_for_initial_bids=pay_for_initial_bids)
    
    standing_bids: dict[Cluster, MyBid | None]

    """"
    # Gotti: TODO: Replace by single function? Add docstring
    def reveal_payments(self, reveal_side: list[Cluster]) -> float:
        # quant_reveal is the list of potential payments by the reveal_side bidders
        quant_reveal = [
            self.standing_bids[c].willing_to_pay for c in reveal_side
            if self.standing_bids[c] is not None
        ]
        
        quant_reveal_sorted = sorted(quant_reveal) # sort ascendingly
        
        # reveal_options[i] is the total amount that the reveal side would pay if the i+1 members with the highest willingness to pay are the ones who pay.
        reveal_options = [
            quant_reveal_sorted[i] * len(quant_reveal_sorted) - i + 1
            for i in range(len(quant_reveal_sorted))
        ]
        # reveal is the acutal amount that will compete against not reveal.
        reveal = max(reveal_options) # [i] for i in range(len(reveal_options))) -> not needed
        return reveal

    def not_reveal_payments(self, miss_side: list[Cluster]) -> float:
        quant_miss = [
            self.standing_bids[c].willing_to_pay for c in miss_side
            if self.standing_bids[c] is not None
        ]
        quant_miss_sorted = sorted(quant_miss)
        miss_options = [
            quant_miss_sorted[i] * len(quant_miss_sorted) - i + 1
            for i in range(len(quant_miss_sorted))
        ]
        not_reveal = max(miss_options) #[i] for i in range(len(miss_options)))
        return not_reveal
    """

    @staticmethod
    def maximum_bid_by_side(maximum_individual_payments: Iterable[int | float]):
        """
        Given a list of maximum payments (typically the list of all payments from either the reveal or miss side of the bidders),
        this function determines the maximum amount that this side is willing to pay *collectively* according the market rules.
        """
        
        maximum_individual_payments_sorted = sorted(maximum_individual_payments)
        candidate_total_payments = [
            maximum_individual_payments[i] * len(maximum_individual_payments) - i + 1
            for i in range(len(maximum_individual_payments))
        ]
        return max(candidate_total_payments) #[i] for i in range(len(miss_options)))
        

    def _determine_auction_winner(
            self, reveal_side: list[Cluster], miss_side: list[Cluster],
            randomness_source: Random, last_slot_proposer: Cluster
    ) -> Tuple[str, dict[Cluster, int | float]]:

        last_proposer_bid: Optional[MyBid] = self.standing_bids[
            last_slot_proposer]

        if last_proposer_bid is None:
            return 'reveal', {}

        if not last_proposer_bid.willing_to_receive_bribes:
            return 'reveal', {}

        own_slots_gained_by_revealing = 0
        for c in reveal_side:
            if c == last_slot_proposer:
                own_slots_gained_by_revealing += 1

        own_slots_gained_by_missing = 0
        for c in miss_side:
            if c == last_slot_proposer:
                own_slots_gained_by_missing += 1

        payment_after_reveal: dict[Cluster, int | float] = {}

        if self.reveal_payments(
                reveal_side
        ) + last_proposer_bid.minimum_gain + own_slots_gained_by_revealing * last_proposer_bid.valuation_of_own_slots >= self.not_reveal_payments(
                miss_side
        ) + own_slots_gained_by_missing * last_proposer_bid.valuation_of_own_slots:
            for c in reveal_side:
                if self.standing_bids[c] is not None:
                    payment_after_reveal[c] = self.standing_bids[
                        c].willing_to_pay
                else:
                    payment_after_reveal[c] = 0
            return "reveal", payment_after_reveal
            # This is just the list of who should pay what. Need to be excecuted by the Market
        else:
            for c in miss_side:
                if self.standing_bids[c] is not None:
                    payment_after_reveal[c] = self.standing_bids[
                        c].willing_to_pay
                else:
                    payment_after_reveal[c] = 0
            return "miss", payment_after_reveal
        # TODO: This is just the list of who should pay what. Need to be excecuted by the Market
        "- how do we capture the fact that the decider may be chosen in one of the two cases?"
