from utils import remove_duplicates


def test_remove_duplicates():
    x1 = [1]
    x2 = [2]
    x3 = [3]
    x4 = [4]
    x5 = [5]
    list1 = [x1, x2, x3, x4, x1, x1, x5, x1, x2, x5]
    list2 = [x1, x1, x2, x3, x3, x4, x4, x1, x1, x1, x2]
    list1_copy = list1[:]
    list2_copy = list2[:]

    l1_no_duplicates, l2_no_duplicates = remove_duplicates(list1, list2)
    assert (list1 == list1_copy)
    assert (list2 == list2_copy)
    assert(sorted(l1_no_duplicates) == [x5,x5])
    assert(sorted(l2_no_duplicates) == [x1,x3,x4])