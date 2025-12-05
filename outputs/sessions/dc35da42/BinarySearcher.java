/**
 * FILE: BinarySearcher.java
 * 
 * Implements the binary search algorithm (iterative approach) in Java.
 * Binary search requires the input array to be sorted.
 */
package com.example.algorithms;

import java.util.Arrays;

public class BinarySearcher {

    /**
     * Performs an iterative binary search on a sorted array to find the index of the target value.
     * 
     * @param array The sorted array of integers to search within.
     * @param target The value to search for.
     * @return The index of the target if found, or -1 if the target is not present.
     */
    public static int binarySearch(int[] array, int target) {
        // 1. Input validation
        if (array == null || array.length == 0) {
            System.out.println("Warning: Array is null or empty.");
            return -1;
        }

        int low = 0;
        int high = array.length - 1;

        // Loop continues as long as the search space is valid
        while (low <= high) {
            
            // Calculate the middle index safely to prevent potential integer overflow.
            // This is preferred over (low + high) / 2 when dealing with extremely large arrays.
            int mid = low + (high - low) / 2;

            // Check if the middle element is the target
            if (array[mid] == target) {
                return mid; // Target found
            } 
            
            // If the middle element is less than the target, ignore the lower half
            else if (array[mid] < target) {
                low = mid + 1;
            } 
            
            // If the middle element is greater than the target, ignore the upper half
            else {
                high = mid - 1;
            }
        }

        // If the loop finishes, the target was not found
        return -1;
    }

    /**
     * Main method for demonstration and testing.
     */
    public static void main(String[] args) {
        // Binary search requires a sorted array
        int[] sortedArray = {2, 5, 8, 12, 16, 23, 38, 56, 72, 91};
        
        System.out.println("--- Binary Search Demonstration ---");
        System.out.println("Array: " + Arrays.toString(sortedArray));

        // Test Case 1: Target found (middle)
        int target1 = 23;
        int index1 = binarySearch(sortedArray, target1);
        printResult(target1, index1, sortedArray);

        // Test Case 2: Target found (start edge)
        int target2 = 2;
        int index2 = binarySearch(sortedArray, target2);
        printResult(target2, index2, sortedArray);

        // Test Case 3: Target found (end edge)
        int target3 = 91;
        int index3 = binarySearch(sortedArray, target3);
        printResult(target3, index3, sortedArray);

        // Test Case 4: Target not found
        int target4 = 40;
        int index4 = binarySearch(sortedArray, target4);
        printResult(target4, index4, sortedArray);
        
        // Test Case 5: Target not found (outside range)
        int target5 = 100;
        int index5 = binarySearch(sortedArray, target5);
        printResult(target5, index5, sortedArray);

        // Test Case 6: Empty array handling
        int[] emptyArray = {};
        int target6 = 10;
        System.out.println("\nTesting empty array...");
        int index6 = binarySearch(emptyArray, target6);
        printResult(target6, index6, emptyArray);
    }
    
    /**
     * Helper method to print the search results clearly.
     */
    private static void printResult(int target, int index, int[] array) {
        if (index != -1) {
            System.out.printf("Target %d found at index %d (Value: %d)%n", 
                              target, index, array[index]);
        } else {
            System.out.printf("Target %d not found.%n", target);
        }
    }
}