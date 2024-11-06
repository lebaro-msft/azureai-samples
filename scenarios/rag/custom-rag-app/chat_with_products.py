# <imports-and-config>
import os
import logging
from opentelemetry import trace
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from config import LOGGING_HANDLER, LOGGING_LEVEL, ASSET_PATH, enable_telemetry
from get_product_documents import get_product_documents

# use the app telemetry settings to configure logging for this module
logger = logging.getLogger(__name__)
logger.addHandler(LOGGING_HANDLER)
logger.setLevel(LOGGING_LEVEL)

# initialize an open telemetry tracer
tracer = trace.get_tracer(__name__)

# create a project client using environment variables loaded from the .env file
project = AIProjectClient.from_connection_string(
    conn_str=os.environ['AIPROJECT_CONNECTION_STRING'],
    credential=DefaultAzureCredential()
)

# create a chat client we can use for testing
chat = project.inference.get_chat_completions_client()
# </imports-and-config>

# <chat-function>
from azure.ai.inference.prompts import PromptTemplate

@tracer.start_as_current_span(name="chat_with_products")
def chat_with_products(messages : list, context : dict = {}) -> dict:
    documents = get_product_documents(messages, context)

    # do a grounded chat call using the search results
    grounded_chat_prompt = PromptTemplate.from_prompty(
        os.path.join(ASSET_PATH, "grounded_chat.prompty")
    )

    system_message = grounded_chat_prompt.render(documents=documents, context=context)
    response = chat.complete(
        model=os.environ["CHAT_MODEL"],
        messages=system_message + messages,
        **grounded_chat_prompt.parameters,
    )
    logger.info(f"💬 Response: {response.choices[0].message}")

    # Return a chat protocol compliant response
    response = {
        "message": response.choices[0].message,
        "context": context
    }

    return response
# </chat-function>

# <test-function>
if __name__ == "__main__":
    import argparse
    
    # load command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--query", type=str, 
        help="Query to use to search product", 
        default="I need a new tent for 4 people, what would you recommend?"
    )
    parser.add_argument(
        "--enable-telemetry", action="store_true", 
        help="Enable sending telemetry back to the project", 
    )
    args = parser.parse_args()

    if (enable_telemetry):
        enable_telemetry(True)

    # run chat with products
    response = chat_with_products(messages=[
        {"role": "user", "content": args.query}
    ])
# </test-function>