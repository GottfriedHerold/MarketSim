from typing import Tuple, Optional, Generator, Iterator
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

    Note that we do not actually need to model individual validators:
    we only care about how what clusters there are and how many validators each cluster has.
  """

  number_of_validators: int  # number of validators this cluster contains
  reputation_factor: int = 1  # how much this cluster values reputatiaton. May be overriden on a per-object basis.

  @property
  def stake_fraction(self):
    """
      much much a fraction of the total stake this cluster represents.
      Implementing this requires setting a total number of a validators.
    """
    raise NotImplementedError

  def __init__(self,
               number_of_validators: int = 1,
               *,
               reputation_factor: int | None = None):
    self.number_of_validators = number_of_validators
    if reputation_factor is not None:
      self.reputation_factor = reputation_factor


class StakeDistribution(ABC):
  """
    abstract base class that defines the API for a stake distribution
  """

  @abstractmethod
  def get_clusters(self) -> list[Cluster]:
    ...

  @abstractmethod
  def new_cluster_sampler(self,
                          random_source: Optional[Random] = None
                          ) -> Iterator[Cluster]:
    """
      Generator that yields a cluster at random, weighted by stake. Note that this is a generator expression, i.e. uses yield.
    """
    ...

  sample_cluster: Iterator[Cluster]


def MakeStakeDistributionFromMap(
    stake_map: dict[int, int | Tuple[int, int]],
    *,
    random_source: Optional[Random] = None,
    reputation_factor: int = 1) -> StakeDistribution:
  """
  Creates a stake distribution from a map {cluster_size -> how many clusters of this size exist}
  If an entry stake_map[i] is a pair such a stake_map[10] == (5,2),
  this is interpreted as 5 clusters of size 10, with each having a   reputiation factor of 2.

  random_source is used to sample from the set of clusters.

  Example stake_distribution = MakeStakeDistributionFromMap({10: (5,2), 20: (3,1), 100: 1})
  """

  class ClusterWithTotalStake(Cluster):
    total_number_of_validators: int  # class variable

    @property
    def stake_fraction(self):
      return self.number_of_validators / self.total_number_of_validators

  class NewStakeDistribution(StakeDistribution):

    def __init__(self, stake_map, random_source, reputation_factor,
                 ClusterWithTotalStake: type):
      self.stake_map = stake_map
      clusters = []
      # self.random_source = Random() if random_source is None else random_source
      r = Random() if random_source is None else random_source
      self.sample_cluster = self.new_cluster_sampler(r)
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
      self.clusters = clusters

      self.cluster_sizes = [c.number_of_validators for c in clusters]
      self.cluster_sizes_cumulated = list(accumulate(self.cluster_sizes))

      ClusterWithTotalStake.total_number_of_validators = sum(
          [c.number_of_validators for c in clusters])

    def get_clusters(
        self
    ) -> list[
        Cluster]:  # actually a list[ClusterWithTotalStake] for some local type
      return self.clusters

    def new_cluster_sampler(self,
                            random_source: Optional[Random] = None
                            ) -> Iterator[Cluster]:
      r: Random = random_source if random_source is not None else Random()
      while True:
        yield r.choices(self.clusters,
                        cum_weights=self.cluster_sizes_cumulated)[0]

  return NewStakeDistribution(stake_map, random_source, reputation_factor,
                              ClusterWithTotalStake)
