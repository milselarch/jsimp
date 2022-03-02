import textwrap
import copy
import re


class Variable(object):
    def __init__(self, name: str, inverted=False):
        assert len(name) > 0
        pattern = re.compile('^[a-zA-Z]+[0-9]*$')
        assert pattern.match(name)

        self.name = name
        self.inverted = inverted

    def __eq__(self, other):
        if type(other) == Product:
            return self.to_product() == other

        return (
            (self.__class__ == other.__class__) and
            (self.inverted == other.inverted) and
            (self.name == other.name)
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

    def to_product(self):
        return Product([self])

    def to_sum(self):
        return self.to_product().to_sum()

    def __mul__(self, other):
        return self.to_sum() * other.to_sum()

    def __add__(self, other):
        return self.to_sum() + other.to_sum()

    def __xor__(self, other):
        return self.to_sum() ^ other.to_sum()

    def to_tuple(self):
        return self.name, self.inverted

    @property
    def sorted_expr(self):
        return self.expr


class Product(object):
    def __init__(self, variables):
        if type(variables) == str:
            variables = self.parse(variables)

        self.variables = variables

    def __eq__(self, other):
        # print(self.sorted_expr, other.sorted_expr)
        return self.sorted_expr == other.sorted_expr

    def to_product(self):
        return Product(variables=self.variables)

    def __add__(self, other):
        return self.to_sum() + other.to_sum()

    @property
    def sorted_vars(self):
        return sorted([var.expr for var in self.variables])

    @property
    def sorted_expr(self):
        return '*'.join(self.sorted_vars)

    @property
    def expr(self):
        return '*'.join([
            var.expr for var in self.variables
        ])

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.expr}')"

    @staticmethod
    def from_expr(string_expr):
        return Product(
            variables=Product.parse(string_expr)
        )

    @staticmethod
    def parse(expression):
        expression = expression.replace(' ', '')
        string_vars = expression.strip().split('*')
        variables = []

        for string_var in string_vars:
            if string_var[0] == '~':
                inverted = True
                string_var = string_var[1:]
            else:
                inverted = False

            variables.append(Variable(
                name=string_var, inverted=inverted
            ))

        return variables

    def simplify(self):
        var_mapping = {}

        for var in self.variables:
            name = var.name
            if name not in var_mapping:
                var_mapping[name] = var.inverted
            elif var_mapping[name] != var.inverted:
                return Product(variables=[])

            var_mapping[name] = var.inverted

        variables = []
        for name in var_mapping:
            inverted = var_mapping[name]
            variables.append(Variable(
                name=name, inverted=inverted
            ))

        return Product(variables=variables)

    def __mul__(self, other):
        if type(other) == type(self):
            combined = self.variables + other.variables
            return Product(variables=combined).simplify()
        else:
            return self.to_sum() * other.to_sum()

    def __invert__(self):
        return SumProducts(products=[
            (~var).to_product() for var in self.variables
        ])

    def __len__(self):
        return len(self.variables)

    def __xor__(self, other):
        return self.to_sum() ^ other.to_sum()

    def to_sum(self):
        return SumProducts(products=[self])

    @staticmethod
    def nand_jsim(
        gate1='a', gate2='b', output='z', counter=1, sw=8, sl=1
    ):
        return textwrap.dedent(f"""
            * {gate1} NAND {gate2}
            MPD{counter} {output} {gate1} {counter} 0 NENH sw={sw} sl={sl}
            MPD{counter+1} {counter} {gate2} 0 0 NENH sw={sw} sl={sl}
            MPU{counter} {output} {gate1} vdd vdd PENH sw={sw} sl={sl}
            MPU{counter+1} {output} {gate2} vdd vdd PENH sw={sw} sl={sl}
        """)

    @classmethod
    def not_jsim(cls, gate, *args, **kwargs):
        return cls.nand_jsim(gate, gate, *args, **kwargs)

    @staticmethod
    def pfet_jsim(
        gate='a', top='vdd', bottom='z',
        counter=1, sw=8, sl=1, bulk='vdd'
    ):
        return ' '.join([
            f'MPP{counter}', str(bottom),
            str(gate), str(top), bulk,
            'PENH', f'sw={sw}', f'sl={sl}'
        ]) + '\n'

    @staticmethod
    def nfet_jsim(
        gate='a', top='vdd', bottom='z',
        counter=1, sw=8, sl=1, bulk='0'
    ):
        return ' '.join([
            f'MPN{counter}', str(top),
            str(gate), str(bottom), bulk,
            'NENH', f'sw={sw}', f'sl={sl}'
        ]) + '\n'

    def make_jsim_chain(
        self, counter=1, start='vdd', output='z', use_pfet=True,
        sw=8, sl=1
    ):
        assert counter > 0  # 0 is considered as gnd
        start_counter = counter
        jsim_code = ""

        for k, var in enumerate(self.variables):
            # generate pullup jsim code
            top = counter
            bottom = top + 1

            if start == 'vdd':
                if k == 0:
                    top = start
                if k == len(self.variables) - 1:
                    bottom = output
            else:
                if k == 0:
                    top = output
                if k == len(self.variables) - 1:
                    bottom = start

            if var.inverted:
                jsim_code += self.pfet_jsim(
                    top=top, bottom=bottom, counter=counter,
                    gate=var.name, sw=sw, sl=sl
                )
            else:
                jsim_code += self.nfet_jsim(
                    top=bottom, bottom=top, counter=counter,
                    gate=var.name, sw=sw, sl=sl
                )

            counter += 1

        jsim_code = jsim_code.strip()
        steps = counter - start_counter
        return jsim_code, steps

    @staticmethod
    def inv_jsim(var, counter, inverter_name='inverter'):
        return f'XINV{counter} {var} {counter} {inverter_name}\n'

    @classmethod
    def and_jsim(
        cls, name1, name2, counter, output=None, use_nand=False
    ):
        output = counter if output is None else output

        if use_nand:
            gate_name = f'XNAND{counter}'
            jsim_line = f'{gate_name} {name1} {name2} {output} nand2\n'
            jsim_line += cls.inv_jsim(output, counter + 1)
            return jsim_line, counter + 1
        else:
            gate_name = f'XAND{counter}'
            jsim_line = f'{gate_name} {name1} {name2} {output} and2\n'
            return jsim_line, counter

    def make_jsim_and_chain(
        self, counter=1, output_name=None, use_nand=False
    ):
        output_node = self.variables[0]

        if len(self) == 1:
            if output_name is None:
                output_name = output_node.name

            if output_node.inverted:
                jsim_code = self.inv_jsim(output_name, counter)
                return jsim_code, counter, counter
            else:
                return '', output_name, counter

        elif len(self) == 2:
            var1 = self.variables[0]
            var2 = self.variables[1]
            var1 = var1.to_product()
            var2 = var2.to_product()

            subchain1 = var1.make_jsim_and_chain(
                counter + 1, use_nand=use_nand
            )
            var_jsim1, name1, counter = subchain1
            subchain2 = var2.make_jsim_and_chain(
                counter + 1, use_nand=use_nand
            )
            var_jsim2, name2, counter = subchain2

            if output_name is None:
                counter += 1
                output_name = counter

            jsim_code = var_jsim1 + var_jsim2
            and_line, counter = self.and_jsim(
                name1, name2, counter, output=output_name,
                use_nand=use_nand
            )

            jsim_code += and_line
            return jsim_code, output_name, counter

        p1 = Product(self.variables[:len(self)//2])
        p2 = Product(self.variables[len(self)//2:])
        sub_jsim1, out1, counter = p1.make_jsim_and_chain(
            counter + 1, use_nand=use_nand
        )
        sub_jsim2, out2, counter = p2.make_jsim_and_chain(
            counter + 1, use_nand=use_nand
        )

        counter += 1
        if output_name is None:
            counter += 1
            output_name = counter

        jsim_code = sub_jsim1 + sub_jsim2
        and_line, counter = self.and_jsim(
            out1, out2, counter, output_name, use_nand=use_nand
        )

        jsim_code += and_line
        return jsim_code, output_name, counter

    def make_jsim_inv_chain(
        self, counter=1, start='vdd', output='z', use_pfet=True,
        sw=8, sl=1
    ):
        assert counter > 0  # 0 is considered as gnd
        start_counter = counter
        jsim_code = ""

        for k, var in enumerate(self.variables):
            # generate pullup jsim code
            top = counter
            bottom = top + 1

            if start == 'vdd':
                if k == 0:
                    top = start
                if k == len(self.variables) - 1:
                    bottom = output
            else:
                if k == 0:
                    top = output
                if k == len(self.variables) - 1:
                    bottom = start

            if var.inverted:
                mid_node = counter + 2
                not_jsim = self.not_jsim(
                    var.name, output=mid_node, counter=counter,
                    sw=sw, sl=sl
                )
                jsim_code += not_jsim + '\n'
                counter = mid_node + 1

            if use_pfet:
                jsim_code += self.pfet_jsim(
                    top=top, bottom=bottom, counter=counter,
                    gate=var.name, sw=sw, sl=sl
                )
            else:
                jsim_code += self.nfet_jsim(
                    top=bottom, bottom=top, counter=counter,
                    gate=var.name, sw=sw, sl=sl
                )

            counter += 1

        jsim_code = jsim_code.strip()
        steps = counter - start_counter
        return jsim_code, steps


class SumProducts(object):
    def __init__(self, products):
        if type(products) == str:
            products = self.parse(products)

        self.products = products

    @staticmethod
    def parse(expression):
        expression = expression.replace(' ', '')
        string_products = expression.split('+')
        products = []

        for string_product in string_products:
            products.append(Product.from_expr(string_product))

        return products

    @staticmethod
    def from_expr(expression):
        return SumProducts(
            products=SumProducts.parse(expression)
        )

    @property
    def sorted_products(self):
        return sorted([
            product.sorted_expr for product in self.products
        ])

    @property
    def sorted_expr(self):
        return '+'.join(self.sorted_products)

    def __repr__(self):
        # print('REPR', self.products)
        expr = '+'.join([product.expr for product in self.products])
        return f"{self.__class__.__name__}('{expr}')"

    def to_sum(self):
        return SumProducts(products=self.products)

    def __add__(self, other):
        new_products = copy.deepcopy(other.products)

        for product in self.products:
            if product not in other.products:
                new_products.append(product)

        return SumProducts(products=new_products).simplify()

    def __mul__(self, other):
        new_products = []
        other_products = other.to_sum().products

        for p1 in self.products:
            for p2 in other_products:
                new_product = p1 * p2
                if new_product.to_sum() in new_products:
                    continue

                new_products.append(new_product)

        return SumProducts(products=new_products).simplify()

    def simplify(self):
        products = copy.deepcopy(self.products)
        products = sorted(products, key=lambda p: -len(p.sorted_expr))
        redundant_products = []

        for k in range(len(products)):
            redundant = False
            p1 = products[k]
            if len(p1) == 0:
                continue

            for i in range(k, len(products)):
                if k == i:
                    continue

                p2 = products[i]
                if len(p2) == 0:
                    continue

                if len(p1 * p2) == max(len(p1), len(p2)):
                    redundant = True

            if redundant and (p1 not in redundant_products):
                redundant_products.append(p1)

        new_products = []
        for product in self.products:
            if len(product) == 0:
                continue
            elif product not in redundant_products:
                new_products.append(product)

        return SumProducts(products=new_products)

    def __invert__(self):
        products = copy.deepcopy(self.products)
        # print('inverting', products)
        result = ~products[0]
        # print(0, result, products[0], ~products[0])

        for k in range(1, len(self.products)):
            # print(f'A{k}', result, ~products[k])
            result = result * ~products[k]
            # print(f'D{k}', result)
            # print(k, result, products[k], ~products[k])

        return result

    def __xor__(self, other):
        return self*~other + ~self*other

    def __len__(self):
        return len(self.products)

    @staticmethod
    def inv_jsim(*args, **kwargs):
        return Product.inv_jsim(*args, **kwargs)

    @classmethod
    def or_jsim(
        cls, name1, name2, counter, output=None, use_nor=False
    ):
        output = counter if output is None else output

        if use_nor:
            gate_name = f'XNOR{counter}'
            jsim_line = f'{gate_name} {name1} {name2} {output} nor2\n'
            jsim_line += cls.inv_jsim(output, counter + 1)
            return jsim_line, counter + 1
        else:
            output = counter if output is None else output
            line = f'XOR{counter} {name1} {name2} {output} or2\n'
            return line, counter

    def gate_jsim(self, *args, **kwargs):
        return self.make_jsim_or_chain(*args, **kwargs)[0]

    def make_jsim_or_chain(
        self, counter=1, output_name=None, nor_nand=False,
        debug=False
    ):
        if len(self) == 1:
            if output_name is None:
                counter += 1
                output_name = counter

            return self.products[0].make_jsim_and_chain(
                counter=counter, output_name=output_name,
                use_nand=nor_nand
            )

        elif len(self) == 2:
            p1 = self.products[0]
            chain_p1 = p1.make_jsim_and_chain(
                counter, use_nand=nor_nand
            )
            jsim_p1, out1, counter = chain_p1
            counter += 1

            p2 = self.products[1]
            chain_p2 = p2.make_jsim_and_chain(
                counter, use_nand=nor_nand
            )
            jsim_p2, out2, counter = chain_p2

            if output_name is None:
                counter += 1
                output_name = counter

            jsim_code = jsim_p1 + jsim_p2
            or_line, counter = self.or_jsim(
                out1, out2, counter, output=output_name,
                use_nor=nor_nand
            )

            jsim_code += or_line
            assert type(jsim_code) == str
            return jsim_code, output_name, counter

        s1 = SumProducts(self.products[:len(self)//2])
        s2 = SumProducts(self.products[len(self)//2:])
        sub_jsim1, out1, counter = s1.make_jsim_or_chain(
            counter + 1, nor_nand=nor_nand
        )
        sub_jsim2, out2, counter = s2.make_jsim_or_chain(
            counter + 1, nor_nand=nor_nand
        )

        counter += 1
        if output_name is None:
            counter += 1
            output_name = counter

        # print(sub_jsim1, sub_jsim2)
        jsim_code = sub_jsim1 + sub_jsim2
        or_line, counter = self.or_jsim(
            out1, out2, counter, output_name, use_nor=nor_nand
        )

        if debug:
            print(f'or line = {or_line}')

        jsim_code += or_line
        return jsim_code, output_name, counter

    def __eq__(self, other):
        return (
            self.to_sum().sorted_expr ==
            other.to_sum().sorted_expr
        )


if __name__ == '__main__':
    a1 = SumProducts('a*b + c')
    a2 = SumProducts('c + d')
    print(a1 + a2)
    print(~(a1 + a2))
    print(a1.gate_jsim())
    print('\n* ~(a1+a2) jsim')
    print((~(a1 + a2)).gate_jsim())

    a = Variable('a')
    b = Variable('b')
    print('\n* xor jsim')
    print(a*~b + ~a*b)
    print((a*~b + ~a*b).gate_jsim())

    print('\n* nand jsim')
    print(~(a*b))
    print((~(a*b)).gate_jsim())
