/**
 * Implementation of the 0/1 Knapsack Problem using Dynamic Programming.
 * 
 * The 0/1 Knapsack problem involves selecting a subset of items, each having a weight and a value,
 * such that the total weight does not exceed a given capacity, and the total value is maximized.
 */
public class KnapsackDP {

    /**
     * Solves the 0/1 Knapsack problem using dynamic programming.
     * 
     * @param values   Array of values of the items.
     * @param weights  Array of weights of the items.
     * @param capacity Maximum weight capacity of the knapsack.
     * @return The maximum total value that can be achieved.
     */
    public static int solveKnapsack(int[] values, int[] weights, int capacity) {
        if (values == null || weights == null || values.length != weights.length || capacity <= 0) {
            System.err.println("Invalid input parameters.");
            return 0;
        }

        int n = values.length;
        
        // DP table: dp[i][w] stores the maximum value that can be obtained 
        // using the first 'i' items with a capacity of 'w'.
        // Dimensions: (n + 1) rows, (capacity + 1) columns
        int[][] dp = new int[n + 1][capacity + 1];

        // Build the DP table
        // i represents the current item index (from 1 to n)
        for (int i = 1; i <= n; i++) {
            // Get the weight and value of the current item (i-1 in 0-indexed arrays)
            int currentWeight = weights[i - 1];
            int currentValue = values[i - 1];

            // w represents the current knapsack capacity being considered (from 0 to capacity)
            for (int w = 1; w <= capacity; w++) {
                
                // Case 1: The current item's weight is greater than the current capacity 'w'.
                // We cannot include this item. The maximum value is the same as without it.
                if (currentWeight > w) {
                    dp[i][w] = dp[i - 1][w];
                } 
                
                // Case 2: The current item can potentially be included.
                else {
                    // Option A: Exclude the current item (Value = dp[i-1][w])
                    int valueExcluding = dp[i - 1][w];
                    
                    // Option B: Include the current item 
                    // Value = current item's value + max value achievable with remaining capacity (w - currentWeight)
                    int valueIncluding = currentValue + dp[i - 1][w - currentWeight];
                    
                    // Take the maximum of the two options
                    dp[i][w] = Math.max(valueExcluding, valueIncluding);
                }
            }
        }

        // The maximum value is stored at the bottom-right corner of the table
        int maxValue = dp[n][capacity];
        
        System.out.println("\n--- DP Table (Max Value at dp[i][w]) ---");
        printDPTable(dp, n, capacity);
        
        // Optional: Reconstruct the items chosen
        reconstructSolution(dp, weights, values, n, capacity);

        return maxValue;
    }

    /**
     * Helper function to print the DP table for visualization.
     */
    private static void printDPTable(int[][] dp, int n, int capacity) {
        System.out.print("W\\I |");
        for (int i = 0; i <= n; i++) {
            System.out.printf(" I%d |", i);
        }
        System.out.println();
        System.out.println("----+" + "----".repeat(n + 1));

        for (int w = 0; w <= capacity; w++) {
            System.out.printf(" %2d |", w);
            for (int i = 0; i <= n; i++) {
                System.out.printf(" %2d |", dp[i][w]);
            }
            System.out.println();
        }
    }

    /**
     * Reconstructs and prints the set of items chosen to achieve the maximum value.
     */
    private static void reconstructSolution(int[][] dp, int[] weights, int[] values, int n, int capacity) {
        System.out.println("\n--- Items Chosen ---");
        int w = capacity;
        int totalWeight = 0;
        
        // Iterate backwards from the last item (n) and max capacity (capacity)
        for (int i = n; i > 0 && w > 0; i--) {
            // If dp[i][w] > dp[i-1][w], it means the value increased at this step, 
            // implying item 'i' (index i-1) was included.
            if (dp[i][w] != dp[i - 1][w]) {
                int itemIndex = i - 1;
                System.out.printf("Item %d: Value=%d, Weight=%d\n", 
                                  i, values[itemIndex], weights[itemIndex]);
                
                // Subtract the weight of the included item and continue checking
                w -= weights[itemIndex];
                totalWeight += weights[itemIndex];
            }
        }
        System.out.printf("Total Weight Used: %d / %d\n", totalWeight, capacity);
    }

    public static void main(String[] args) {
        // Sample Data
        int[] values = {60, 100, 120};
        int[] weights = {10, 20, 30};
        int capacity = 50;

        System.out.println("Knapsack Capacity: " + capacity);
        System.out.println("Items available:");
        for (int i = 0; i < values.length; i++) {
            System.out.printf("Item %d: Value=%d, Weight=%d\n", i + 1, values[i], weights[i]);
        }

        try {
            long startTime = System.nanoTime();
            int maxVal = solveKnapsack(values, weights, capacity);
            long endTime = System.nanoTime();

            System.out.println("\n========================================");
            System.out.println("Maximum Achievable Value: " + maxVal);
            System.out.printf("Execution Time: %.3f ms\n", (endTime - startTime) / 1_000_000.0);
            System.out.println("========================================");

        } catch (Exception e) {
            System.err.println("An unexpected error occurred during knapsack calculation: " + e.getMessage());
            e.printStackTrace();
        }
    }
}