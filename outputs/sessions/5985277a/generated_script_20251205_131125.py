import logging
from typing import List, Tuple

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def knapsack_dp(capacity: int, weights: List[int], values: List[int]) -> Tuple[int, List[int]]:
    """
    Solves the 0/1 Knapsack problem using dynamic programming.

    The function calculates the maximum value that can be obtained by selecting 
    a subset of items such that their total weight does not exceed the knapsack capacity.

    Args:
        capacity: The maximum weight capacity of the knapsack.
        weights: A list of weights for each item.
        values: A list of values corresponding to each item.

    Returns:
        A tuple containing:
        1. The maximum total value achievable.
        2. A list of indices (0-based) of the items included in the optimal solution.
    
    Raises:
        ValueError: If inputs are invalid (e.g., mismatched list lengths, negative capacity/weights/values).
    """
    
    N = len(weights)
    
    # --- Input Validation (Fixing previous failure mode) ---
    if N != len(values):
        logging.error("Input validation failed: Length of weights (%d) does not match length of values (%d).", N, len(values))
        raise ValueError("The number of weights must match the number of values.")
    
    if capacity < 0:
        logging.error("Input validation failed: Capacity cannot be negative (%d).", capacity)
        raise ValueError("Knapsack capacity must be non-negative.")
        
    if any(w < 0 or v < 0 for w, v in zip(weights, values)):
        logging.error("Input validation failed: Weights or values contain negative numbers.")
        raise ValueError("Weights and values must be non-negative.")

    logging.info("Starting Knapsack DP calculation for %d items and capacity %d.", N, capacity)

    # Initialize the DP table: dp[i][w] stores the maximum value using the first i items 
    # with a capacity of w.
    # Dimensions: (N + 1) rows, (capacity + 1) columns
    # We use list comprehension for initialization to ensure deep copies.
    dp = [[0] * (capacity + 1) for _ in range(N + 1)]

    # --- Fill the DP table ---
    for i in range(1, N + 1):
        # Current item index (0-based)
        item_index = i - 1
        w_i = weights[item_index]
        v_i = values[item_index]
        
        for w in range(capacity + 1):
            
            # Case 1: The current item is too heavy to fit in the remaining capacity w
            if w_i > w:
                # We must exclude the current item. Value is the same as the previous row (i-1).
                dp[i][w] = dp[i - 1][w]
            
            # Case 2: The current item fits
            else:
                # Option A: Exclude the current item (Value from previous row)
                value_exclude = dp[i - 1][w]
                
                # Option B: Include the current item (Value + Max value from remaining capacity)
                # Remaining capacity is w - w_i
                value_include = v_i + dp[i - 1][w - w_i]
                
                # Take the maximum of the two options
                dp[i][w] = max(value_exclude, value_include)

    max_value = dp[N][capacity]
    logging.info("DP table calculation complete. Maximum value found: %d.", max_value)

    # --- Backtracking to find the selected items ---
    
    selected_items: List[int] = []
    w = capacity
    
    # Iterate backwards through the items (rows)
    for i in range(N, 0, -1):
        # If the value at dp[i][w] is different from dp[i-1][w], 
        # it means item i was included to achieve the maximum value.
        if dp[i][w] != dp[i - 1][w]:
            item_index = i - 1
            selected_items.append(item_index)
            
            # Reduce the remaining capacity by the weight of the included item
            w -= weights[item_index]
            
            # Optimization: If capacity is exhausted, stop
            if w == 0:
                break

    # The items were found in reverse order, so reverse the list for correct output
    selected_items.reverse()
    
    logging.info("Selected items indices: %s", selected_items)
    
    return max_value, selected_items

if __name__ == "__main__":
    
    # --- Example 1: Standard Test Case ---
    
    CAPACITY_1 = 50
    WEIGHTS_1 = [10, 20, 30]
    VALUES_1 = [60, 100, 120]
    
    # Expected optimal solution: Items 1 (20kg, $100) and 3 (30kg, $120). Total: 50kg, $220.
    
    print("--- Running Example 1: Standard Knapsack ---")
    try:
        max_val_1, items_1 = knapsack_dp(CAPACITY_1, WEIGHTS_1, VALUES_1)
        
        print(f"\nKnapsack Capacity: {CAPACITY_1}")
        print(f"Items (Weight, Value): {list(zip(WEIGHTS_1, VALUES_1))}")
        print(f"Maximum Value Achieved: ${max_val_1}")
        
        total_weight = sum(WEIGHTS_1[i] for i in items_1)
        total_value = sum(VALUES_1[i] for i in items_1)
        
        print(f"Selected Items Indices: {items_1}")
        print(f"Total Weight Used: {total_weight} (Max: {CAPACITY_1})")
        print(f"Total Value Verified: ${total_value}")
        
    except ValueError as e:
        print(f"Error in Example 1: {e}")

    print("\n" + "="*50 + "\n")

    # --- Example 2: Test Case for Input Validation (Mismatched Lists) ---
    
    CAPACITY_2 = 10
    WEIGHTS_2 = [2, 3, 4]
    VALUES_2 = [3, 4] # Missing one value
    
    print("--- Running Example 2: Input Validation Test (Expected Failure) ---")
    try:
        knapsack_dp(CAPACITY_2, WEIGHTS_2, VALUES_2)
    except ValueError as e:
        print(f"Successfully caught expected error: {e}")
        
    print("\n" + "="*50 + "\n")

    # --- Example 3: Test Case for Zero Capacity ---
    
    CAPACITY_3 = 0
    WEIGHTS_3 = [1, 1, 1]
    VALUES_3 = [10, 20, 30]
    
    print("--- Running Example 3: Zero Capacity Test ---")
    try:
        max_val_3, items_3 = knapsack_dp(CAPACITY_3, WEIGHTS_3, VALUES_3)
        print(f"Knapsack Capacity: {CAPACITY_3}")
        print(f"Maximum Value Achieved: ${max_val_3}")
        print(f"Selected Items Indices: {items_3}")
        
    except ValueError as e:
        print(f"Error in Example 3: {e}")