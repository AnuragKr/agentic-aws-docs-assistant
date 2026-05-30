import tiktoken


def get_token_encoder(model: str = "cl100k_base"):
    return tiktoken.get_encoding(model)


def count_tokens(text: str, encoder=None) -> int:
    enc = encoder or get_token_encoder()
    return len(enc.encode(text))
