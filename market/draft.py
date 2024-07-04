from dataclasses import dataclass
from participants import Cluster
from .market import Bid
from .market import Market
from random import Random
from typing import Tuple


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
  standing_bids: dict[Cluster, MyBid]

  def reveal_payments(self, reveal_side: list[Cluster]) -> float:
    reveal = sum(self.standing_bids[c].willing_to_pay for c in reveal_side)
    return reveal

  
  def not_reveal_payments(self, miss_side: list[Cluster]) -> float:
    not_reveal = sum(self.standing_bids[c].willing_to_pay for c in miss_side)
    return not_reveal

  
  def _determine_auction_winner(
      self, reveal_side: list[Cluster], miss_side: list[Cluster],
      randomness_source: Random,
      last_slot_proposer: Cluster) -> Tuple[str, dict[Cluster, int | float]]:

    
    own_slots_gained_by_revealing = 0
    for c in reveal_side:
      if c == last_slot_proposer:
        own_slots_gained_by_revealing += 1

    
    own_slots_gained_by_missing = 0
    for c in miss_side:
      if c == last_slot_proposer:
        own_slots_gained_by_missing += 1

    
    if self.reveal_payments(reveal_side) + self.standing_bids[
        last_slot_proposer].minimum_gain > self.not_reveal_payments(miss_side):
      return "reveal", {}
      # TODO: actual Payments of bribes
    else:
      return "miss slot", {}
      # TODO: actual Payments of bribes


"- how do we capture the fact that the decider may be chosen in one of the two cases?"
