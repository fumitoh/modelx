from modelx import *

from modelx.io.excel import read_xlrange

def mortality_keys(table):

    def sex(col):
        return 'M' if col == 0 else 'F'

    for age, rates in enumerate(table):
        for col, rate in enumerate(rates):
            yield (('sex', sex(col)),
                   ('age', age)), rate.value


mortality_table = read_xlrange("SampleActuarialModel1.xlsx",
                               "MortalityTable2",
                               None,
                               mortality_keys)

model = create_model()
policy = model.create_space(
    factory=lambda id: {'bases': get_self()})

policy.create_cells_from_module('samples.sample_lifetable')
policy.create_cells_from_module('samples.sample_actuarialmodel')
policy.mortality_table = mortality_table

print(policy)

# policies = [model.create_space(name="Policy" + str(id)) for id in range(1, 13)]
#
# for id, policy in enumerate(policies, 1):
#
#
#
#     if id < 7:
#         @defcells(space=policy)
#         def qx(x):
#             return mortality_table[(('sex', 'M'), ('age', x))]
#     else:
#         @defcells(space=policy)
#         def qx(x):
#             return mortality_table[(('sex', 'F'), ('age', x))]
#
#     if id >= 7:
#         id -= 6
#
#     print(policy.netprem(id * 10, 70 - id * 10) * 100000)


@defcells(space=policy)
def qx(x):

    if id < 7:
        return mortality_table[(('sex', 'M'), ('age', x))]

    else:
        return mortality_table[(('sex', 'F'), ('age', x))]

for id in range(1, 13):

    idx = id if id < 7 else id - 6

    print(policy(id).netprem(idx * 10, 70 - idx * 10))

# print(policy(1).to_dataframe())





