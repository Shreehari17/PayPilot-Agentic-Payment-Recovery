from typing import TypedDict,Annotated
from langgraph.graph import START,END,StateGraph
import operator
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage,SystemMessage
from langgraph.prebuilt import ToolNode
from agent.tools import search_knowledge_base,web_search,calculate
from dotenv import load_dotenv
from agent.audit import log_investigation

from agent.memory import save_conversation_memory,search_conversation_memory
load_dotenv()

from agent.commerce_tools import (
    get_payment_analytics,
    get_payment_recovery_guidance
)

tools = [
    search_knowledge_base,
    web_search,
    calculate,
    get_payment_analytics,
    get_payment_recovery_guidance
]
tool_node=ToolNode(tools)


llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0
)
llm_with_tools=llm.bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[list,operator.add]

def agent_node(state:AgentState):
    response=llm_with_tools.invoke(state["messages"])
    return {"messages":[response]}
def should_continue(state:AgentState):
    last_message=state["messages"][-1]
    if hasattr(last_message,"tool_calls") and last_message.tool_calls:
        return "use_tool"
    return "end"
    

builder=StateGraph(AgentState)
builder.add_node("agent",agent_node)
builder.add_node("tools",tool_node)
builder.add_edge(START,"agent")
builder.add_edge("tools","agent")


builder.add_conditional_edges(
    "agent",
    should_continue,
    {"use_tool":"tools","end":END}
    )
agent = builder.compile()

SYSTEM_PROMPT = """
You are PayPilot, an agentic payment recovery copilot for merchants.

You have access to five tools:

1. get_payment_analytics
   - Use this for payment performance investigations.
   - It provides real transaction metrics, payment-method breakdowns,
     failure reasons, and revenue at risk.

2. calculate
   - Use this for arithmetic and quantitative calculations.
   - Use it when deriving a value from tool-provided numbers.

3. get_payment_recovery_guidance
   - Use this AFTER payment analytics identifies a specific failure pattern.
   - Pass the specific issue to retrieve relevant recovery guidance.
   - Treat the returned guidance as the authoritative source for recovery actions.

4. search_knowledge_base
   - Use for general internal knowledge questions.

5. web_search
   - Use when current external information is required.

IMPORTANT RULES:

- For payment degradation or revenue-risk investigations, start with
  get_payment_analytics.
- Do not invent payment metrics or financial figures.
- Tool-provided metrics may be reported directly.
- Use calculate for derived arithmetic when necessary.
- Base recovery recommendations only on evidence returned by the tools.
- Do not invent thresholds, SLAs, timeout values, retry limits, percentages,
  deadlines, targets, owners, or operational policies.
- If a specific value or policy is not provided by the tools, explicitly say
  that it is not specified.
- Never claim that money was actually recovered.
- You provide recommendations; you do not execute real financial transactions.
- Do not claim that a recovery action was executed unless a tool explicitly
  reports that it was executed.
- Keep recovery recommendations bounded by the retrieved guidance.
- Clearly distinguish observed facts from recommended actions.
"""

if __name__ == "__main__":
    messages = [
        SystemMessage(content=SYSTEM_PROMPT)
    ]

    while True:
        user_input = input("You: ")

        if user_input.lower() == "exit":
            save_conversation_memory(messages, "default")
            break

        past_memories = search_conversation_memory(
            user_input,
            "default"
        )

        if past_memories:
            messages.append(
                SystemMessage(
                    content=f"Relevant context from past conversation:\n{past_memories}"
                )
            )

        messages.append(HumanMessage(content=user_input))

        result = agent.invoke({
        "messages": messages
        })

        messages = result["messages"]

        tools_used = []

        for message in result["messages"]:
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tool_call in message.tool_calls:
                    tools_used.append(tool_call["name"])

        final_response = result["messages"][-1].content

        log_investigation(
        user_query=user_input,
        tools_used=tools_used,
        final_response=final_response
        )

        print("Agent:", final_response)