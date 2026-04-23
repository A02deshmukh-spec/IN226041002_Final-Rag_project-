import uuid
from chatbot import build_graph

def main():
    print("=" * 60)
    print("Welcome to the RAG Support Assistant w/ LangGraph & HITL")
    print("Type 'quit' to exit.")
    print("=" * 60)
    
    app = build_graph()
    
    # We assign a threaded ID so memory checkpointer isolates this conversation
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        user_input = input("\nUser > ")
        if user_input.lower() in ["quit", "exit"]:
            print("Session ended.")
            break
            
        initial_state = {
            "question": user_input,
            "hitl_response": "",
            "generation": ""
        }
        
        # Execute the graph
        for event in app.stream(initial_state, config, stream_mode="values"):
            pass 
            
        # Inspect state. If LangGraph hit an `interrupt_before`, it will halt execution 
        # and store a `next` task pointer indicating where it paused.
        state = app.get_state(config)
        
        if state.next and state.next[0] == "hitl_node":
            print("\n🚨 [SYSTEM] Automated workflow suspended. HITL Escalation required!")
            print(f"🚨 [QUESTION WAITING FOR ANSWER]: '{state.values['question']}'")
            
            human_response = input("Human Agent Override > ")
            
            # Inject the human operator's text back into the Graph State
            app.update_state(config, {"hitl_response": human_response})
            
            # Resume processing from the halt point
            print("...[System] Resuming graph execution...")
            for event in app.stream(None, config, stream_mode="values"):
                pass
                
        # Final output fetching
        # Re-fetch state because the graph finished
        final_state = app.get_state(config).values
        answer = final_state.get('generation', 'No answer generated.')
        
        print("-" * 60)
        print(f"Bot > {answer}")
        print("-" * 60)

if __name__ == "__main__":
    main()

