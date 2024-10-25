from typing import Any, Tuple

def remove_duplicates(l1: list[Any],l2: list[Any]) -> Tuple[list[Any], list[Any]]:
    """
    Takes two lists and returns a pair of lists where each entry that is contained in both l1 and l2 is removed.
    (i.e. if an element is contained 3 times in l1 and 5 times in l2, then in the output it is contained 0 times in the first and 2 times in the second list)

    The returned lists are (shallow) copies of the input, so the input is not modified. The comparison is done via is, not via ==.
    The output may be sorted arbitrarily.
    """

    # make a sorted copy of both lists, sorted by id (i.e. by memory address)
    l1_copy = sorted([x for x in l1], key=lambda x: id(x))
    l2_copy = sorted([x for x in l2], key=lambda x: id(x))

    if len(l1) == 0:
        return [], l2_copy
    if len(l2) == 0:
        return l1_copy, []
    
    l1_output = [None] * len(l1_copy)
    l2_output = [None] * len(l2_copy)
    l1_output = l1_output[0:0]
    l2_output = l2_output[0:0]

    while True:
        if l1_copy[-1] is l2_copy[-1]:  # duplicate found
            l1_copy.pop()  # remove duplicate from both list
            l2_copy.pop()
            if len(l1_copy) == 0 or len(l2_copy) == 0:
                break
        # if the last element from l2 copy is larger than that of l1_copy, it is (due to sorting) the largest remaining element
        # of the union of both lists, hence unique (i.e cannot be in the other list). We remove it and put it into the output.
        elif id(l2_copy[-1]) > id(l1_copy[-1]):
            l2_output.append(l2_copy.pop())
            if len(l2_copy) == 0:
                break
        # otherwise the largest element from l1_copy is largest among the union of both list and we proceed analogously.
        else:
            l1_output.append(l1_copy.pop())
            if len(l1_copy) == 0:
                break

    return l1_output + l1_copy, l2_output + l2_copy

# tested
