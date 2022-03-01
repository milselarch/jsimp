import math
import textwrap
from typing import List

template_code = textwrap.dedent("""
.include "nominal.jsim"
.include "stdcell.jsim"
.include "test_debug.jsim"

* .subckt adder32 subtract xa[31:0] b[31:0] s[31:0] z v n p[31:1]

**********************************
* .03 + .03 + .02 = .08
**********************************
.subckt fast_xor a b xor_out
XOR_INV_A a a_inv inverter
XOR_INV_B b b_inv inverter
XOR_NAND1 a b_inv xor_pt1 nand2
XOR_NAND2 a_inv b xor_pt2 nand2
XOR_NAND3 xor_pt1 xor_pt2 xor_out nand2
.ends

.subckt fast_and4 a b c d out
XAND4_NAND4 a b c d out_inv nand4
XAND4_INV out_inv out inverter
.ends

.subckt fast_and a b out
XAND2_NAND2 a b out_inv nand2
XAND2_INV out_inv out inverter 
.ends

* we're using this as our half adder unit
* it uses 5 nand gates, but logic depth is only 2
**********************************
.subckt fast_xor3 a b c xor_out
XOR3_INV_A a a_inv inverter_2
XOR3_INV_B b b_inv inverter_2
XOR3_INV_C c c_inv inverter_2
XOR3_NAND1 a b c np1 nand3
XOR3_NAND2 a b_inv c_inv np2 nand3
XOR3_NAND3 a_inv b c_inv np3 nand3
XOR3_NAND4 a_inv b_inv c np4 nand3
XOR3_NAND_ALL np1 np2 np3 np4 xor_out nand4
.ends

.subckt xor3 a b c xor_out
XXOR_PT1 a b xor_ab xor2
XXOR_PT2 xor_ab c xor_out xor2
.ends

* propogate carry g
**********************************
* g_new = gp + pp * gn
* = ~((~gp)*~(pp*gn))
* = NAND2(INV(gp), NAND2(pp, gn))
**********************************
.subckt prop_g gp pp gn g_new
* XPROP_NAND_PROP pp gn nand_prod nand2
* XPROP_INV gp gp_inv inverter
* XPROP_NAND_END gp_inv nand_prod g_new nand2
XTEST1 pp gn out1 and2
XTEST2 out1 gp g_new or2
.ends
**********************************
""")


class CarryChain(object):
    def __init__(self, end, start=0):
        assert end >= start
        self.end = end
        self.start = start

    def __repr__(self):
        name = self.__class__.__name__
        return f'{name}({self.end}, {self.start})'

    def __key(self):
        return self.end, self.start

    def to_tuple(self):
        return self.end, self.start

    @property
    def is_single(self):
        return self.start == self.end

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.to_tuple() == other.to_tuple()

    def build_jsim(self, counter=1):
        c, n = counter, self.end
        end, start = self.to_tuple()
        new_g = f'g{start}_{end}'
        new_p = f'p{start}_{end}'

        if self.is_single:
            assert start == end

            return [
                f'* tie sg{n} to {new_g}',
                # f'XG{c} a{n} b{n} sg{n}_inv nand2',
                # f'XG{c}_INV sg{n}_inv sg{n} inverter_4',
                f'XG{c}_INV a{n} b{n} sg{n} and2',
                f'XP{c} a{n} b{n} sp{n} fast_xor',
                f'XBUS_G{c} sg{n} {new_g} bus',
                f'XBUS_P{c} sp{n} {new_p} bus',
                f''
            ], c

        sub_chain, prev_chain = self.decompose(smart=True)
        prev_end, prev_start = prev_chain.to_tuple()
        sub_end, sub_start = sub_chain.to_tuple()

        prev_g = f'g{prev_start}_{prev_end}'
        prev_p = f'p{prev_start}_{prev_end}'
        sub_g = f'g{sub_start}_{sub_end}'
        sub_p = f'p{sub_start}_{sub_end}'

        jsim_lines = [
            f'* carry propagate from bit {start} to bit {end}',
            f'XCHAIN_G{c} {prev_g} {prev_p} {sub_g} {new_g} prop_g',
            f'XCHAIN_P{c}_INV {prev_p} {sub_p} {new_p}_inv nand2',
            f'XCHAIN_P{c} {new_p}_inv {new_p} inverter_4'
        ]

        if start == 0:
            # create input carry bit
            jsim_lines.extend([
                f'* create input carry bit {end}',
                f'XBUS_C{c} {new_g} c{end} bus',
                F'XBUS_P{c} {new_p} p{end} bus'
            ])

        jsim_lines.append('')
        return jsim_lines, c

    @property
    def crit_length(self):
        return self.critical_length

    @property
    def critical_length(self):
        return self.critical_path_length(
            self.end, offset=self.start
        )

    @classmethod
    def make_paths(cls, node, offset=0):
        if offset == node:
            return [(node, offset)]

        diff = node - offset
        # print('DIFF', diff, node, offset)
        p_diff = 2 ** math.floor(math.log(diff, 2))
        # print('PDIFF', p_diff, node, offset)

        bootstrap = p_diff + offset
        sub_path = cls.make_paths(node, offset=bootstrap)
        if node - bootstrap == 1:
            sub_path = [(node, bootstrap)]

        path = sub_path + [(bootstrap - 1, offset)]
        return path

    def smart_decompose(self):
        sub_chains = self.decompose(smart=False)
        if len(sub_chains) <= 2:
            return sub_chains

        # reduce sub chains to just 2 chains
        # this helps in reducing jsim connections generated
        sub_chains[0].start = sub_chains[-2].start
        sub_chains = [sub_chains[0], sub_chains[-1]]
        # print(sub_chains)
        return sub_chains

    def decompose(self, smart=False):
        if smart is True:
            return self.smart_decompose()

        return self.decompose_chains(self.end, self.start)

    @classmethod
    def decompose_chains(cls, node, offset=0):
        raw_chains = cls.make_paths(node, offset=offset)
        carry_chains = []

        for raw_chain in raw_chains:
            node, offset = raw_chain
            carry_chains.append(CarryChain(node, offset))

        return carry_chains

    @classmethod
    def critical_path_length(cls, node, offset=0):
        lengths = cls.path_lengths(node, offset)
        # print('crit', (node, offset), lengths)
        total_length = lengths[0]

        for k in range(len(lengths) - 1):
            next_length = lengths[k + 1]
            total_length = max(total_length, next_length)
            # it takes 1 unit of time to combine two paths
            total_length += 1

        return total_length

    @classmethod
    def path_lengths(cls, node, offset=0):
        if node == offset:
            return [1]

        lengths: list[int] = []
        path = cls.make_paths(node, offset)
        # print('path', (node, offset), path)

        for point in path:
            sub_node, sub_offset = point
            sub_length = cls.critical_path_length(
                sub_node, sub_offset
            )
            lengths.append(sub_length)

        return lengths