from dataclasses import dataclass
from participants import Cluster
from .market import Bid
from .market import Market
from random import Random
from typing import Tuple, Optional
from .draft import MyMarket
from .draft import MyBid



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
    percentage : dict [Cluster, int | float]= {}

    for c in reveal_side:
        if self.standing_bids[c] is not None:
            percentage[c] = self.standing_bids[c].willing_to_pay * 100 /                 (self.reveal_payments(reveal_side) + last_proposer_bid.minimum_gain + own_slots_gained_by_revealing * last_proposer_bid.valuation_of_own_slots)

    for c in miss_side:
        if self.standing_bids[c] is not None
            percentage[c] = self.standing_bids[c].willing_to_pay * 100 /                    (self.not_reveal_payments(miss_side) + own_slots_gained_by_missing * last_proposer_bid.valuation_of_own_slots)
    
    if self.reveal_payments(reveal_side) + last_proposer_bid.minimum_gain + own_slots_gained_by_revealing * last_proposer_bid.valuation_of_own_slots  >= self.not_reveal_payments(miss_side) + own_slots_gained_by_missing * last_proposer_bid.valuation_of_own_slots:
        for c in reveal_side:
            if self.standing_bids[c] is not None:
                payment_after_reveal[c] = self.percentage[c] *  (self.not_reveal_payments(miss_side) + own_slots_gained_by_missing * last_proposer_bid.valuation_of_own_slots + 1)
            else:
                payment_after_reveal[c] = 0
        return "reveal", payment_after_reveal
        # This is just the list of who should pay what. Need to be excecuted by the Market           
    else:
        for c in reveal_side:
            if self.standing_bids[c] is not None:
                payment_after_reveal[c] = self.percentage[c] * (self.reveal_payments(reveal_side) + last_proposer_bid.minimum_gain + own_slots_gained_by_revealing * last_proposer_bid.valuation_of_own_slots + 1)
            else:
                payment_after_reveal[c] = 0
        return "miss", payment_after_reveal
    # TODO: This is just the list of who should pay what. Need to be excecuted by the Market   


