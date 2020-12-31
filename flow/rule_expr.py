# encoding: utf-8

"""
规则解析：
- {{疾病史 == 糖尿病)}}  # 疾病史是个数组
- {{疾病史 != 糖尿病}}   # 评估
- {{(评估 == 慢性肾脏病G1 or 评估 == 慢性肾脏病G2) and 每日蛋白质摄入量 >= 0.6 and 每日蛋白质摄入量 <= 0.8}}
- {{BMI >20 and BMI < 24}}
- {{运动方式 >= 中等强度 and  每周运动时长 >= 150}}

预防规则说明:
1、规则编辑时采用mustache模板语法，即{{疾病史 != 糖尿病}}样例
2、规则执行表达式运算，运算结果为boolean类型，即true或false
3、支持 and 、or、not等逻辑运算符
4、支持括号表示运算优先级
5、支持>、< 、>=、<=、==、!= 6个比较运算符
6、>、< 、>=、<= 支持数值类型比较
6、==、!= 除支持字符串值和数值外，还支持扩展的集合和元素比较，即如果左变量为列表时，表示为包含和不包含关系
7、支持枚举类型自动转换，例如{{运动方式 >= 中等强度}},会自动把“中等强度”转换为枚举数值2("")
8、字符串可以不用引号括起来

固定输入：
1、参数字典
2、函数字典
3、枚举定义字典：国标

变量输入:
1、参数对象

"""
import os
import sys

pythonPath = os.path.join(os.path.dirname(__file__), '..')
if pythonPath not in sys.path:
    sys.path.append(pythonPath)
import ast

VAR_MAP = {}
FUNC_MAP = {}
enums = {}


def binary_ops_eq_ext(left, right):
    if isinstance(left, list):
        return right in left
    return left == right


def binary_ops_neq_ext(left, right):
    if isinstance(left, list):
        return right not in left
    return left != right


class RuleExpr(ast.NodeVisitor):
    """
    Transformer that safely parses an expression, disallowing any complicated
    FUNC_MAP or control structures (inline if..else is allowed though).
    """

    # Boolean operators
    # The AST nodes may have multiple ops and right comparators, but we
    # evaluate each op individually.
    _boolean_ops = {
        ast.And: lambda left, right: left and right,
        ast.Or: lambda left, right: left or right
    }

    # Binary operators
    _binary_ops = {
        ast.Add: lambda left, right: left + right,
        ast.Sub: lambda left, right: left - right,
        ast.Mult: lambda left, right: left * right,
        ast.Div: lambda left, right: left / right,
        ast.Mod: lambda left, right: left % right,
        ast.Pow: lambda left, right: left ** right,
        ast.LShift: lambda left, right: left << right,
        ast.RShift: lambda left, right: left >> right,
        ast.BitOr: lambda left, right: left | right,
        ast.BitXor: lambda left, right: left ^ right,
        ast.BitAnd: lambda left, right: left & right,
        ast.FloorDiv: lambda left, right: left // right
    }

    # Unary operators
    _unary_ops = {
        ast.Invert: lambda operand: ~operand,
        ast.Not: lambda operand: not operand,
        ast.UAdd: lambda operand: +operand,
        ast.USub: lambda operand: -operand
    }

    # Comparison operators
    # The AST nodes may have multiple ops and right comparators, but we
    # evaluate each op individually.
    _compare_ops = {
        ast.Eq: binary_ops_eq_ext,  # 自定义，支持集合操作
        ast.NotEq: binary_ops_neq_ext,  # 自定义，支持集合操作
        ast.Lt: lambda left, right: left < right,  # 自定义，支持集合操作
        ast.LtE: lambda left, right: left <= right,
        ast.Gt: lambda left, right: left > right,  # 自定义，支持集合操作
        ast.GtE: lambda left, right: left >= right,
        ast.Is: lambda left, right: left is right,
        ast.IsNot: lambda left, right: left is not right,
        ast.In: lambda left, right: left in right,
        ast.NotIn: lambda left, right: left not in right
    }

    def __init__(self, expr_node, env, expr=None):
        self.env = env
        self.expr_node = expr_node
        self.expr = expr
        self.warn_factors = []
        self.extent = []

    def exec(self):
        try:
            if self.expr_node is None:
                self.expr_node = ast.parse(self.expr)
            return self.visit(self.expr_node)
        except SyntaxError as error:
            error.text = self.expr
            raise error
        except Exception as error:
            error_type = error.__class__.__name__
            if len(error.args) > 2:
                line_col = error.args[1:]
            else:
                line_col = (1, 0)

            error = SyntaxError('{}: {}'.format(error_type, error.args[0]),
                                ('filename',) + line_col + (self.expr,))
            raise error

    def visit_Module(self, node):
        """
        Visit the root module node.
        """

        if len(node.body) != 1:
            if len(node.body) > 1:
                lineno = node.body[1].lineno
                col_offset = node.body[1].col_offset
            else:
                lineno = 1
                col_offset = 0

            raise SyntaxError('Exactly one expression must be provided',
                              ('', lineno, col_offset, ''))

        return self.visit(node.body[0])

    def visit_Expr(self, node):
        """
        Visit an expression node.
        """

        return self.visit(node.value)

    def visit_BoolOp(self, node):
        """
        Visit a boolean expression node.
        """

        op = type(node.op)
        func = self._boolean_ops[op]
        result = func(self.visit(node.values[0]), self.visit(node.values[1]))
        for value in node.values[2:]:
            result = func(result, self.visit(value))

        return result

    def visit_BinOp(self, node):
        """
        Visit a binary expression node.
        """

        op = type(node.op)
        func = self._binary_ops[op]
        return func(self.visit(node.left), self.visit(node.right))

    def visit_UnaryOp(self, node):
        """
        Visit a unary expression node.
        """

        op = type(node.op)
        func = self._unary_ops[op]
        return func(self.visit(node.operand))

    def visit_Compare(self, node):
        """
        Visit a comparison expression node.
        """
        result = self.visit(node.left)
        for operator, comparator in zip(node.ops, node.comparators):
            op = type(operator)
            func = self._compare_ops[op]
            left_v = result
            right_v = self.visit(comparator)
            # 特殊处理1，如果左值为None，则默认为true
            if result is None:
                return True

            result = func(result, right_v)
            # 特殊处理2，记录下结果为false的因子，用于后面推导
            if not result:
                # self.warn_factors[f'{node.left.id}({left_v})_{op.__name__}_{str(right_v)}']=1
                self.warn_factors.append(node.left.id)
                if op == ast.Gt or op == ast.GtE:
                    self.extent.append("偏低")
                elif op == ast.Lt or op == ast.LtE:
                    self.extent.append("偏高")
                else:
                    self.extent.append("")
                # self.
        return result

    def visit_Num(self, node):
        """
        Visit a literal number node.
        """

        # pylint: disable=no-self-use
        return node.n

    def visit_Name(self, node):
        """
        Visit a named variable node.
        """
        if node.id in self.env:
            return self.env[node.id]
        else:
            print(f'unkown ({node.id})')
        return node.id


if __name__ == '__main__':
    env = {
        "评估": ["慢性肾脏病G1", "ASCVD高危"],
        "饮食": [
            {"食物名称": "花卷", "摄入量": 200},
            {"食物名称": "木薯", "摄入量": 100},
            {"食物名称": "冬瓜", "摄入量": 200},
        ],
        "吸烟情况": "戒烟",
        "体重": 66,
        "性别": "男",
        "是否怀孕": "否",
        "年龄": 60,
        "BMI": 22,
        "疾病史": ["高血压", "糖尿病"],
        "饮酒情况": "喝酒",
        "睡眠总时长": 8,
        "心理情况": "良好",
        "饮酒信息": {"每日饮酒量": 330, "每周饮酒频率": 5, "种类": "啤酒"},
        "运动": [
            {"运动名称": "下楼", "运动频率": 3, "运动时长": 30},
            {"运动名称": "乒乓球", "运动频率": 3, "运动时长": 30},
        ],
        "慢性肾脏病分期": 2,  # 诊断模型提供
        "腰围": 88,
        "每日步数": 7000,
    }


    # e = RuleExpr(None,env,"(评估 == 慢性肾脏病G1 or 评估 == 慢性肾脏病G2) and 每日蛋白质摄入量 >= 每日钙推荐摄入量 and 每日蛋白质摄入量 <= 0.8")
    def test(s):
        e = RuleExpr(None, env, s)
        print('      结果==>', e.exec(), "警告因子==>", e.warn_factors, e.extent)


    # test("每日蛋白质摄入量 >= 每日钙推荐摄入量")
    # test("(评估 == 慢性肾脏病G1 or 评估 == 慢性肾脏病G2) and 每日蛋白质摄入量 >= 每日钙推荐摄入量 and 每日蛋白质摄入量 <= 0.8")
    # test("评估 != ASCVD高危 and 每日蛋白质摄入量>= 每日钙推荐摄入量 and 每日蛋白质摄入量 > 0.8")
    # test("(每日运动时长 >= 30 and 每周运动次数 >= 3) or (年龄 <= 44 and (每周最大运动强度 == 高强度 or 每周最大运动强度 == 极高强度) and 每周运动次数 >= 2)")
    # str = "每日蔬菜 > 40"
    # str = str.replace("\xa0"," ")
    # print(str)
    # for element in str.split(" "):
    #     print(element)
    # # for element in str:
    # #     print(element.split("\t"))
    # test("每日蛋白质摄入量>0.8")
    test("体重 > 900")
