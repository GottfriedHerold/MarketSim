from .market import Cluster, Market

class Runner:
    """
    This class actually run our simulation.
    """

    # Arbitrary constant. This is the default value in terms of MEV + issuance that
    # gaining a single proposer slot is worth. For the sake of our market analysis, this is essentially
    # the (ETH-denominated) monetary "unit" we care about. Setting this to 100 means that
    # Balance is measured in centi-proposer-slots.
    # We could (should?) set it to 1, but then we would need to use floats when considering monetary values smaller
    # than this.
    DEFAULT_PROPOSER_SLOT_VALUE = 100

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
              might be higher.
            - MEV per slot may be different if a given cluster gets multiple slots in a row.
        We just currently do not model these subtleties.

        NOTE: The price that a participant might be willing to pay to become a proposer might be different
        from the value returned here. The reason is that the last proposer of a slot has power to influence the
        next epochs' proposers (this is what this market is about).
        This part of a slot's value is NOT the job of this method.
        """
        return [self.DEFAULT_PROPOSER_SLOT_VALUE] * len(proposers)

    def process_epoch(self, market: Market):
        """
        Process one single epoch of the simulation.
        """
        raise NotImplementedError
