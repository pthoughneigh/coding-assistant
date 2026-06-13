from agent.agent import agent
def cli() -> None:
    while True:
        question = input("user: ")
        if question.upper() == 'QUIT':
            break
        if not question.strip():
            continue
    
        agent(question=question)

        
if __name__ == '__main__':
    cli()