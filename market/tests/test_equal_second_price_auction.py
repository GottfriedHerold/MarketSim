from market import EqualSecondPriceMarket, EqualSecondPriceBid

def test_ESP_maximum_bid_by_side():
    L = [1,2,3,4]
    m = EqualSecondPriceMarket.maximum_bid_by_side(L)

    assert m == 6
    print(m)  # will be shown if pytest is run with -rP option.

    L = [1,1,1,1]
    assert EqualSecondPriceMarket.maximum_bid_by_side(L) == 4

    L = [1.0, 2.0, 2.0]
    assert EqualSecondPriceMarket.maximum_bid_by_side(L) == 4.0

    