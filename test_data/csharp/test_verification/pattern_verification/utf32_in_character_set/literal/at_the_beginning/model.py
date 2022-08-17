@verification
def match_something(text: str) -> bool:
    pattern = f"^prefix[\\U00010000a-zA-Z]suffix$"
    return match(pattern, text) is not None


__book_url__ = "dummy"
__book_version__ = "dummy"
__xml_namespace__ = "https://dummy.com"
