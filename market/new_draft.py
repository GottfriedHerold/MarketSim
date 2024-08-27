from dataclasses import dataclass
from participants import Cluster
from .market import Bid
from .market import Market
from random import Random
from typing import Tuple, Optional


@dataclass(kw_only=True, init=True)
class MyBid(Bid):
    willing_to_pay: int | float = 0
    "how much the participant is willing to pay to be included in the next committee"

    willing_to_receive_bribes: bool = False
    "whether the participant is willing to receive bribes from the market and misbehave in the protocol"

    minimum_gain: int | float = 0
    "minimum amount by which the bribes from the miss side have to exceed the reveal side in order to sway towards missing the slot"

    valuation_of_own_slots: int | float = 0
    "how much the participant values getting slots in the next epoch on its own"

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
    def __init__ (self, standing_bids: dict[Cluster, MyBid|None]):
        self.standing_bids = standing_bids
        
    def reveal_payments(self, reveal_side: list[Cluster]) -> float:
        quant_reveal = [self.standing_bids[c].willing_to_pay for c in reveal_side if self.standing_bids[c] is not None]
        quant_reveal_sorted = sorted(quant_reveal)
        reveal_options = [quant_reveal_sorted[i] * len(quant_reveal_sorted)-i+1 for i in range(len(quant_reveal_sorted))]
        reveal = max(reveal_options[i] for i in range(len(reveal_options)))
        return reveal

    def not_reveal_payments(self, miss_side: list[Cluster]) -> float:
        quant_miss = [self.standing_bids[c].willing_to_pay for c in miss_side if self.standing_bids[c] is not None]
        quant_miss_sorted = sorted(quant_miss)
        miss_options = [quant_miss_sorted[i] * len(quant_miss_sorted)-i+1 for i in range(len(quant_miss_sorted))]
        not_reveal = max(miss_options[i] for i in range(len(miss_options)))
        return not_reveal


    def _determine_auction_winner(
        self, reveal_side: list[Cluster], miss_side: list[Cluster],
        randomness_source: Random,
        last_slot_proposer: Cluster) -> Tuple[str, dict[Cluster, int | float]]:

        last_proposer_bid: Optional[MyBid] = self.standing_bids[last_slot_proposer]

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

        payment_after_reveal: dict[Cluster, int|float] = {}

        if self.reveal_payments(reveal_side) + last_proposer_bid.minimum_gain + own_slots_gained_by_revealing * last_proposer_bid.valuation_of_own_slots  >= self.not_reveal_payments(miss_side) + own_slots_gained_by_missing * last_proposer_bid.valuation_of_own_slots:
            for c in reveal_side:
                if self.standing_bids[c] is not None:
                    payment_after_reveal[c] = self.standing_bids[c].willing_to_pay  
                else:
                    payment_after_reveal[c] = 0
            return "reveal", payment_after_reveal
            # This is just the list of who should pay what. Need to be excecuted by the Market           
        else:
            for c in miss_side:
                if self.standing_bids[c] is not None:
                    payment_after_reveal[c] = self.standing_bids[c].willing_to_pay  
                else:
                    payment_after_reveal[c] = 0
            return "miss", payment_after_reveal
        # TODO: This is just the list of who should pay what. Need to be excecuted by the Market        

        "- how do we capture the fact that the decider may be chosen in one of the two cases?"
