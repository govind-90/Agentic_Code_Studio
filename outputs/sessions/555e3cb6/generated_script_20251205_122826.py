import logging
from typing import List, Tuple

# Setup basic logging. Set level to WARNING/INFO for production, DEBUG for tracing.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def knapsack_dp(weights: List[int], values: List[int], capacity: int) -> Tuple[int, List[int]]:
    """
    Solves the 0/1 Knapsack problem using dynamic programming (2D table approach).

    The 0/1 Knapsack problem seeks to maximize the total value of items
    included in a knapsack without exceeding its weight capacity.

    Args:
        weights: A list of weights for each item.
        values: A list of values corresponding to each item.
        capacity: The maximum weight the knapsack can hold.

    Returns:
        A tuple containing:
        1. The maximum total value achievable.
        2. A list of indices (0-based) of the items included in the optimal solution.
    """
    n = len(weights)

    if n == 0 or capacity <= 0:
        logging.warning("Input constraints violated (no items or zero/negative capacity). Returning 0 value.")
        return 0, []

    # 1. Initialize the DP table
    # dp[i][w] stores the maximum value achievable using the first i items
    # (items 0 to i-1) with a capacity of w.
    # Dimensions: (n + 1) rows, (capacity + 1) columns
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]

    logging.debug(f"Starting DP calculation for {n} items and capacity {capacity}")

    # 2. Fill the DP table
    # i iterates through the items (1 to n, representing items 0 to n-1)
    for i in range(1, n + 1):
        # Get the weight and value of the current item (item i-1)
        current_weight = weights[i - 1]
        current_value = values[i - 1]

        # w iterates through the possible capacities (0 to capacity)
        for w in range(capacity + 1):
            
            # Check if the current item can fit in the remaining capacity w
            if current_weight > w:
                # Cannot include the item. Value is the same as without this item.
                dp[i][w] = dp[i - 1][w]
            else:
                # We choose the maximum of two options:
                
                # a) Exclude the current item (Value = dp[i - 1][w])
                value_excluding = dp[i - 1][w]
                
                # b) Include the current item (Value = current_value + dp[i - 1][w - current_weight])
                value_including = current_value + dp[i - 1][w - current_weight]
                
                dp[i][w] = max(value_excluding, value_including)
                
    # The maximum value is stored at dp[n][capacity]
    max_value = dp[n][capacity]
    logging.debug(f"DP Table filled. Max value found: {max_value}")

    # 3. Trace back to find the included items
    included_items: List[int] = []
    w = capacity
    
    # Iterate backwards through the items (from n down to 1)
    for i in range(n, 0, -1):
        # If dp[i][w] is different from dp[i-1][w], it means the decision at step i
        # was to include item i-1, as including it yielded a higher value.
        if dp[i][w] != dp[i - 1][w]:
            item_index = i - 1
            included_items.append(item_index)
            
            # Update the remaining capacity
            w -= weights[item_index]
            
            if w == 0:
                break
    
    # Reverse the list to show items in their original index order
    included_items.reverse()
    
    return max_value, included_items

if __name__ == "__main__":
    # Set logging level to INFO for standard execution output
    logging.getLogger().setLevel(logging.INFO)
    
    # --- Example 1: Standard Knapsack Problem ---
    
    # Items: (Weight, Value)
    # Item 0: (2, 3)
    # Item 1: (3, 4)
    # Item 2: (4, 5)
    # Item 3: (5, 6)
    
    weights_1 = [2, 3, 4, 5]
    values_1 = [3, 4, 5, 6]
    capacity_1 = 5
    
    print("--- Example 1: Capacity 5 ---")
    print(f"Available Items (W, V): {list(zip(weights_1, values_1))}")
    print(f"Knapsack Capacity: {capacity_1}")
    
    max_val_1, items_1 = knapsack_dp(weights_1, values_1, capacity_1)
    
    # Verification
    total_weight_1 = sum(weights_1[i] for i in items_1)
    
    print(f"\nResult: Max Value = {max_val_1}")
    print(f"Included Item Indices: {items_1}")
    print(f"Total Weight Used: {total_weight_1}")
    
    print("-" * 40)

    # --- Example 2: Larger Problem ---
    
    weights_2 = [10, 20, 30]
    values_2 = [60, 100, 120]
    capacity_2 = 50
    
    print("--- Example 2: Capacity 50 ---")
    print(f"Available Items (W, V): {list(zip(weights_2, values_2))}")
    print(f"Knapsack Capacity: {capacity_2}")
    
    max_val_2, items_2 = knapsack_dp(weights_2, values_2, capacity_2)
    
    # Verification
    total_weight_2 = sum(weights_2[i] for i in items_2)
    total_value_2 = sum(values_2[i] for i in items_2)
    
    print(f"\nResult: Max Value = {max_val_2}")
    print(f"Included Item Indices: {items_2}")
    print(f"Total Weight Used: {total_weight_2}, Total Value Verified: {total_value_2}")
    
    print("-" * 40)
    
    # --- Example 3: Edge Case (Item too heavy) ---
    weights_3 = [100]
    values_3 = [500]
    capacity_3 = 50
    
    print("--- Example 3: Item Too Heavy ---")
    max_val_3, items_3 = knapsack_dp(weights_3, values_3, capacity_3)
    print(f"Result: Max Value = {max_val_3}, Items: {items_3}")