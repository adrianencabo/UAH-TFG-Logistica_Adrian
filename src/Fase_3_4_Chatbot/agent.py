import os
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# Import the previously created tools
from alx_tools import alx_tools

# System prompt to give personality and context to the AI
SYSTEM_PROMPT = """You are a Senior Logistics Engineer and an AI Assistant expert in AnyLogistix.
Your goal is to help the user manage projects, list scenarios, run simulations, and apply scenario modifications.
You have access to tools that interact directly with the REST API of a local or remote AnyLogistix server.

Follow these rules:
1. Always verify which project the user wants to use and use 'open_and_get_project' to get its ID before interacting with its scenarios.
2. If the user asks to list scenarios, use 'get_scenarios_list'.
3. If the user asks to run a simulation, use 'run_simulation'. Note that it will return an experiment_result_id.
4. Always explain to the user briefly and clearly which tools you are going to use or have just used.
5. If an error occurs when invoking a tool, report it kindly and try to guide the user to solve it."""

def get_agent():
    # Initialize the free LLM using Gemini (Google).
    # Note: Make sure you have the GOOGLE_API_KEY environment variable set.
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)
    
    # Create a prebuilt ReAct agent from LangGraph.
    # This agent automatically manages the "Thought -> Action (Tool) -> Observation -> Response" loop.
    agent_executor = create_react_agent(
        llm, 
        tools=alx_tools,
        state_modifier=SYSTEM_PROMPT
    )
    
    return agent_executor
