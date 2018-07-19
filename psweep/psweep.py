from io import IOBase
import multiprocessing as mp
from functools import partial
import os, copy, uuid, pickle
import pandas as pd

pj = os.path.join


dtype_err_msg = ("reading and writing the json with dtype other than object "
                 "will allow Pandas typecasting, which we very much dislike")


def df_json_write(df, name, **kwds):
    assert (df.dtypes == object).all(), dtype_err_msg
    orient = kwds.pop('orient', 'records')
    makedirs(os.path.dirname(name))
    df.to_json(name, double_precision=15, orient=orient, **kwds)


def df_json_read(name, **kwds):
    orient = kwds.pop('orient', 'records')
    dtype = kwds.pop('dtype', object)
    if dtype is not object:
        raise ValueError(dtype_err_msg)
    return pd.io.json.read_json(name, 
                                precise_float=True, 
                                orient=orient, 
                                dtype=dtype,
                                **kwds)


def pickle_read(fn):
    with open(fn, 'rb') as fd:
        return pickle.load(fd)


def pickle_write(df, fn):
    makedirs(os.path.dirname(fn))
    with open(fn, 'wb') as fd:
        pickle.dump(df, fd)


# https://github.com/elcorto/pwtools
def makedirs(path):
    if not path.strip() == '':
        os.makedirs(path, exist_ok=True)


# https://github.com/elcorto/pwtools
def fullpath(path):
    return os.path.abspath(os.path.expanduser(path))


def seq2dicts(name, seq):
    """
    >>> seq2dicts('a', [1,2,3])
    [{'a': 1}, {'a': 2}, {'a': 3}]
    """
    return [{name: entry} for entry in seq]


def itr(func):
    def wrapper(*args):
        if len(args) == 1:
            return func(args[0])
        else:
            return func(args)
    return wrapper


@itr
def merge_dicts(args):
    dct = {}
    for entry in args:
        dct.update(entry)
    return dct


# stolen from pwtools and adapted for python3
def is_seq(seq):
    if isinstance(seq, str) or \
       isinstance(seq, IOBase) or \
       isinstance(seq, dict):
        return False
    else:
        try:
            _ = iter(seq)
            return True
        except:
            return False


def flatten(seq):
    for item in seq:
        if not is_seq(item):
            yield item
        else:
            for subitem in flatten(item):
                yield subitem

@itr
def loops2params(loops):
    return [merge_dicts(flatten(entry)) for entry in loops]


# tmpsave: That's cool, but when running in parallel, we loose the ability to
# store the whole state of the study calculated thus far. For that we would
# need an extra thread that periodically checks for or -- even better -- gets
# informed by workers about finished work and collects the so-far written temp
# results into a global df -- maybe useful for monitoring progress.

def worker_wrapper(pset, worker, tmpsave=False, verbose=False, run_id=None,
                   calc_dir=None):
    assert run_id is not None
    assert calc_dir is not None
    pset_id = str(uuid.uuid4())
    # for printing only
    df_row = pd.DataFrame([pset], dtype=object)
    if isinstance(verbose, bool) and verbose:
        print(df_row)
    elif is_seq(verbose):
        print(df_row[verbose])
    _pset = copy.deepcopy(pset)
    update = {'_run_id': run_id,
              '_pset_id': pset_id,
              '_calc_dir': calc_dir,
              }
    _pset.update(update)
    _pset.update(worker(_pset))
    df_row = pd.DataFrame([_pset], dtype=object)
    if tmpsave:
        fn = pj(calc_dir, 'tmpsave', run_id, pset_id + '.json')
        df_json_write(df_row, fn)
    return df_row
    

def run(worker, params, df=None, poolsize=1, tmpsave=False, verbose=False,
        calc_dir='calc'):
    results_fn = pj(calc_dir, 'results.json')
    makedirs(calc_dir)
    
    if df is None:
        if os.path.exists(results_fn):
            df = df_json_read(results_fn)
        else:
            df = pd.DataFrame()

    run_id = str(uuid.uuid4())
    worker_wrapper_partial = partial(worker_wrapper,
                                     worker=worker,
                                     tmpsave=tmpsave,
                                     verbose=verbose,
                                     run_id=run_id,
                                     calc_dir=calc_dir,
                                     )
    with mp.Pool(poolsize) as pool:
        results = pool.map(worker_wrapper_partial, params)
    
    for df_row in results:
        df = df.append(df_row, ignore_index=True)

    df_json_write(df, results_fn)
    return df
