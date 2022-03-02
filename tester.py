from builder import *

a = Variable('a')
b = Variable('b')
c = Variable('c')

xor = ~a*b + a*~b
print('xor', xor, xor.products)
print(~xor)

xor2 = a ^ b
print('xor2', xor2, xor2.products)
print(~xor2)

print('')
print('xor jsim')
print(xor.gate_jsim())

print('')
print('xnor jsim')
print((~xor).gate_jsim())