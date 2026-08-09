create table if not exists rag_chunks (
    id uuid primary key default gen_random_uuid(),
    parent_doc_id text not null,
    parent_title text not null,
    category text not null,
    source_url text not null,
    header_path text[] not null,
    part integer,                   -- null si la sección no se dividió
    content text not null,
    embedding vector(768) not null
);

create index if not exists rag_chunks_category_idx on rag_chunks (category);