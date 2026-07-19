from __future__ import annotations

import re


class DocumentChunker:
    """
    Splits long document text into overlapping sliding-window semantic chunks.

    Maintains section context by prepending global document metadata
    (e.g., original filename, classification) to every generated chunk.
    This guarantees the LLM understands "where" the text belongs.
    """

    def __init__(
        self,
        chunk_size: int = 800,       # characters (~150-200 words)
        chunk_overlap: int = 150,     # characters overlap to prevent boundary splitting
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(
        self,
        text: str,
        document_metadata: dict | None = None,
    ) -> list[dict]:
        """
        Splits text into chunks and returns a list of dictionaries with:
        - text: the chunk content (including prepended context)
        - clean_text: the original text chunk without prepended context
        - index: the chunk position index (0-based)
        - metadata: combined document metadata for filter queries
        """
        if not text:
            return []

        document_metadata = document_metadata or {}
        filename = document_metadata.get("filename", "unknown_document")
        doc_type = document_metadata.get("document_type", "unknown_type")

        # Global header appended to every chunk for context preservation
        global_header = f"[Doc: {filename} | Type: {doc_type}]\n"

        # Split text by paragraphs first to attempt preservation of boundaries
        paragraphs = re.split(r"\n{2,}", text)
        chunks: list[dict] = []
        current_chunk: list[str] = []
        current_length = 0
        chunk_idx = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If a single paragraph is larger than chunk_size, split by sentences
            if len(para) > self.chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    if current_length + len(sentence) > self.chunk_size:
                        if current_chunk:
                            # Finalize current chunk
                            clean_text = " ".join(current_chunk)
                            chunks.append(self._create_chunk_dict(
                                clean_text=clean_text,
                                global_header=global_header,
                                index=chunk_idx,
                                metadata=document_metadata,
                            ))
                            chunk_idx += 1

                            # Keep overlap content
                            overlap_content = current_chunk[-1] if len(current_chunk[-1]) < self.chunk_overlap else current_chunk[-1][-self.chunk_overlap:]
                            current_chunk = [overlap_content, sentence]
                            current_length = len(overlap_content) + len(sentence)
                        else:
                            current_chunk = [sentence]
                            current_length = len(sentence)
                    else:
                        current_chunk.append(sentence)
                        current_length += len(sentence)
            else:
                if current_length + len(para) > self.chunk_size:
                    if current_chunk:
                        # Finalize
                        clean_text = "\n".join(current_chunk)
                        chunks.append(self._create_chunk_dict(
                            clean_text=clean_text,
                            global_header=global_header,
                            index=chunk_idx,
                            metadata=document_metadata,
                        ))
                        chunk_idx += 1

                        # Keep overlap content
                        overlap_content = current_chunk[-1] if len(current_chunk[-1]) < self.chunk_overlap else current_chunk[-1][-self.chunk_overlap:]
                        current_chunk = [overlap_content, para]
                        current_length = len(overlap_content) + len(para)
                    else:
                        current_chunk = [para]
                        current_length = len(para)
                else:
                    current_chunk.append(para)
                    current_length += len(para)

        # Catch remaining text
        if current_chunk:
            clean_text = "\n".join(current_chunk)
            chunks.append(self._create_chunk_dict(
                clean_text=clean_text,
                global_header=global_header,
                index=chunk_idx,
                metadata=document_metadata,
            ))

        return chunks

    def _create_chunk_dict(
        self,
        clean_text: str,
        global_header: str,
        index: int,
        metadata: dict,
    ) -> dict:
        return {
            "text": f"{global_header}{clean_text}",
            "clean_text": clean_text,
            "index": index,
            "metadata": {
                **metadata,
                "chunk_index": index,
            }
        }
