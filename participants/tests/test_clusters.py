# Since we use pytest and don't want to bother too much with
# packaging, tests (and example code, which one can just make a test)
# should simply go into a tests subfolder with an (empty) __init__.py
#
# To work with the automatic test discovery of pytest,
# tests must be placed into files named test_<foo>.py
# Within such files, pytest automatically finds and runs
#  - functions named test_<sth>
#  - methods named test_<sth> inside (__init__-less) classes named Test<bar>.
#
# see https://docs.pytest.org/en/8.2.x/explanation/goodpractices.html#conventions-for-python-test-discovery


# Example of a (failing) test:
# (This is commented out, precisely because it fails)

# def test_foo():
#     assert False

import itertools
import random

from participants import Cluster, StakeDistribution, make_stake_distribution_from_map


# Example code how to use make_stake_distribution_from_map
def test_make_stake_distribution_from_map():
    # 5+3+1 clusters of sizes 10,10,10,10,10,20,20,20,100
    # The size-10 clusters have reputation_factor 2
    # (NOTE: intentionally sorted wrongly, to check that sorting works)
    d = {20: (3, 1), 10: (5, 2), 100: 1}

    SD = make_stake_distribution_from_map(d)

    clusters = SD.get_clusters()
    assert [c.number_of_validators for c in clusters] == [10, 10, 10, 10, 10, 20, 20, 20, 100]
    assert [c.reputation_factor for c in clusters] == [2, 2, 2, 2, 2, 1.0, 1.0, 1.0, 1.0]

    for c in clusters:
        assert abs(c.stake_fraction - c.number_of_validators/210) < 0.0001

    # itertools.islice(iterator, number) returns (an iterator that yields) number many samples from iterator.
    # This may be used to be able to write a simple for-loop, such as
    # for c in itertools.islice(SD.sample_cluster, number):
    #   ...
    #
    # Here, we just get a list.
    number_of_samples = 50000
    some_sampled_clusters = list(itertools.islice(SD.sample_cluster, number_of_samples))

    assert len(some_sampled_clusters) == number_of_samples
    for c in some_sampled_clusters:
        assert c in clusters

    # Check that distribution is roughly what we expect:
    size_distribution = {10: 0, 20: 0, 100: 0}
    for c in some_sampled_clusters:
        size_distribution[c.number_of_validators] += 1
    num_10 = size_distribution[10]/number_of_samples
    num_20 = size_distribution[20]/number_of_samples
    num_100 = size_distribution[100]/number_of_samples

    # we expect
    #   num_10 to be around 50/210
    #   num_20 to be around 60/210
    #   num_100 to be around 100/210

    assert abs(num_10 - 50/210) < 0.05
    assert abs(num_20 - 60/210) < 0.05
    assert abs(num_100 - 100/210) < 0.05

    # Check that using a deterministic RNG works:

    RNG1 = random.Random(23525)  # 23525 is the randomness seed
    RNG2 = random.Random(23525)  # independent generator with same seed

    sampler1 = SD.new_cluster_sampler(RNG1)
    sampler2 = SD.new_cluster_sampler(RNG2)

    # Get 100 samples from sampler1, then 200 from sampler2, then 100 from sampler1.
    samples1 = list(itertools.islice(sampler1, 100))
    samples2 = list(itertools.islice(sampler2, 200))
    samples3 = list(itertools.islice(sampler1, 100))
    assert samples1 + samples3 == samples2





