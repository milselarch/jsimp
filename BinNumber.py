import math
import copy


class BinNumber(object):
    def __init__(
        self, num, num_bits=32, hex_val=None
    ):
        if num < 0:
            negative = True
            num = num + 2 ** (num_bits - 1)
        else:
            negative = False

        self.num_bits = num_bits
        self.bits = self.fill_bits(
            num, num_bits=num_bits, negative=negative
        )

        if hex_val is not None:
            assert hex_val == self.to_decimal(
                self.bits, False
            )

    @property
    def is_negative(self):
        return self.bits[0] == 1

    def to_decimal(self, bits=None, complement=True):
        number = 0
        if bits is None:
            bits = self.bits

        bits = copy.deepcopy(bits)[::-1]

        for k, bit in enumerate(bits):
            bit_val = bit * 2 ** k
            if complement and (k == len(bits) - 1):
                bit_val *= -1

            number += bit_val

        return number

    @property
    def value(self):
        return self.to_decimal()

    def __add__(self, other):
        if isinstance(other, self.__class__):
            other = other.value

        new_val = self.value + other
        print('add val', self, self.value, other, new_val)
        new_bin_no = self.__class__(
            num=new_val, num_bits=self.num_bits
        )

        try:
            assert new_bin_no.value == new_val
        except AssertionError as e:
            print('VAL_MISMATCH', new_bin_no.value, new_val)
            raise e

        return new_bin_no

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            other = other.value

        new_val = self.value - other
        print('new val', new_val)
        return self.__class__(
            num=new_val, num_bits=self.num_bits
        )

    def __invert__(self):
        bits = copy.deepcopy(self.bits)
        print('old bits', bits)
        for k in range(len(bits)):
            bits[k] = 1 - bits[k]

        # print('new bits', bits)
        value = self.to_decimal(bits)
        inv_bin_no = self.__class__(
            num=value, num_bits=self.num_bits
        )

        print(f'inv_value', value, inv_bin_no)
        return inv_bin_no

    def __neg__(self):
        return ~self + 1

    @staticmethod
    def fill_bits(num, num_bits=32, negative=False):
        str_num = bin(num)
        bits = [0] * num_bits

        for k, digit in enumerate(str_num[::-1]):
            if digit == 'b':
                break

            digit = 1 if digit == '1' else 0
            bits[-1-k] = digit

        if negative:
            assert bits[0] == 0
            bits[0] = 1

        return bits

    def to_hex(self, num=None):
        if num is None:
            num = self.to_decimal(complement=False)

        str_num = hex(num)[2:]
        length = math.ceil(self.num_bits / 4)
        padded_hex = '0x' + str_num.zfill(length)
        return padded_hex

    def __repr__(self):
        name = self.__class__.__name__
        num = self.to_decimal()
        return (
            f'{name}({num}, '
            f'num_bits={self.num_bits}, '
            f'hex_val={self.to_hex()}'
            ')'
        )


if __name__ == '__main__':
    an = BinNumber(0)
    bn = BinNumber(0x55555555)
    cn = BinNumber(0x80000000)
    print(an, bn, cn)
    print('inv', ~bn)
    # print('inv inv', ~~bn)
    print('negative', -bn)
    print('SUB', an-bn)

