import copy


class BitsNumber(object):
    def __init__(self, num_or_bits, num_bits=32):
        assert num >= 0

        if type(num_or_bits) is int:
            self.bits = self.fill_bits(num, num_bits)
        else:
            assert len(num_or_bits) == num_bits
            self.bits = copy.deepcopy(num_or_bits)

    def __invert__(self):
        bits = copy.deepcopy(self.bits)
        print('old bits', bits)
        for k in range(len(bits)):
            bits[k] = 1 - bits[k]

        inv_bin_no = self.__class__(
            num_or_bits=bits, num_bits=self.num_bits
        )

        return inv_bin_no

    @staticmethod
    def fill_bits(num, num_bits=32):
        bits = [0] * num_bits
        bin_num = bin(num)

        for k in range(num_bits):
            digit = bin_num[-1-k]
            if digit == 'b':
                break

            digit = int(digit)
            bits[-1-k] = digit

        return bits