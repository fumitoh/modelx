"""
============
Loan example
============

Calculate either the annual payment amount or payback period for a
given principal and interest rate.
To solve for the annual payment amount, a payback period must be inputted,
to solve for the payback period, an annual payment amount must be inputted.
This example demonstrate input value having a priority over the cells formula.
"""
from modelx import *

space = new_model().new_space()
space.principal = 10000
space.interest_rate = 0.03


def annual_payment():
    """How much amount per payment for a given payback period."""
    n = payback_period
    return principal / pv_payments(n)


def pv_payments(n):
    """Present value of repayments of 1 for n years."""
    if n == 1:
        return 1 / (1 + interest_rate)
    else:
        return pv_payments(n - 1) + 1 / (1 + interest_rate) ** n


def payback_period():
    """Payback period for a given annual payment"""
    n = 1
    while annual_payment * pv_payments(n) < principal:
        n += 1
    return n


# Define multiple cells at once from function definitions.
[defcells(func) for func in [payback_period,
                             annual_payment,
                             pv_payments]]

# Give payback period and solve for annual payment.
space.payback_period = 13
print(space.annual_payment())

# Instead, Give annual payment and solve for payback period.
space.payback_period.clear() # Clear the input and all dependent cell values.
space.annual_payment = 500
print(space.payback_period())





