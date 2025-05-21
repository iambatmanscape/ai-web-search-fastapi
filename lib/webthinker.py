from langchain.prompts import PromptTemplate
import logging
from typing import Dict, Any
from fastapi import Request
from .oprah import webscraper
from langchain_openai import OpenAIEmbeddings
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
import asyncio
import time
from langchain_openai import OpenAI
from langchain_ollama import OllamaLLM
load_dotenv('.env')
from os import getenv
from ast import literal_eval
from async_lru import alru_cache



logging.basicConfig(level=logging.INFO)


async def gather_extracted_info(self, question, final_results):
    semaphore = asyncio.Semaphore(5)  # max 5 concurrent tasks
    total_extracted_info = ""

    async def safe_extract(result):
        async with semaphore:
            return await self.extract_information(question, result)

    tasks = [safe_extract(result) for result in final_results]
    extracted_info_list = await asyncio.gather(*tasks)
    total_extracted_info = "\n\n".join(extracted_info_list)
    return total_extracted_info

class WebThinkerAgent:
    def __init__(self, llm):
        self.llm = llm
        self.setup_prompts()
        
    def setup_prompts(self):
        
        self.extraction_prompt = PromptTemplate(
    template="""You are a precise information extraction system. Your primary task is to extract ONLY the most relevant and recent factual information from the provided web search results that directly answers the user's query.

        Question:
        {question}

        Web Search Results:
        {search_results}

        Instructions:
        1. FIRST analyze the query to identify key constraints:
        - Location (e.g., city, region, country)
        - Timeframe (e.g., "latest", "past month", "in 2023")
        - Core topic or subject

        2. LOCATION FILTERING:
        - If the query is location-specific, ONLY include information directly relevant to that location.

        3. RECENCY FILTERING:
        - If the query requests recent or latest information, ONLY include content from the past 30 days unless the query specifies a broader range.
        - Prioritize events or data from the past 7 days.

        4. RELEVANCE FILTERING:
        - Discard unrelated or tangential information.
        - Only include content that directly addresses the user's query.
        - Location, timeframe, and core topic should be the primary focus.

        5. EXTRACTION GUIDELINES:
        - Extract concrete facts, events, data points, or official announcements.
        - Attribute each fact to its source when available (e.g., "According to [Source]").
        - Extract complete information, that convey the full context of the event or data point.

        6. NEVER:
        - Fabricate or infer beyond the provided content.
        - Include editorials, opinions, or speculation unless explicitly requested.
        - For latest news, only include the most recent and relevant information.
        - Today's date is 20 may 2025

        Format your response using:
        - Clear categorization by theme if applicable (e.g., "PRODUCT UPDATES:", "LEGAL:", "EVENTS:", "ANNOUNCEMENTS:")
        - List most recent items first within each category

        Relevant Information:""",
            input_variables=["question", "search_results"],
        )

        self.join_prompt = PromptTemplate(
        template="""You are given a list of web search results. Your task is to create a comprehensive and factual summary of the most relevant information found in these results. 
        Expand on each key point clearly and thoroughly. Do not omit important details, and avoid shortening or generalizing the content. 
        Ensure that all information included comes directly from the provided search results — do not infer, assume, or fabricate any facts.
        Ensure that all information is relevant to the user's query and is presented in a clear and organized manner.

        \nQuestion:\n{question}
        \nWeb Search Results:\n{search_results}
        \n\nDetailed Summary:""",
            input_variables=["question", "search_results"]
        )

    async def extract_information(self, question: str, search_results: str) -> str:
        """Extract relevant information from search results."""
        try:
            extraction_chain = self.extraction_prompt | self.llm
            extracted_info = await extraction_chain.ainvoke({"question": question, "search_results": search_results})
            return extracted_info
        except Exception as e:
            logging.error(f"Error extracting information: {e}")
            return f"Error extracting information: {str(e)}"

    async def search(self, question: str, request: Request) -> Dict[str, Any]:
        """Conduct a full research session using the Think-Search-Draft approach."""
        
        try:
            search_results = await webscraper(question, request)
            # logging.info(f"Search results: {search_results}")
            search_results = [result for result in search_results if result is not None and result.strip() != ""]
            # logging.info(f"Search results for query '{query}': {search_results}")
            vector_store,_ = get_vector_store()
            if search_results:
                metadata = [{"source": "some_source"} for _ in search_results]
                
                vector_store.add_texts(
                    texts=search_results,
                    metadatas=metadata
                )
            
            # vector_store.add_texts(search_results, metadatas=[{"source": "someting"}])
            final_results = vector_store.similarity_search(f"{question}", k=int(getenv('NUMBER_OF_POINTS')))
            vector_store._documents = []
            vector_store.index.reset()

            if final_results:
                final_results = [doc.page_content for doc in final_results]
            else:
                final_results = ["No relevant information found."]

            # total_extracted_info = await self.extract_information(question, "\n\n".join(final_results))

            total_extracted_info = await gather_extracted_info(self, question, final_results)
            # logging.info(f"Extracted information: {total_extracted_info}")

            finalized_chain = self.join_prompt | self.llm
            finalized_summary = await finalized_chain.ainvoke({"question": question, "search_results": total_extracted_info})

            return {
                "search_results": search_results,
                "extracted_info": finalized_summary
            }

        except Exception as e:
            logging.error(f"Error in research process: {e}")
            return {
                "search_results": [],
                "extracted_info": []
            }
        


def get_vector_store():
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(
        api_key=getenv('OPENAI_API_KEY')
    )
    
    # Compute embedding dimension
    try:
        dim = len(embeddings.embed_query("hello world"))
    except Exception as e:
        logging.error(e)
        raise

    # Create FAISS index
    index = faiss.IndexFlatL2(dim)

    # Create and return vector store
    vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )
    
    return vector_store, embeddings

@alru_cache(ttl=literal_eval(getenv('TTL_CACHE')))
async def search_web(request:Request,query: str) -> Dict[str, Any]:
    """Search the web for a given query."""
    # Initialize the WebThinkerAgent
    webthinker: WebThinkerAgent = request.app.state.webthinker
    results = await webthinker.search(query,request)
    return results['extracted_info']






if __name__ == "__main__":
    # from langchain_ollama import OllamaLLM
    import asyncio
    from langchain_openai import OpenAI
    from langchain_ollama import OllamaLLM
    from langchain_groq import ChatGroq
    # client = OllamaLLM(
    #     model=getenv('EXTRACTION_MODEL'),
    #     temperature=0.1,
    #     base_url=getenv('OLLAMA_URL')
    # )
    if literal_eval(getenv('use_ollama')):
        client = OllamaLLM(
            model=getenv('EXTRACTION_MODEL'),
            temperature=0.1,
            base_url=getenv('OLLAMA_URL')
        )
    elif literal_eval(getenv('use_groq')):
        client = ChatGroq(
            model=getenv('EXTRACTION_MODEL'),
            temperature=0.1,
            api_key=getenv('GROQ_API_KEY')
        )
    else:
        client = OpenAI(
            model=getenv('EXTRACTION_MODEL'),
            temperature=0.1,
            api_key=getenv('OPENAI_API_KEY'),
            max_tokens=2000
        )

    # logging.info(f"Client invoke: {client.invoke('hi')}")

    webthinker = WebThinkerAgent(client)
    # question = ""
    question = "Latest news lucknow"
    t1 = time.time()
    results = asyncio.run(webthinker.search(question))
    t2 = time.time()
    logging.info(f"Time taken for search: {t2-t1:.2f}s")
    # logging.info(f"Search results: {results['search_results']}")
    logging.info(f"Extracted information: {results['extracted_info']}")



