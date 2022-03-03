import math
import copy
import textwrap

from CarryChain import CarryChain, template_code
from BinNumber import BinNumber


class BrentKung(object):
    @staticmethod
    def compute_fanout(num_bits=32, smart=True):
        """
        unaccounted chains are carry chains
        whose fanout have yet to be accounted for
        """
        fanout_count = {}
        unaccounted_chains = []

        for k in range(num_bits):
            carry_chain = CarryChain(k)
            # sub_chains = carry_chain.decompose()
            unaccounted_chains.append(carry_chain)
            fanout_count[carry_chain] = 1

        while len(unaccounted_chains) > 0:
            max_crit_length = 1
            for carry_chain in unaccounted_chains:
                max_crit_length = max(
                    max_crit_length, carry_chain.crit_length
                )

            if max_crit_length == 1:
                break

            new_unaccounted_chains = []

            for carry_chain in unaccounted_chains:
                if carry_chain.crit_length != max_crit_length:
                    new_unaccounted_chains.append(carry_chain)
                    continue

                sub_chains = carry_chain.decompose(smart=smart)

                for sub_chain in sub_chains:
                    if sub_chain not in fanout_count:
                        fanout_count[sub_chain] = 0

                    fanout_count[sub_chain] += 1

                    if sub_chain not in new_unaccounted_chains:
                        new_unaccounted_chains.append(sub_chain)

            unaccounted_chains = new_unaccounted_chains

        sorted_chains = [c[0] for c in sorted(
            fanout_count.items(), key=lambda c: c[1],
            reverse=True
        )]

        print('sorted carry chain fanouts:')
        for carry_chain in sorted_chains:
            print(
                f'[{fanout_count[carry_chain]}]',
                carry_chain.to_tuple(), 'depth =',
                carry_chain.crit_length,
                carry_chain.decompose(smart=smart),
                # carry_chain.decompose()
            )

        return fanout_count

    @staticmethod
    def make_z_jsim():
        jsim_lines = [
            '* nor outputs 1 if inputs are all 0'
        ]

        for k in range(0, 32, 4):
            name = f'XZNOR_L1{k//4}'
            jsim_lines.extend([
                f'{name} s{k} s{k+1} s{k+2} s{k+3} za{k//4} nor4'
            ])

        jsim_lines.extend([
            f'XZAND_L20 za[0] za[1] za[2] za[3] z0_to_15 nand4',
            f'XZAND_L21 za[4] za[5] za[6] za[7] z16_to_31 nand4',
            f'XZAND_L30 z0_to_15 z16_to_31 z nor2',
            ''
        ])

        return jsim_lines

    def build_jsim(self, num_bits=32, counter=1):
        fanout_counts = self.compute_fanout(num_bits=num_bits)
        jsim_lines = [
            template_code,
            '.subckt adder32 subtract xa[31:0] xb[31:0] s[31:0] z v n '
            '\n* p[31:0] c[31:0]',
            'XBUS_A xa[31:0] a[31:0] bus',
            'XSUBTRACT_BUFFER subtract subtract_buffer buffer_8',
            'XXOR_B xb[31:0] subtract_buffer#32 b[31:0] fast_xor',
            'XBUS_C0 g0_0 c0 bus',
            'XBUS_P0 p0 p0_0 bus',
            'XBUS_G0 g0 g0_0 bus',
            'XBUS_N s31 n bus', textwrap.dedent("""
                **********************************
                * v = ~a31*~b31*s31 + a31*b31*~s31
                * v = ~(~(~a31*~b31*31)*~(a31*b31*~s31))
                * v = NAND2(NAND3(~a31,~b31,s31), NAND3(a31,b31,~s31))
                **********************************
                XINV_A31 a31 a31_inv inverter
                XINV_B31 b31 b31_inv inverter 
                XINV_S31 s31 s31_inv inverter
                XV_NAND1 a31_inv b31_inv s31 v_nand_prod1 nand3
                XV_NAND2 a31 b31 s31_inv v_nand_prod2 nand3
                XV_NAND_OUT v_nand_prod1 v_nand_prod2 v nand2
                **********************************
            """), textwrap.dedent("""
                **********************************
                * generate single g, p bits
                * XG_GEN a[31:1] b[31:1] sg[31:1] and2
                * XP_GEN a[31:1] b[31:1] sp[31:1] xor2
                * XG_BUS sg[31:1] g[31:1]_[31:1] bus
                * XP_BUS sp[31:1] p[31:1]_[31:1] bus
                * special case for bit 0 with +1 from sub op
                **********************************
                * if two of a0, b0, or subtract are true, sg0 = 1
                **********************************
                * sg0 = a0*b0 + a0*s0 + b0*s0
                * = ~(~(a0*b0)*~(a0*s0)*~(b0*s0))
                * = NAND3(NAND2(a0,b0), NAND2(a0,s0), NAND2(b0,s0)
                **********************************
                XP_GEN0 a[0] b[0] subtract_buffer sp0 xor3
                XP_GEN0_BUS sp0 p0 bus
                XG_GEN0_SUB1 a[0] b[0] g0_nand_ab nand2
                XG_GEN0_SUB2 a[0] subtract_buffer g0_nand_as nand2
                XG_GEN0_SUB3 b[0] subtract_buffer g0_nand_bs nand2
                XG_GEN0 g0_nand_ab g0_nand_as g0_nand_bs sg0 nand3
                XG_GEN0_BUS sg0 g0_0 bus
                **********************************
            """)
        ]

        carry_chains = list(fanout_counts.keys())
        carry_chains = sorted(
            carry_chains, key=lambda c: (c.crit_length, c.end)
        )

        for carry_chain in carry_chains:
            if carry_chain.to_tuple() == (0, 0):
                continue

            fanout = fanout_counts[carry_chain]
            carry_lines, counter = carry_chain.build_jsim(
                counter=counter, fanout=fanout
            )

            jsim_lines.extend(carry_lines)
            counter += 1

        adder_lines = [
            f'XKHA0 p0 s0 bus',
            f'XKHA sp[31:1] c[30:0] s[31:1] fast_xor'
        ]

        jsim_lines.append('')
        jsim_lines.extend(adder_lines)
        jsim_lines.append('')
        jsim_lines.extend(self.make_z_jsim())
        jsim_lines.append('.ends')

        print('')
        print('* propogate jsim')
        jsim_code = '\n'.join(jsim_lines)
        print(jsim_code)

        filepath = 'checkoffs/fast_adder32_v2.jsim'
        with open(filepath, 'w') as fileobj:
            fileobj.write(jsim_code)

        print(f'* saved to {filepath}')

    @staticmethod
    def get_carries(a, b, num_bits=32, subtract=False):
        bin_a = BinNumber(a, num_bits=num_bits)
        orig_bin_b = BinNumber(b, num_bits=num_bits)
        bin_b = copy.deepcopy(orig_bin_b)
        bin_b = ~bin_b if subtract else bin_b

        p_cache, g_cache = {}, {}

        for bit_no in range(num_bits):
            chain = CarryChain(bit_no, start=0)
            G, P = chain.compute_carry(bin_a, bin_b, cin=subtract)
            g, p = chain.get_single_carry(bin_a, bin_b, cin=subtract)
            print(
                f'{chain}: G={G}, P={P}, g={g}, p={p}, '
                f'a[{bit_no}]={bin_a[bit_no]}, '
                f'b[{bit_no}]={bin_b[bit_no]}'
            )

            p_cache[bit_no] = P
            g_cache[bit_no] = G

        print('')
        print('carry chains')
        s0 = bin_a[0] ^ bin_b[0] ^ subtract
        print(f's0={s0}')
        s_bits = [s0]

        for bit_no in range(1, num_bits):
            # P = p_cache[bit_no]
            if bit_no == 0:
                sp = bin_a[bit_no] ^ bin_b[bit_no] ^ subtract
            else:
                sp = bin_a[bit_no] ^ bin_b[bit_no]

            prev_c = g_cache[bit_no - 1]
            digit = sp ^ prev_c
            print(
                f's{bit_no}={digit} '
                f'P{bit_no}={sp} C{bit_no-1}={prev_c}'
            )

            s_bits = [digit] + s_bits

        print(f's raw bits {s_bits}')
        bin_s = BinNumber(s_bits, num_bits=num_bits)

        print('')
        print('brent kung adder reuslts:')
        print(f'subtract = {subtract}')
        print(f'a = {bin_a}')
        print(f'b = {orig_bin_b}')
        print(f'adjusted b = {bin_b}')
        print(f's = {bin_s}')

    def test(self, num_bits=31):
        print(self.path_durations(31), self.critical_path_length(31))
        # print(path_durations(23))
        carry_out_paths = {}
        # path_dependencies = {}
        fanout_count = {}
        output_paths = []

        for k in range(num_bits):
            print(
                f'bit[{k}]',
                self.critical_path_length(k),
                self.path_durations(k),
                self.make_paths(k)
            )

            sub_paths = self.make_paths(k)
            carry_out_paths[k] = sub_paths

            for sub_path in sub_paths:
                # node, offset = sub_path
                if sub_path not in fanout_count:
                    fanout_count[sub_path] = 0
                    output_paths.append(sub_path)

                fanout_count[sub_path] += 1

        """
        for sub_path in fanout_count:
            print(sub_path, fanout_count[sub_path])
        """


if __name__ == '__main__':
    brent_kung = BrentKung()
    # fanout = brent_kung.compute_fanout()
    brent_kung.build_jsim()
    # brent_kung.get_carries(0x7FFFFFFF, 1)
    # print(fanout)