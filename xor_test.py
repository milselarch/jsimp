from builder import *

result = None
for k in range(5):
    if result is None:
        result = Variable(f'a{k}')
        continue

    result ^= Variable(f'a{k}')

print(result)
print(len(result))