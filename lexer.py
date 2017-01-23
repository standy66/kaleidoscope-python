from typing import Callable
from enum import Enum
from io import TextIOBase

import sys


class TokenType(Enum):
    EOF = -1
    DEF = -2
    EXTERN = -3
    IDENTIFIER = -4
    NUMBER = -5
    OP = -6


class Token:
    GENERIC_TOKEN_TYPES = [TokenType.NUMBER, TokenType.IDENTIFIER, TokenType.OP]

    def __init__(self, token_type: TokenType, **kwargs):
        self.type = token_type
        if self.type in Token.GENERIC_TOKEN_TYPES:
            self.value = kwargs["value"]
        else:
            self.value = self.type.name

    def __str__(self):
        return repr(self)

    def __repr__(self):
        if self.type not in Token.GENERIC_TOKEN_TYPES:
            return f"Token(token_type={self.type})"
        else:
            return f"Token(token_type={self.type}, value={repr(self.value)})"


class Lexer:
    def __init__(self, fp: TextIOBase):
        self.fp = fp
        self.current_token : Token = None
        self.last_char = " "

    def next_token(self) -> Token:
        self._read_while(str.isspace)
        if self.last_char.isalpha():
            # identifier or def or extern
            word = self._read_while(str.isalnum)
            if word == "def":
                self.current_token = Token(TokenType.DEF)
            elif word == "extern":
                self.current_token = Token(TokenType.EXTERN)
            else:
                self.current_token = Token(TokenType.IDENTIFIER, value=word)
        elif self.last_char.isdigit() or self.last_char == ".":
            # number
            word = self._read_while(str.isdigit)
            if self.last_char == ".":
                word += "."
                self._eat(1)
                word += self._read_while(str.isdigit)
            self.current_token = Token(TokenType.NUMBER, value=float(word))
        elif self.last_char == "#":
            # comment until eof or eol
            self._read_while(lambda x: x not in ["\n", "\r", ""])
            self._eat(1)
        elif self.last_char == "":
            # EOF
            self.current_token = Token(TokenType.EOF)
        else:
            self.current_token = Token(TokenType.OP, value=self.last_char)
            self._eat(1)

        return self.current_token

    def _read_while(self, predicate: Callable[[str], bool]):
        word = ""
        while predicate(self.last_char):
            word += self.last_char
            self.last_char = self.fp.read(1)
        return word

    def _eat(self, n: int):
        self.last_char = self.fp.read(n)


def main():
    l = Lexer(sys.stdin)
    while True:
        tok = l.next_token()
        print(tok)
        if tok.type == TokenType.EOF:
            break


if __name__ == "__main__":
    main()
