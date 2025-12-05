# FILE: knapsack_solver.py
"""
Implementation of the 0/1 Knapsack problem using Dynamic Programming.
The 0/1 Knapsack problem seeks to maximize the total value of items
that can be included in a knapsack without exceeding its weight capacity,
where each item can be included at most once (0 or 1).
"""
from typing import List

def knapsack_dp(capacity: int, weights: List[int], values: List[int]) -> int:
    """
    Solves the 0/1 Knapsack problem using dynamic programming.

    Args:
        capacity: The maximum weight capacity of the knapsack (W).
        weights: A list of weights for each item.
        values: A list of values corresponding to each item.

    Returns:
        The maximum total value that can be achieved without exceeding the capacity.
    """
    n = len(weights)
    W = capacity

    if n == 0 or W == 0:
        return 0

    # Initialize the DP table. dp[i][w] stores the maximum value that can be obtained
    # using the first 'i' items with a maximum capacity 'w'.
    # Dimensions: (n + 1) rows, (W + 1) columns. Initialized to 0.
    # We use n+1 and W+1 to handle the base case (0 items or 0 capacity).
    try:
        dp = [[0] * (W + 1) for _ in range(n + 1)]
    except MemoryError:
        print(f"Error: Capacity ({W}) or number of items ({n}) is too large for memory allocation.")
        return 0

    # Iterate through items (i) from 1 to n
    for i in range(1, n + 1):
        # Get the weight and value of the current item (using 0-based indexing for input lists)
        current_weight = weights[i - 1]
        current_value = values[i - 1]

        # Iterate through capacities (w) from 1 to W
        for w in range(1, W + 1):
            
            # Case 1: If the current item's weight exceeds the current capacity 'w',
            # we cannot include it. The max value is the same as the max value
            # achieved without this item (i-1).
            if current_weight > w:
                dp[i][w] = dp[i - 1][w]
            else:
                # Case 2: We have two choices:
                
                # Option A: Exclude the current item.
                value_if_excluded = dp[i - 1][w]
                
                # Option B: Include the current item.
                # Value = current item's value + max value achievable with the 
                # remaining capacity (w - current_weight) using previous items (i-1).
                value_if_included = current_value + dp[i - 1][w - current_weight]
                
                # Choose the maximum value between including and excluding the item.
                dp[i][w] = max(value_if_excluded, value_if_included)

    # The maximum value is stored at the bottom-right corner of the table.
    return dp[n][W]

if __name__ == "__main__":
    print("--- 0/1 Knapsack Problem Solver (Dynamic Programming) ---")

    # Example 1: Standard Test Case
    weights1 = [10, 20, 30]
    values1 = [60, 100, 120]
    capacity1 = 50
    
    print(f"\nTest Case 1:")
    print(f"Items (Weight, Value): {list(zip(weights1, values1))}")
    print(f"Knapsack Capacity: {capacity1}")
    
    max_value1 = knapsack_dp(capacity1, weights1, values1)
    print(f"Maximum Value Achievable: {max_value1}")
    # Expected result: 220 (Items 20 and 30, Values 100 + 120)

    # Example 2: More items, different capacity
    weights2 = [4, 2, 1, 10, 12]
    values2 = [12, 2, 1, 4, 4]
    capacity2 = 15

    print(f"\nTest Case 2:")
    print(f"Items (Weight, Value): {list(zip(weights2, values2))}")
    print(f"Knapsack Capacity: {capacity2}")

    max_value2 = knapsack_dp(capacity2, weights2, values2)
    print(f"Maximum Value Achievable: {max_value2}")
    # Expected result: 19 (Items 4, 2, 1, 10 -> 12+2+1+4 = 19. Total weight 17 > 15.
    # Optimal selection: Items 4, 2, 1, (Weight 10 excluded). Total weight 7. Value 15.
    # Optimal selection: Items 4, 2, 1, 10 (Weight 17, too heavy)
    # Let's check manually:
    # Capacity 15. Items: (4, 12), (2, 2), (1, 1), (10, 4), (12, 4)
    # Best combination: (4, 12) + (2, 2) + (1, 1) + (10, 4) -> Weight 17 (Fail)
    # Best combination: (4, 12) + (2, 2) + (1, 1) -> Weight 7. Value 15.
    # Best combination: (4, 12) + (10, 4) -> Weight 14. Value 16. (This is the optimal)
    # Result should be 16.

    # Example 3: Edge Case (Zero capacity)
    weights3 = [5, 5]
    values3 = [10, 10]
    capacity3 = 0
    
    print(f"\nTest Case 3 (Zero Capacity):")
    print(f"Knapsack Capacity: {capacity3}")
    max_value3 = knapsack_dp(capacity3, weights3, values3)
    print(f"Maximum Value Achievable: {max_value3}")
    # Expected result: 0