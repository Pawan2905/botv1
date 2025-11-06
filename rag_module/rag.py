"""
Reusable RAG (Retrieval-Augmented Generation) module using LangGraph.
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, StateGraph

from api.bot_service import BotService

logger = logging.getLogger(__name__)

class RAGState:
    """Represents the state of the RAG graph."""
    def __init__(self):
        self.question: str = ""
        self.documents: List[Document] = []
        self.generation: str = ""

class RAG:
    """A LangGraph-based RAG pipeline."""

    def __init__(self):
        """Initializes the RAG module."""
        try:
            self.bot_service = BotService()
            self.retriever = self.bot_service.retriever
            self.llm = AzureChatOpenAI(
                azure_endpoint=self.bot_service.settings.azure_openai_endpoint,
                api_key=self.bot_service.settings.azure_openai_key,
                api_version=self.bot_service.settings.azure_openai_api_version,
                deployment_name=self.bot_service.settings.azure_openai_deployment,
                temperature=0,
            )
            self.graph = self._build_graph()
            logger.info("RAG module initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize RAG module: {e}")
            raise

    def _build_graph(self):
        """Builds the LangGraph RAG pipeline."""
        workflow = StateGraph(RAGState)

        # Define the nodes
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("grade_documents", self._grade_documents)
        workflow.add_node("generate", self._generate)
        workflow.add_node("web_search", self._web_search)

        # Build graph
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self._decide_to_generate,
            {
                "websearch": "web_search",
                "generate": "generate",
            },
        )
        workflow.add_edge("web_search", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    def _retrieve(self, state: RAGState) -> RAGState:
        """Retrieves documents from the vector store."""
        logger.info("---RETRIEVE---")
        question = state.question
        documents = self.retriever.invoke(question)
        return RAGState(question=question, documents=documents)

    def _grade_documents(self, state: RAGState) -> RAGState:
        """Grades the relevance of the retrieved documents."""
        logger.info("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
        # This is a simplified grading mechanism. A more robust implementation
        # would use an LLM to grade the documents.
        if not state.documents:
            logger.warning("No documents found.")
            state.documents = []
        return state

    def _decide_to_generate(self, state: RAGState) -> str:
        """Decides whether to generate an answer or try a web search."""
        logger.info("---ASSESS GRADED DOCUMENTS---")
        if not state.documents:
            logger.warning("---DECISION: NO DOCUMENTS, WEB SEARCH---")
            return "websearch"
        logger.info("---DECISION: GENERATE---")
        return "generate"

    def _generate(self, state: RAGState) -> RAGState:
        """Generates an answer using the retrieved documents."""
        logger.info("---GENERATE---")
        prompt = PromptTemplate(
            template="""
            Use the following pieces of context to answer the question at the end.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.
            
            Context: {context}
            
            Question: {question}
            
            Helpful Answer:
            """,
            input_variables=["context", "question"],
        )
        rag_chain = prompt | self.llm
        generation = rag_chain.invoke({
            "context": "\n\n".join([doc.page_content for doc in state.documents]),
            "question": state.question,
        })
        state.generation = generation.content
        return state

    def _web_search(self, state: RAGState) -> RAGState:
        """Performs a web search as a fallback."""
        logger.info("---WEB SEARCH---")
        # This is a placeholder for a web search implementation.
        state.documents = [Document(page_content="Web search results for: " + state.question)]
        return state

    def query(self, query_text: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Performs a RAG query."""
        logger.info(f"Performing RAG query: '{query_text}'")
        initial_state = RAGState(question=query_text)
        final_state = self.graph.invoke(initial_state)
        return {
            "response": final_state.generation,
            "sources": [doc.metadata for doc in final_state.documents],
        }
