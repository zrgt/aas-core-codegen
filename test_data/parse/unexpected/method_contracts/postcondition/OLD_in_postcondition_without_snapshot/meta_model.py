class Something:
    @ensure(lambda OLD: len(OLD.lst) > 0)
    def do_something(self, x: int, y: int) -> int:
        pass


__book_url__ = "dummy"
__book_version__ = "dummy"
__xml_namespace__ = "https://dummy.com"
