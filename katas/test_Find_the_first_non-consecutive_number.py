import pytest

"""
Your task is to find the first element of an array that is not consecutive.

By not consecutive we mean not exactly 1 larger than the previous element of the array.

E.g. If we have an array [1,2,3,4,6,7,8] then 1 then 2 then 3 then 4 are all consecutive but 6 is not, so that's the first non-consecutive number.

If the whole array is consecutive then return null2.

The array will always have at least 2 elements1 and all elements will be numbers.
The numbers will also all be unique and in ascending order. The numbers could be positive or negative and the first non-consecutive could be either too!
"""


def find_first_non_consecutive(arr):
    for i in range(1, len(arr)):
        if arr[i] != arr[i - 1] + 1:
            return arr[i]
    return None


@pytest.mark.parametrize(
    "arr, expected",
    [
        ([1, 2, 3, 4, 6, 7, 8], 6),
        ([1, 2, 3, 4, 5, 6, 7, 8], None),
        ([4, 6, 7, 8, 9, 11], 6),
        ([4, 5, 6, 7, 8, 9, 11], 11),
        ([31, 32], None),
        ([-3, -2, 0, 1], 0),
        ([-5, -4, -3, -1], -1),
    ],
)
def test_first_non_consecutive(arr, expected):
    assert find_first_non_consecutive(arr) == expected
