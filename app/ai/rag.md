# RAG Flow

## Input Sources

* PDF
* TXT
* Raw Text (Swagger, FAQ, Product Info, Policy)
* JSON From Front

---

## Ingestion Flow

```text
Input
↓
Extract Text
↓
Chunking
↓
Embedding
↓
Save Documents
```

---

## Chunking Features

* Paragraph-aware splitting
* Overlap (120 chars)
* Heading detection
* Heading injection into content
* Metadata generation

Example:

```text
หัวข้อ: ค่าติดตั้ง

ค่าติดตั้งเริ่มต้น 1,000 บาท
```

---

## Stored Metadata

```text
shop_id
document_id
chunk_index
source
file_type
heading
embedding
```

---

## Retrieval Flow

```text
Question
↓
Embedding
↓
Similarity Search
↓
Top Chunks
↓
LLM
↓
Answer
```


Cache เก็บ semantic cache history เก่า 10-20 -> sum -> long term memory