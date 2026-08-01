# Learning Note: RAG

RAG means Retrieval-Augmented Generation.

## Main Idea
1. Split documents into chunks.
2. Convert chunks into embeddings.
3. Store embeddings in a vector database.
4. When a question arrives, retrieve relevant chunks.
5. Send retrieved context plus the question to an LLM.
6. The LLM answers using the retrieved context.

## Benefits
- Can answer based on personal documents.
- Reduces hallucination.
- Useful for project knowledge bases.
- Useful for study notes.
