from builder import *

result = None
for k in range(32):
    var = SumProducts(f'ra{k}')
    if result is None:
        result = var
        continue

    result += var

print(result.gate_jsim(output_name='ra_or_out'))
print(len(result))