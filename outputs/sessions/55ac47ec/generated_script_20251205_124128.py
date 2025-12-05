# REQUIRES: None (Standard Python 3.10+)

import logging
from typing import List, Tuple

# Setup basic logging. Set level to INFO for standard output, DEBUG for detailed tracing.
# We use DEBUG level internally but keep the default handler at INFO unless explicitly changed.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG) # Uncomment this line to see detailed DP steps

def knapsack_dp(weights: List[int], values: List[int], capacity: int) -> Tuple[int, List[int]]:
    """
    Solves the 0/1 Knapsack problem using dynamic programming (DP).

    The 0/1 Knapsack problem seeks to maximize the total value of items
    included in a knapsack without exceeding its weight capacity.

    Args:
        weights: A list of integers representing the weight of each item.
        values: A list of integers representing the value of each item.
        capacity: The maximum weight capacity of the knapsack.

    Returns:
        A tuple containing:
        1. The maximum total value achievable.
        2. A list of indices (0-based) of the items selected.
    """
    n = len(weights)

    if n == 0 or capacity <= 0:
        return 0, []

    # 1. Initialization: Create the DP table
    # dp[i][w] stores the maximum value achievable using the first i items
    # (items 0 to i-1) with a capacity of w.
    # Size: (n + 1) rows x (capacity + 1) columns
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]

    logger.debug(f"Starting DP calculation for {n} items and capacity {capacity}")

    # 2. Iteration: Fill the DP table
    # i represents the item count (1 to n)
    for i in range(1, n + 1):
        # Get the weight and value of the current item (i-1 in 0-based index)
        current_weight = weights[i - 1]
        current_value = values[i - 1]

        # w represents the current capacity (1 to capacity)
        for w in range(1, capacity + 1):
            
            # Case 1: If the current item's weight exceeds the current capacity 'w',
            # we cannot include it. The value is inherited from the previous item set.
            if current_weight > w:
                dp[i][w] = dp[i - 1][w]
            
            # Case 2: We can potentially include the item.
            else:
                # Option A: Exclude the item (Value from the previous item set)
                value_excluding = dp[i - 1][w]
                
                # Option B: Include the item 
                # (Current value + max value achievable with the remaining capacity: w - current_weight)
                value_including = current_value + dp[i - 1][w - current_weight]
                
                # Take the maximum of the two options
                dp[i][w] = max(value_excluding, value_including)
                
                logger.debug(f"i={i}, w={w}. W={current_weight}, V={current_value}. DP[{i}][{w}] = {dp[i][w]}")

    # The maximum value is stored at the bottom-right corner
    max_value = dp[n][capacity]

    # 3. Traceback: Determine which items were selected
    selected_items: List[int] = []
    w = capacity
    
    # Iterate backwards through the items (from n down to 1)
    for i in range(n, 0, -1):
        # If the value at dp[i][w] is different from dp[i-1][w], 
        # it means item i-1 was included to achieve this maximum value.
        if dp[i][w] != dp[i - 1][w]:
            # Item i-1 was selected
            item_index = i - 1
            selected_items.append(item_index)
            
            # Reduce the remaining capacity by the weight of the selected item
            w -= weights[item_index]
            
            logger.debug(f"Item {item_index} selected. Remaining capacity: {w}")
            
            # Optimization: If capacity hits 0, we can stop tracing
            if w == 0:
                break

    # The items were found in reverse order of iteration, so reverse the list for correct output
    selected_items.reverse()

    return max_value, selected_items

if __name__ == "__main__":
    
    print("="*50)
    print("0/1 KNAPSACK PROBLEM (DYNAMIC PROGRAMMING)")
    print("="*50)

    # --- Example 1: Standard Test Case ---
    
    # Item 0: W=2, V=3
    # Item 1: W=3, V=4
    # Item 2: W=4, V=5
    # Item 3: W=5, V=8
    
    weights1 = [2, 3, 4, 5]
    values1 = [3, 4, 5, 8]
    capacity1 = 5
    
    print("\n--- Example 1: Capacity 5 ---")
    print(f"Items (W, V): {list(zip(weights1, values1))}")
    print(f"Capacity: {capacity1}")
    
    try:
        max_val1, selected_items1 = knapsack_dp(weights1, values1, capacity1)
        
        # Verification: Optimal choice is Item 3 (W=5, V=8)
        total_weight1 = sum(weights1[i] for i in selected_items1)
        total_value1 = sum(values1[i] for i in selected_items1)
        
        print(f"\nMaximum Value Achieved: {max_val1}")
        print(f"Selected Item Indices: {selected_items1}")
        print(f"Total Weight Used: {total_weight1} (Capacity Limit: {capacity1})")
        print(f"Total Value Calculated: {total_value1}")
        
        if max_val1 == 8 and selected_items1 == [3]:
            print("Verification Status: SUCCESS")
        else:
            print("Verification Status: FAILED (Expected Value: 8, Items: [3])")
            
    except Exception as e:
        logger.error(f"An error occurred during Example 1 execution: {e}")


    # --- Example 2: Larger Test Case ---
    
    weights2 = [10, 20, 30]
    values2 = [60, 100, 120]
    capacity2 = 50
    
    print("\n" + "="*40)
    print("--- Example 2: Capacity 50 ---")
    print(f"Items (W, V): {list(zip(weights2, values2))}")
    print(f"Capacity: {capacity2}")
    
    try:
        max_val2, selected_items2 = knapsack_dp(weights2, values2, capacity2)
        
        # Verification: Optimal choice is Item 1 (W=20, V=100) + Item 2 (W=30, V=120) = W=50, V=220
        total_weight2 = sum(weights2[i] for i in selected_items2)
        total_value2 = sum(values2[i] for i in selected_items2)
        
        print(f"\nMaximum Value Achieved: {max_val2}")
        print(f"Selected Item Indices: {selected_items2}")
        print(f"Total Weight Used: {total_weight2} (Capacity Limit: {capacity2})")
        print(f"Total Value Calculated: {total_value2}")
        
        # Ensure the selected items are sorted for comparison
        if max_val2 == 220 and sorted(selected_items2) == [1, 2]:
            print("Verification Status: SUCCESS")
        else:
            print("Verification Status: FAILED (Expected Value: 220, Items: [1, 2])")
            
    except Exception as e:
        logger.error(f"An error occurred during Example 2 execution: {e}")