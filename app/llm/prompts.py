def truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def split_text_into_chunks(
    text: str,
    chunk_chars: int,
    overlap_chars: int,
    max_chunks: int,
) -> tuple[list[str], bool]:
    normalized = text.strip()
    if not normalized:
        return [], False

    if chunk_chars <= 0 or len(normalized) <= chunk_chars:
        return [normalized], False

    chunks: list[str] = []
    start = 0
    safe_overlap = max(0, min(overlap_chars, chunk_chars - 1))
    last_end = 0

    while start < len(normalized) and len(chunks) < max_chunks:
        end = min(start + chunk_chars, len(normalized))
        last_end = end
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(0, end - safe_overlap)

    truncated = len(chunks) >= max_chunks and last_end < len(normalized)
    return chunks, truncated


def build_individual_summary_prompt(text: str) -> str:
    return f"""Você é um assistente especializado em resumir documentos.

Gere um resumo claro, objetivo e fiel ao conteúdo abaixo.

Regras:
- Não invente informações.
- Preserve nomes, datas, conceitos e números importantes.
- Organize o resumo em tópicos.
- Termine com uma conclusão curta.

Texto:
{text}
"""


def build_individual_chunk_prompt(text: str, index: int, total: int) -> str:
    return f"""Você está resumindo a parte {index} de {total} de um documento.

Gere um resumo parcial fiel, objetivo e útil para uma consolidação posterior.

Regras:
- Não invente informações.
- Preserve nomes, datas, conceitos e números importantes.
- Organize pontos centrais em tópicos curtos.
- Não escreva conclusão final.

Texto da parte:
{text}
"""


def build_individual_final_prompt(partial_summaries: str) -> str:
    return f"""Você receberá resumos parciais de um mesmo documento.

Gere um resumo final claro, objetivo e fiel ao conteúdo consolidado.

Inclua:
- Tema central do documento
- Pontos principais
- Dados, nomes, datas e números importantes
- Conclusão curta

Resumos parciais:
{partial_summaries}
"""


def build_integrated_summary_prompt(content: str) -> str:
    return f"""Você receberá conteúdos de múltiplos documentos.

Gere um resumo integrado, comparando e consolidando as informações.

Inclua:
- Tema geral dos documentos
- Pontos principais em comum
- Diferenças relevantes
- Informações complementares
- Conclusão final

Conteúdo:
{content}
"""


def build_integrated_chunk_prompt(content: str, index: int, total: int) -> str:
    return f"""Você está resumindo a parte {index} de {total} de um conjunto de documentos.

Gere um resumo parcial que preserve o documento de origem sempre que possível.

Regras:
- Não invente informações.
- Preserve diferenças e semelhanças relevantes.
- Preserve nomes, datas, conceitos e números importantes.

Conteúdo da parte:
{content}
"""


def build_integrated_final_prompt(partial_summaries: str) -> str:
    return f"""Você receberá resumos parciais de múltiplos documentos.

Gere um resumo integrado, comparando e consolidando as informações.

Inclua:
- Tema geral dos documentos
- Pontos principais em comum
- Diferenças relevantes
- Informações complementares
- Conclusão final

Resumos parciais:
{partial_summaries}
"""
