import re


class Variable(object):
    def __init__(self, name: str, inverted=False):
        assert len(name) > 0
        pattern = re.compile('^[a-zA-Z]+[0-9]*$')
        assert pattern.match(name)

        self.name = name
        self.inverted = inverted

    def __eq__(self, other):
        if type(other) == Variable:
            return (
                (self.name == other.name) and
                (self.inverted == other.inverted)
            )

    @property
    def expression(self):
        if self.inverted:
            return f"~{self.name}"
        else:
            return f"{self.name}"

    @property
    def expr(self):
        return self.expression

    def __repr__(self):
        class_name = self.__class__.__name__
        return f"{class_name}('{self.expression}')"

    def __invert__(self):
        return self.__class__(
            name=self.name, inverted=not self.inverted
        )

    def __mul__(self, other):
        return self.to_expr() * other.to_expr()

    def __add__(self, other):
        return self.to_expr() + other.to_expr()

    def __xor__(self, other):
        return self.to_expr() ^ other.to_expr()

    def to_expr(self):
        return Expression(data=[self])

    def to_tuple(self):
        return self.name, self.inverted

    @property
    def sorted_expr(self):
        return self.expr


class Expression(object):
    def __init__(self, data, inverted=False):
        assert len(data) >= 1
        assert type(data) is not str
        self.inverted = inverted
        self.data = data

    def invert_inplace(self):
        self.inverted = not self.inverted

    def __invert__(self):
        new_expr = Expression(data=self.data, inverted=self.inverted)
        new_expr.invert_inplace()
        return new_expr

