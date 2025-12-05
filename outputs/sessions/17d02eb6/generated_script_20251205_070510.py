# FILE: hello_world.py
# REQUIRES: None

import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main():
    """
    Main function to execute the script's primary logic.
    """
    try:
        # The message to be printed, as per user requirements.
        message = "Hello, Agentic Code Studio!"

        # Print the message to the standard output.
        print(message)

        # Log a success message for tracking and debugging purposes.
        logging.info("Successfully printed the greeting message.")

    except Exception as e:
        # In the unlikely event of an error with this simple operation,
        # log the error for diagnostics.
        logging.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    # This is the standard entry point for a Python script.
    # The main() function is called only when the script is executed directly.
    main()
