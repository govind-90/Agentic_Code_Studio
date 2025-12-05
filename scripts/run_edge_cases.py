"""Run several orchestrator edge-case sessions programmatically.

This script invokes `OrchestratorAgent.generate_code` for a set of prompts
to exercise dependency extraction, builds, and testing paths.
"""
import logging
from src.agents.orchestrator import OrchestratorAgent
from src.models.schemas import ProgrammingLanguage


def progress_cb(message, iteration):
    print(f"[Progress] Iteration {iteration}: {message}")


def run_cases():
    agent = OrchestratorAgent()

    prompts = [
        "Implement the 0/1 knapsack problem using dynamic programming. Include clear function and example usage.",
        "Write a function that sorts a list using quicksort and include unit-test-like assertions.",
        "Implement a small script that fetches https://example.com and parses the title using BeautifulSoup.",
        "Write a script that uses numpy to compute the eigenvalues of a given 3x3 matrix and prints them.",
    ]

    results = []

    for i, prompt in enumerate(prompts, start=1):
        print(f"\n=== Running case {i}/{len(prompts)} ===")
        try:
            session = agent.generate_code(
                requirements=prompt,
                language=ProgrammingLanguage.PYTHON,
                max_iterations=5,
                progress_callback=progress_cb,
            )

            print(f"Session {session.session_id} finished: success={session.success} iterations={len(session.iterations)}")
            if session.final_code:
                print(f"Final filename: {session.final_code.filename}")
                print(f"Dependencies: {session.final_code.dependencies}")

            results.append((prompt, session))

        except Exception as e:
            print(f"Case {i} raised exception: {e}")

    print("\nAll cases executed.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_cases()
