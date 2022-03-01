import math
import copy
import textwrap

from CarryChain import CarryChain, template_code


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
        jsim_lines = []
        for k in range(0, 32, 4):
            name = f'XZAND_L1{k//4}'
            jsim_lines.extend([
                f'{name} s{k} s{k+1} s{k+2} s{k+3} za{k//4} and4'
            ])

        jsim_lines.extend([
            f'XZAND_L20 za[0] za[1] za[2] za[3] z0_to_15 and4',
            f'XZAND_L21 za[0] za[1] za[2] za[3] z16_to_31 and4',
            f'XZAND_L30 z0_to_15 z16_to_31 z and2',
            ''
        ])

        return jsim_lines

    def build_jsim(self, num_bits=32, counter=1):
        fanout_counts = self.compute_fanout(num_bits=num_bits)
        jsim_lines = [
            template_code,
            '.subckt adder32 subtract a[31:0] xb[31:0] s[31:0] z v n '
            'p[31:0] c[31:0]',
            'XXOR_B xb[31:0] subtract#32 b[31:0] fast_xor',
            'XBUS_C0 subtract c0 bus',
            'XBUS_P0 0 p0 bus',
            'XBUS_G0 0 g0 bus',
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
            """),
        ]

        carry_chains = list(fanout_counts.keys())
        carry_chains = sorted(
            carry_chains, key=lambda c: (c.crit_length, c.end)
        )

        for carry_chain in carry_chains:
            carry_lines, counter = carry_chain.build_jsim(
                counter=counter
            )

            jsim_lines.extend(carry_lines)
            counter += 1

        adder_lines = [f'XKHA0 a0 b0 c0 s0 xor3']
        for k in range(1, num_bits):
            adder_lines.append(
                f'XKHA{k} p{k} c{k-1} s{k} xor2'
            )

        jsim_lines.append('')
        jsim_lines.extend(adder_lines)
        jsim_lines.append('')
        jsim_lines.extend(self.make_z_jsim())
        jsim_lines.append('.ends')

        print('')
        print('* propogate jsim')
        jsim_code = '\n'.join(jsim_lines)
        print(jsim_code)

        filepath = 'checkoffs/fast_adder32.jsim'
        with open(filepath, 'w') as fileobj:
            fileobj.write(jsim_code)

        print(f'* saved to {filepath}')

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
    # print(fanout)