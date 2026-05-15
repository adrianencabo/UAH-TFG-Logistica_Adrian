import os
import chainlit as cl
from langchain_core.messages import HumanMessage
from agent import get_agent

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
        content="Hello! 👋 I am your Intelligent AnyLogistix Assistant.\n\n"
                "I can help you to:\n"
                "📦 Open projects and view scenarios.\n"
                "⚙️ Run simulations and export results.\n"
                "🤖 Modify scenarios based on logical decisions.\n\n"
                "Make sure to set your `OPENAI_API_KEY` or `GOOGLE_API_KEY` in your environment variables. How can I help you today?"
    ).send()

# This function runs every time the user sends a message
@cl.on_message
async def on_message(message: cl.Message):
    agent = cl.user_session.get("agent")
    messages = cl.user_session.get("messages")
    
    # Add the new user message to the history
    messages.append(HumanMessage(content=message.content))
    
    # Show a temporary "thinking" message in the UI
    ui_msg = cl.Message(content="Processing and interacting with AnyLogistix...")
    await ui_msg.send()
    
    try:
        # Execute the agent asynchronously passing the history
        result = await agent.ainvoke({"messages": messages})
        
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
