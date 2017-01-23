from lexer import Lexer, Token, TokenType
from typing import List
from io import TextIOBase
import codegen

class Expr:
    pass


class NumebrExpr(Expr):
    """Number expression, e.g. 5"""

    def __init__(self, value: float):
        self.value = value

    def __repr__(self):
        return f"NumebrExpr(value={repr(self.value)})"


class VariableExpr(Expr):
    """Variable expression, e.g. x"""

    def __init__(self, var_name: str):
        self.var_name = var_name

    def __repr__(self):
        return f"VariableExpr(var_name={repr(self.var_name)})"


class BinaryOpExpr(Expr):
    """Binary opeartion expression, e.g. x + y"""

    def __init__(self, op: str, lhs: Expr, rhs: Expr):
        self.op = op
        self.lhs = lhs
        self.rhs = rhs

    def __repr__(self):
        return f"BinaryOpExpr(op={repr(self.op)}, lhs={repr(self.lhs)}, rhs={repr(self.rhs)})"


class CallExpr(Expr):
    """Function call expression, e.g. f(x, y)"""

    def __init__(self, callee: str, args: List[Expr]):
        self.callee = callee
        self.args = args

    def __repr__(self):
        return f"CallExpr(callee={repr(self.callee)}, args={repr(self.args)})"


class Prototype:
    """Function prototype statement, e.g. extern def f(x y z)"""

    def __init__(self, name: str, args: List[str]):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"Prototype(name={repr(self.name)}, args={repr(self.args)})"


class Function:
    """Function statement. e.g e.g. def f(n) n + 1"""

    anon_counter = 0

    def __init__(self, proto: Prototype, body: Expr):
        self.proto = proto
        self.body = body

    def __repr__(self):
        return f"Function(proto={repr(self.proto)}, body={repr(self.body)})"

    @classmethod
    def create_anonymous(cls, body):
        proto = Prototype(f"_anon{cls.anon_counter}", [])
        cls.anon_counter += 1
        return cls(proto, body)


class ParseError(Exception):
    pass


class Parser:
    """Parser to parse text."""

    binop_precedence = {
        "<": 10,
        "+": 20,
        "-": 30,
        "*": 40,
    }

    def __init__(self, fp: TextIOBase):
        self.lexer = Lexer(fp)

    @property
    def cur_tok_precedence(self):
        if self.cur_tok.type != TokenType.OP:
            return -1 # not a binop
        if self.cur_tok.value in type(self).binop_precedence:
            return type(self).binop_precedence[self.cur_tok.value]
        else:
            return -1 # not a binop

    @property
    def cur_tok(self):
        return self.lexer.current_token

    def next_token(self):
        self.lexer.next_token()
        # print(self.cur_tok)
        return self.cur_tok

    def _parse_numberexpr(self):
        """Parse numberexpr, e.g. 5

        numberexpr ::= number"""
        expr = NumebrExpr(self.cur_tok.value)
        self.next_token()
        return expr

    def _parse_parenexpr(self):
        """Parse parenexpr, e.g. (1 + 3*x)

        parenexpr ::= '(' expr ')'"""
        self.next_token()  # eat (
        expr = self._parse_expr()
        if self.cur_tok.type != TokenType.OP or self.cur_tok.value != ")":
            raise ParseError(f"Expected ), got {self.cur_tok.value}")
        self.next_token()  # eat )
        return expr

    def _parse_identifier_expr(self):
        """Parse identifier expressions, e.g. var or f(x, y, z)

        identifierexpr
            ::= identifier
            ::= identifier '(' expression* ')'
        """
        identifier_name = self.cur_tok.value
        self.next_token()  # eat identifier name
        if self.cur_tok.value != '(':
            return VariableExpr(identifier_name)
        self.next_token()  # eat (

        args = []
        if self.cur_tok.value != ')':
            while True:
                args.append(self._parse_expr())
                if self.cur_tok.value == ')':
                    break
                if self.cur_tok.value != ',':
                    raise ParseError(f"Expected , or ) but got {self.cur_tok.value}")
                self.next_token()  # eat ,

        self.next_token()  # eat )

        return CallExpr(identifier_name, args)

    def _parse_primary(self):
        """Parse primary expresison.

        primary
            ::= numberexpr
            ::= parenexpr
            ::= identifierexpr
        """
        if self.cur_tok.type == TokenType.NUMBER:
            return self._parse_numberexpr()
        elif self.cur_tok.type == TokenType.IDENTIFIER:
            return self._parse_identifier_expr()
        elif self.cur_tok.type == TokenType.OP and self.cur_tok.value == '(':
            return self._parse_parenexpr()
        else:
            raise ParseError(f"Got unexpected token {self.cur_tok.value} in expresison")

    def _parse_expr(self):
        """Parse expression"""
        lhs = self._parse_primary()
        return self._parse_bin_op_rhs(lhs)

    def _parse_bin_op_rhs(self, lhs, min_precedence=0):
        while True:
            op_precedence = self.cur_tok_precedence
            if op_precedence < min_precedence:
                # x + a * b * c + d
                #       ^       ^ we are here
                #       | _parse_bin_op_rhs invoked here with lhs = a
                # lhs now is a * b * c
                return lhs
            # a + b * c * d
            #           ^ this case
            bin_op = self.cur_tok.value
            self.next_token()  # eat bin_op
            rhs = self._parse_primary()
            if op_precedence < self.cur_tok_precedence:
                # a + b + c * d
                #           ^ we are here
                #   ^ _parse_bin_op_rhs invoked here with lhs = a
                # lhs now is a + b
                # should pass rhs = c to _parse_bin_op_rhs as lhs to group as (c * d)
                rhs = self._parse_bin_op_rhs(rhs, op_precedence + 1)

            lhs = BinaryOpExpr(bin_op, lhs, rhs)

    def _parse_prototype(self):
        """Parse prototype expression.

        prototype
            ::= id '(' id* ')'
        """
        if self.cur_tok.type != TokenType.IDENTIFIER:
            raise ParseError("Expected identifier in function prototype")
        id_name = self.cur_tok.value
        self.next_token()  # eat id_name
        if self.cur_tok.type != TokenType.OP or self.cur_tok.value != '(':
            raise ParseError(f"Expexted ( got {self.cur_tok.value}")
        args = []
        while self.next_token().type == TokenType.IDENTIFIER:
            args.append(self.cur_tok.value)
            self.next_token()
            if self.cur_tok.value == ")":
                break
            if self.cur_tok.value != ",":
                raise ParseError(f", expected, got {self.cur_tok}")
        if self.cur_tok.type != TokenType.OP or self.cur_tok.value != ')':
            raise ParseError(f"Expexted ) got {self.cur_tok.value}")
        self.next_token()  # eat )
        return Prototype(id_name, args)

    def _parse_definition(self):
        """Parse definition expression.

        definition ::= 'def' prototype expression
        """
        self.next_token()  # eat def
        proto = self._parse_prototype()
        if self.cur_tok.value != ':':
            raise ParseError("Exprected : before function body")
        self.next_token()  # eat :
        body = self._parse_expr()
        return Function(proto, body)

    def _parse_extern(self):
        """Parse extern expression.

        extern ::= 'extern' prototype
        """
        self.next_token()  # eat 'extern'
        return self._parse_prototype()

    def _parse_top_level_expr(self):
        """Parse top level expression.

        toplevel ::= expression
        """
        return Function.create_anonymous(self._parse_expr())

    def parse(self):
        print("ready> ", end=None)
        self.next_token()
        generator = codegen.IRGenerator()
        while True:
            print("ready> ", end=None)
            if self.cur_tok.type == TokenType.EOF:
                break
            elif self.cur_tok.type == TokenType.DEF:
                node = self._parse_definition()
            elif self.cur_tok.type == TokenType.EXTERN:
                node = self._parse_extern()
            elif self.cur_tok.value == ';':
                self.next_token()
                continue
            else:
                node = self._parse_top_level_expr()
            print(repr(node))
            print(generator.generate(node))
        print(generator.module)
