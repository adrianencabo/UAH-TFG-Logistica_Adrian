import os
import chainlit as cl
import logging
from langchain_core.messages import HumanMessage
from agent import get_agent

# Configure functional logging to a file, separating it from the UI logs
logging.basicConfig(
    filename='sistema_funcional.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

# Entry point when a user starts a new conversation in Chainlit
@cl.on_chat_start
async def on_chat_start():
    # Initialize our LangGraph agent
    agent = get_agent()
    # Save it in the user session to reuse it in each message
    cl.user_session.set("agent", agent)
    
    # Initialize an empty list to store message history
    cl.user_session.set("messages", [])
    
    # Welcome message
    await cl.Message(
        content="""Hello! 👋 I am your Intelligent AnyLogistix Assistant powered by Google Gemini.

I can help you to:
📦 **Phase 1**: Open projects, explore scenarios, run simulations, and export dashboard results.
⚙️ **Phase 2**: Analyze simulation KPIs and autonomously modify scenarios (like increasing demand) to improve performance.
📚 **Phase 3 (RAG)**: Answer theoretical logistics questions or AnyLogistix feature queries by reading the internal knowledge base.

To get started, you can ask me something like:
- *"What is the bullwhip effect?"* (RAG)
- *"What scenarios are available?"* (Phase 1)
- *"Simulate the Cold Chain scenario and modify it to improve profit"* (Phase 2)

How can I help you today?"""
    ).send()

# This function runs every time the user sends a message
@cl.on_message
async def on_message(message: cl.Message):
    agent = cl.user_session.get("agent")
    messages = cl.user_session.get("messages")
    
    
    # Process uploaded files
    content = message.content
    if message.elements:
        file_paths = []
        for element in message.elements:
            # We check if it's an Excel file (by mime or name). Sometimes Chainlit misidentifies xlsx as zip.
            if element.name.endswith(".xlsx") or element.name.endswith(".xls") or element.name.endswith(".zip") or "excel" in element.mime.lower() or "spreadsheet" in element.mime.lower() or "zip" in element.mime.lower():
                file_paths.append(element.path)
        
        if file_paths:
            content += f"\n\n[System Note: The user has uploaded the following Excel file(s) for you to process. You can use their absolute paths: {', '.join(file_paths)}]"
            
    # Add the new user message to the history
    messages.append(HumanMessage(content=content))
    
    # Show a temporary "thinking" message in the UI
    ui_msg = cl.Message(content="Thinking and executing tools...", author="Assistant")
    await ui_msg.send()
    
    try:
        # We need a unique thread_id per user session to use LangGraph MemorySaver
        session_id = cl.user_session.get("id")
        
        # Log the user request functionally
        logging.info(f"Session {session_id} - User input received.")
        
        # Create a callback handler so Chainlit can render the intermediate steps
        cb = cl.AsyncLangchainCallbackHandler()
        
        # Execute the agent asynchronously passing the history, thread_id, and callbacks
        result = await agent.ainvoke(
            {"messages": messages},
            config={"configurable": {"thread_id": session_id}, "callbacks": [cb]}
        )
        
        logging.info(f"Session {session_id} - Agent execution successful.")
        
        # The result contains the updated history (includes internal tool steps and LLM response)
        updated_messages = result["messages"]
        cl.user_session.set("messages", updated_messages)
        
        # The final AI response is the last message in the list
        final_answer = updated_messages[-1].content
        
        # Update the temporary message with the actual response
        ui_msg.content = final_answer
        await ui_msg.update()
        
    except Exception as e:
        ui_msg.content = f"⚠️ **An error occurred in the Agent:**\n```python\n{str(e)}\n```"
        await ui_msg.update()
