from typing import Tuple, Optional, Iterator
from abc import ABC, abstractmethod
from random import Random
from itertools import accumulate

"""
This file defines the Cluster class, which is used to represent a cluster of validators.
In the context our our bribery market, these clusters are the market participants.
(excluding the market maker, who could be a "special" participant)
"""


class Cluster:
    """
    A cluster of validators.
    An object of this type models a single market participant.
    Note that we only model the "static" data for one participant in this class.
    Dynamic data like "how much did this cluster benefit from the bribery market"
    are modelled by a dict:Cluster -> Balance, where Balance collects all the data that we
    care about. We could in principle make the Balance a part of the Cluster type,
    but this way feels a bit cleaner.

    The only relevant such static data that our participants have are
        - the number of validators this cluster comprises
        - how much this cluster economically values its reputation.

    Note: For reputation, we assume that participating in a bribery market brings a reputation loss.
    The cluster c then values this economically as c.reputation_factor * amount_of_reputation_loss,
    where c.reputation_factor may or may not actually depend on c. By default, the reputation_factor is 1.

    Note that we do not actually need to model individual validators:
    we only care about how what clusters there are and how many validators each cluster has.
    """

    number_of_validators: int  # number of validators this cluster contains
    reputation_factor: int = 1  # how much this cluster values reputation. May be overridden on a per-object basis.

    @property
    def stake_fraction(self) -> float:
        """
        how much a fraction of the total stake this cluster represents.
        Implementing this requires setting a total number of a validators.
        """
        raise NotImplementedError

    def __init__(self, number_of_validators: int = 1, *, reputation_factor: int | None = None):
        self.number_of_validators = number_of_validators

        # For the passed reputation_factor, we default to None rather than 1.
        # If the user passes None, we just let self.reputation_factor unset,
        # which causes access to self.reputation_factor to look up the class variable,
        # which is set as one. This is slightly better, since it allows to change the
        # default by changing the class variable in Cluster or a derived class directly
        # without changing the method's API.
        if reputation_factor is not None:
            self.reputation_factor = reputation_factor

    def __lt__(self, other):
        """
        comparison operator < between clusters.
        This is solely provided to allow sorting, which helps write test and example code.
        """
        other: Cluster
        if self.number_of_validators == other.number_of_validators:
            return self.reputation_factor < other.reputation_factor
        else:
            return self.number_of_validators < other.number_of_validators


class StakeDistribution(ABC):
    """
    Abstract base class that defines the API for a stake distribution.
    A stake distribution essentially is just a list[Clusters] that participate in a given
    bribery market.
    However, we add some extra functionality here by allowing to sample from this list
    weighted by the stake distribution.This is useful for our simulation because we need to
    sample proposers according to this distribution. Also, a concrete instantiation of StakeDistribution
    should have a randomness source embedded into it, so we can make everything deterministic if desired.
    (This is useful for reproducibility, which aids debugging)
    Embedding a randomness source in the StakeDistribution is just a nicer API than passing randomness to every call to
    sample.

    NOTE: When sampling a proposer, we return a cluster rather than a validator, because we only
    care about which cluster the proposer belongs to -- we don't (need to) model validators at all.
    """

    @abstractmethod
    def get_clusters(self) -> list[Cluster]:
        """
        Returns the list of all clusters that comprise this StakeDistribution.
        This is sorted first by number_of_validators, then by reputation_factor

        This may return the actual list of clusters rather than a copy.
        The caller should not modify the returned list and treat it as read-only.
        The reason is that StakeDistribution would need to be made aware of any modifications
        (e.g. to update some internal precomputations) and we provide no API for that for simplicity.
        """
        ...

    @abstractmethod
    def new_cluster_sampler(self, randomness_source: Optional[Random] = None) -> Iterator[Cluster]:
        """
        Generator that yields a cluster at random, weighted by stake.
        Note that this is a generator expression, i.e. uses yield.
        new_cluster_sampler allows to create a new sample that embeds a randomness source.
        If a user just wants to use the "default", randomness source, they
        may want to use sample_cluster instead.
        """
        ...

    _sample_cluster: Iterator[Cluster]  # Default sampler

    @property
    def sample_cluster(self) -> Iterator[Cluster]:
        """
        An iterator that that samples a cluster according to the stake distribution.
        Note that this samples with replacement, so for any StakeDistribution sd, a loop such as
    
        for cluster in sd.sample_cluster:
            ...
        
        is an infinite loop.
        """
        if hasattr(self, "_sample_cluster"):
            return self._sample_cluster
        else:
            self._sample_cluster = self.new_cluster_sampler(randomness_source=None)
            return self._sample_cluster


def make_stake_distribution_from_map(stake_map: dict[int, int | Tuple[int, int]],
                                     *,
                                     randomness_source: Optional[Random] = None,
                                     reputation_factor: int = 1) -> StakeDistribution:
    """
    Creates a stake distribution from a map {cluster_size -> how many clusters of this size exist}
    If an entry stake_map[i] is a pair such a stake_map[10] == (5,2),
    this is interpreted as 5 clusters of size 10, with each having a  reputation factor of 2.

    randomness_source is used as the default randomness source to sample from the set of clusters
    when using sample_cluster

    Example:
        stake_distribution = MakeStakeDistributionFromMap({10: (5,2), 20: (3,1), 100: 1})

        # returns a list of 5+3+1 clusters of sizes 10,10,10,10,10,20,20,20,100.
        # The size-10 cluster each have reputation_factor 2, the other have reputation_factor 1.
        clusters = stake_distribution.get_clusters()

        # samples from the cluster:
        for c in stake_distribution.sample_cluster:
            ... # infinite loop
    """

    # We implement make_stake_distribution_from_map by creating a new class NewStakeDistribution derived from
    # StakeDistribution and retuning an instance of it.

    # The class NewStakeDistribution will not hold (and have get_clusters() return) a list[Cluster],
    # but instead a list[ClusterWithTotalStake], where ClusterWithTotalStake is a new class derived from Cluster.
    # This ClusterWithTotalStake class "knows" which StakeDistribution the cluster belongs to
    # by storing the total amount of stake present. This is just so that we can implement stake_fraction on
    # ClusterWithTotalStake.

    # NOTE: Calling make_stake_distribution_from_map multiple times will each return a new object of a new type.
    # In particular, if we call it twice as
    #
    # >>> sd1 = make_stake_distribution_from_map(...)
    # >>> sd2 = make_stake_distribution_from_map(...)
    # >>> type(sd1) == type(sd2)
    # False
    #
    # sd1 and sd2 wil have a different type: Both type(sd1) are type(sd2) are freshly generated types, because
    # each call creates a fresh NewStakeDistribution type. Dito for ClusterWithTotalStake.
    class ClusterWithTotalStake(Cluster):
        """
        This is a new type derived from Cluster that knows the total amount of stake
        of the StakeDistribution that this cluster is part of.
        """
        total_number_of_validators: int  # class variable. Will be set later by NewStakeDistribution.__init__

        @property
        def stake_fraction(self) -> float:
            return self.number_of_validators / self.total_number_of_validators

    class NewStakeDistribution(StakeDistribution):
        """
        locally defined class. make_stake_distribution_from_map will return an instance of this type.
        """

        def __init__(self):
            # embed the arguments passed to make_stake_distribution_from_map into the new instance of
            # type NewStakeDistribution:
            self.stake_map = stake_map
            clusters = []  # We will set self.cluster = clusters below

            r = Random() if randomness_source is None else randomness_source
            self._sample_cluster = self.new_cluster_sampler(r)
            for cluster_size, count in stake_map.items():
                if isinstance(count, int):
                    clusters += [
                        ClusterWithTotalStake(number_of_validators=cluster_size,
                                              reputation_factor=reputation_factor)
                        for _ in range(count)
                    ]
                else:
                    assert len(count) == 2  # sequence of 2 ints
                    clusters += [
                        ClusterWithTotalStake(number_of_validators=cluster_size,
                                              reputation_factor=count[1])
                        for _ in range(count[0])
                    ]
            clusters.sort()
            self.clusters = clusters

            self.cluster_sizes = [c.number_of_validators for c in clusters]
            self.cluster_sizes_cumulated = list(accumulate(self.cluster_sizes))

            ClusterWithTotalStake.total_number_of_validators = sum(
                [c.number_of_validators for c in clusters])

        def get_clusters(self) -> list[Cluster]:  # actually a list[ClusterWithTotalStake] for some local type
            return self.clusters

        # Note: custom_randomness_source, given to this function, is independent of
        # randomness_source given to make_stake_distribution_from_map.
        # Notably, we can use
        # SD = make_stake_distribution_from_map(..., randomness_source = r1)
        # default_sampler = SD.sample_cluster
        # custom_sampler = SD.new_cluster_sampler(..., randomness_source = r2)
        # In this construction, the intended behaviour is that
        # default_sampler uses r1, custom_sampler uses r2
        def new_cluster_sampler(self, randomness_source: Optional[Random] = None) -> Iterator[Cluster]:
            # NOTE: randomness_source shadows name given to make_stake_distribution_from_map.
            # This is unfortunate, but hard to avoid.
            r: Random = randomness_source if randomness_source is not None else Random()
            while True:
                yield r.choices(self.clusters,
                                cum_weights=self.cluster_sizes_cumulated)[0]

    return NewStakeDistribution()
