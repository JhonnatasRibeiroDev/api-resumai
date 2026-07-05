def truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


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
