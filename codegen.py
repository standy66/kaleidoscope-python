import llvmlite.ir
import parser

from llvmlite.ir import IRBuilder, Module, Value, Context, Constant, FunctionType, Function, Block

DoubleType = llvmlite.ir.DoubleType()

class CodegenError(Exception):
    pass


class IRGenerator:
    def __init__(self):
        self.builder = IRBuilder()
        self.module = Module()

    def search_functions(self, name, num_args):
        for function in self.module.functions:
            if function.name == name and len(function.args) == num_args:
                return function
        return None

    def generate(self, node, lookup={}):
        if isinstance(node, parser.VariableExpr):
            if node.var_name in lookup:
                return lookup[node.var_name]
            else:
                raise CodegenError(f"Undefined variable {node.var_name}")
        elif isinstance(node, parser.NumebrExpr):
            return DoubleType(node.value)
        elif isinstance(node, parser.BinaryOpExpr):
            lhs = self.generate(node.lhs, lookup)
            rhs = self.generate(node.rhs, lookup)
            if node.op == "+":
                return self.builder.fadd(lhs, rhs, name="addtmp")
            elif node.op == "-":
                return self.builder.fsub(lhs, rhs, name="subtmp")
            elif node.op == "<":
                tmp = self.builder.fcmp_unordered('<', lhs, rhs, name="tmpcmp")
                return self.builder.uitofp(tmp, DoubleType, name="booltmp")
            elif node.op == "*":
                return self.builder.fmul(lhs, rhs, name="multmp")
            else:
                return CodegenError(f"Invalid binary operation {node.op}")
        elif isinstance(node, parser.CallExpr):
            fn = self.search_functions(node.callee, len(node.args))
            if fn is None:
                return CodegenError(f"Function {node.name} of {len(node.args)} arguments not found")
            args = []
            for arg in node.args:
                args.append(self.generate(arg, lookup))
            return self.builder.call(fn, args, name="calltmp")
        elif isinstance(node, parser.Prototype):
            fn_type = FunctionType(DoubleType, [DoubleType] * len(node.args))
            fn = Function(self.module, fn_type, node.name)
            fn.linkage = ""  # this means external linkage
            for arg, arg_name in zip(fn.args, node.args):
                arg.name = arg_name
            return fn
        elif isinstance(node, parser.Function):
            fn = self.search_functions(node.proto.name, len(node.proto.args))
            if fn is None:
                fn = self.generate(node.proto, lookup)
            if len(fn.blocks) > 0:
                raise CodegenError(f"Cannot redefine function {node.proto}")
            bb = fn.append_basic_block("entry")
            self.builder.position_at_end(bb)
            lookup_add = {arg.name: arg for arg in fn.args}
            ret = self.generate(node.body, lookup={**lookup, **lookup_add})
            self.builder.ret(ret)
            return fn
        else:
            print("WATAFAK")
            print(type(node))
            print(parser.Function)
        print("End")
