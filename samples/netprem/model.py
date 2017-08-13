import sys
import os

from modelx import *
from modelx.io.excel import read_range

this_dir = os.path.dirname(sys.modules[__name__].__file__)
sample_file = this_dir + "/../data/SampleActuarialModel1.xlsx"

def mortality_keys(table):

    def sex(col):
        return 'M' if col == 0 else 'F'

    for age, rates in enumerate(table):
        for col, rate in enumerate(rates):
            yield (('sex', sex(col)),
                   ('age', age)), rate.value


mortality_table = read_range(sample_file, "MortalityTable2")

def policy_keys(table):

    for policy in table:
        yield policy[0].value, tuple(attr.value for attr in policy)


policy_data = read_range(sample_file, "PolicyData", None, policy_keys)


model = create_model()
policy = model.create_space()
policy.create_cells_from_module('samples.netprem.policy')
policy.create_cells_from_module('samples.netprem.lifetable')
policy.create_cells_from_module('samples.netprem.commutation_funcs')
policy.policy_data = policy_data
policy.mortality_table = mortality_table

@defcells(space=policy)
def qx(x):
    if sex == 1:
        return mortality_table[(x, 0)]
    else:
        return mortality_table[(x, 1)]

policies = model.create_space(bases=policy,
                              factory=lambda policy_id: {'bases': get_self()})

for policy_id in range(1, 13):
    policy = policies[policy_id]
    print(policy.net_prem(),
          policy.pv_benefit(),
          policy.pv_annuity())





