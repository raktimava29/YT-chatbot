from langchain_text_splitters import RecursiveCharacterTextSplitter

def split_transcript(transcript:str, chunk_size:int = 1000, chunk_overlap:int = 200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    chunks = splitter.create_documents([transcript])
    return chunks