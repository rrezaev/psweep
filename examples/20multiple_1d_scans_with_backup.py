#!/usr/bin/env python3

# second run: extend study with more 'b' values
#
# run 10multiple_1d_scans_with_backup.py first

import random
from itertools import product
from psweep import psweep as ps


def func(pset):
    return {'result': random.random() * pset['a'] * pset['b']}


if __name__ == '__main__':

    print("second run")

    const = {'a': 11111,
             'b': 55555}

    params = []
    disp_cols = []

    values = dict(b=[88,99])

    for study,seq in values.items():
        params_1d = ps.seq2dicts(study, seq)
        this_params = ps.loops2params(product(params_1d, [{'study': study}]))
        this_params = [ps.merge_dicts(const, dct) for dct in this_params]
        params += this_params
        disp_cols.append(study)

    disp_cols += ['_run_id']
    df = ps.run(func, params, backup_script=__file__, backup_calc_dir=True,
                verbose=disp_cols)
    print(df[disp_cols + ['result']])
