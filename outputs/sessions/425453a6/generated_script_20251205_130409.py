from typing import List, TypeVar, Any
import random
import sys

# Set recursion limit higher for potentially deep quicksort calls,
# although the standard Python limit (usually 1000) is often sufficient.
# sys.setrecursionlimit(2000) 

# Define a type variable for generic lists of comparable items
# We use Any here because Python's standard typing doesn't enforce comparability
# at compile time, but we assume the elements support comparison operators (<, ==, >).
T = TypeVar('T', bound=Any)

def quicksort(data: List[T]) -> List[T]:
    """
    Sorts a list using the Quicksort algorithm (recursive, non-in-place implementation).

    Args:
        data: The list of comparable elements to be sorted.

    Returns:
        A new list containing the sorted elements.
    """
    # 1. Base Case: If the list has 0 or 1 element, it is already sorted.
    if len(data) <= 1:
        return data

    try:
        # 2. Choose a Pivot: Select the first element as the pivot.
        pivot = data[0]

        # 3. Partitioning: Create three sub-lists based on comparison with the pivot.
        less: List[T] = []
        equal: List[T] = [pivot]
        greater: List[T] = []

        # Iterate through the rest of the elements
        for element in data[1:]:
            if element < pivot:
                less.append(element)
            elif element == pivot:
                equal.append(element)
            else: # element > pivot
                greater.append(element)

        # 4. Recursive Step: Recursively sort the 'less' and 'greater' sub-lists.
        # 5. Combine: Concatenate the sorted 'less', 'equal', and sorted 'greater' lists.
        return quicksort(less) + equal + quicksort(greater)

    except TypeError as e:
        # Handle cases where elements are not comparable (e.g., mixing strings and integers)
        print(f"Error during comparison in quicksort: {e}", file=sys.stderr)
        raise ValueError("List elements must be mutually comparable for quicksort.")


def run_tests():
    """
    Runs unit-test-like assertions to verify the quicksort implementation.
    """
    print("--- Running Quicksort Verification Tests ---")

    # Test Case 1: Empty list
    test_list_1: List[int] = []
    expected_1 = sorted(test_list_1)
    result_1 = quicksort(test_list_1)
    assert result_1 == expected_1, f"Test 1 Failed: Expected {expected_1}, Got {result_1}"
    print(f"Test 1 (Empty List) Passed.")

    # Test Case 2: Single element
    test_list_2 = [42]
    expected_2 = sorted(test_list_2)
    result_2 = quicksort(test_list_2)
    assert result_2 == expected_2, f"Test 2 Failed: Expected {expected_2}, Got {result_2}"
    print(f"Test 2 (Single Element) Passed.")

    # Test Case 3: Already sorted list
    test_list_3 = [1, 2, 3, 4, 5]
    expected_3 = sorted(test_list_3)
    result_3 = quicksort(test_list_3)
    assert result_3 == expected_3, f"Test 3 Failed: Expected {expected_3}, Got {result_3}"
    print(f"Test 3 (Already Sorted) Passed.")

    # Test Case 4: Reverse sorted list
    test_list_4 = [5, 4, 3, 2, 1]
    expected_4 = sorted(test_list_4)
    result_4 = quicksort(test_list_4)
    assert result_4 == expected_4, f"Test 4 Failed: Expected {expected_4}, Got {result_4}"
    print(f"Test 4 (Reverse Sorted) Passed.")

    # Test Case 5: List with duplicates
    test_list_5 = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
    expected_5 = sorted(test_list_5)
    result_5 = quicksort(test_list_5)
    assert result_5 == expected_5, f"Test 5 Failed: Expected {expected_5}, Got {result_5}"
    print(f"Test 5 (With Duplicates) Passed.")

    # Test Case 6: Random large list
    random.seed(42) # Ensure reproducibility
    test_list_6 = [random.randint(0, 1000) for _ in range(100)]
    expected_6 = sorted(test_list_6)
    result_6 = quicksort(test_list_6)
    assert result_6 == expected_6, f"Test 6 Failed: Random list not sorted correctly."
    print(f"Test 6 (Large Random List) Passed.")

    # Test Case 7: List of strings
    test_list_7 = ["banana", "apple", "cherry", "date", "fig"]
    expected_7 = sorted(test_list_7)
    result_7 = quicksort(test_list_7)
    assert result_7 == expected_7, f"Test 7 Failed: String list not sorted correctly."
    print(f"Test 7 (String List) Passed.")

    print("\nAll Quicksort tests passed successfully!")


if __name__ == "__main__":
    run_tests()