from agent.agent import agent
from evals.harness import run_eval

def cli() -> None:
    while True:
        try:
            question = input("user: ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if question.upper() == 'QUIT':
            break
        if not question.strip():
            continue

        try:
            agent(question=question)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == '__main__':
    cli()