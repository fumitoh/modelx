from modelx import *

space = new_model().new_space()

# print('start assign')

space.principal = 10000

# print("""start next
# """)

space.interest_rate = 0.03
# print(space._impl.namespace.data)

# space._impl.print_members()

# print(space._impl.namespace)

def annual_payment():
    n = payback_period
    return principal / pv_payments(n)


def pv_payments(n):

    if n == 1:
        return 1 / (1 + interest_rate)

    else:
        return pv_payments(n - 1) + 1 / (1 + interest_rate) ** n


def payback_period():
    n = 1
    while annual_payment * pv_payments(n) < principal:
        # print(pv_n_payments(n))
        n += 1

    return n


[defcells(func) for func in [payback_period,
                             annual_payment,
                             pv_payments]]

space.payback_period = 13
# space.annual_payment = 1000

print(space.payback_period())
print(space.annual_payment())
# print(space._impl.print_members())




