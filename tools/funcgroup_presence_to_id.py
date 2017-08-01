# Sebastian Raschka 2017
#
# screenlamp is a Python toolkit
# for hypothesis-driven virtual screening.
#
# Copyright (C) 2017 Michigan State University
# License: MIT
#
# Software author: Sebastian Raschka <http://sebastianraschka.com>
# Software author email: mail@sebastianraschka.com
#
# Software source repository: https://github.com/rasbt/screenlamp
# Documenatation: https://psa-lab.github.io/screenlamp
#
# screenlamp was developed in the
# Protein Structural Analysis & Design Laboratory
# (http://www.kuhnlab.bmb.msu.edu)
#
# If you are using screenlamp in your research, please cite
# the following journal article:
#
# Sebastian Raschka, Anne M. Scott, Nan Liu,
#   Santosh Gunturu, Mar Huertas, Weiming Li,
#   and Leslie A. Kuhn.
# "Screenlamp: A hypothesis-driven, ligand-based toolkit to
#    facilitate large-scale screening,
#    applied to discover potent GPCR inhibitors"


import os
import argparse
import sys
import pandas as pd
import time
from mputil import lazy_imap
from multiprocessing import cpu_count
from biopandas.mol2 import split_multimol2
from biopandas.mol2 import PandasMol2


def get_mol2_files(dir_path):

    files = []

    if os.path.isdir(dir_path):
        for f in os.listdir(dir_path):
            if f.endswith(('.mol2', 'mol2.gz')):
                file_path = os.path.join(dir_path, f)
                files.append(file_path)

    elif (os.path.isfile(dir_path) and
          dir_path.endswith(('.mol2', 'mol2.gz'))):
        files.append(dir_path)

    return files


def parse_selection_string(s, df_name='pdmol.df'):

    columns = ['(atom_id', '(atom_name', '(atom_type',
               '(subst_id', '(subst_name', '(charge']
    lst = [subs.strip() for subs in s.split('-->')]
    parsed = []

    for subs in lst:
        for c in columns:
            subs = subs.replace(c, '(%s.%s' % (df_name, c[1:]))
        parsed.append(subs)
    return parsed


def data_processor(mol2):

    pdmol = PandasMol2().read_mol2_from_list(mol2_lines=mol2[1],
                                             mol2_code=mol2[0])

    match = mol2[0]
    for sub_sele in SELECTION:
        if not pd.eval(sub_sele).any():
            match = ''
            break

    return match

def data_processor_gz(mol2_gz):

    pdmol = PandasMol2().read_mol2_from_list(mol2_lines=mol2_gz[1],
                                             mol2_code=mol2_gz[0])

    match = mol2_gz[0].decode('utf-8')
    for sub_sele in SELECTION:
        if not pd.eval(sub_sele).any():
            match = ''
            break

    return match


def read_and_write(mol2_files, id_file_path, verbose, n_cpus):

    if verbose:
        sys.stdout.write('Using selection: %s\n' % SELECTION)
        sys.stdout.flush()

    with open(id_file_path, 'w') as f:

        for mol2_file in mol2_files:
            if verbose:
                start = time.time()
                sys.stdout.write('Processing %s' % os.path.basename(mol2_file))
                sys.stdout.flush()

            cnt = 0

            if mol2_file.endswith('.gz'):
                data_processor_fn = data_processor_gz
            else:
                data_processor_fn = data_processor

            for chunk in lazy_imap(data_processor=data_processor_fn,
                                   data_generator=split_multimol2(
                                      mol2_file),
                                   n_cpus=n_cpus):

                _ = [f.write('%s\n' % mol2_id) for mol2_id
                     in chunk if mol2_id]
                cnt += len(chunk)

            if verbose:
                elapsed = time.time() - start
                sys.stdout.write(' | %d mol/sec\n' % (cnt / elapsed))
                sys.stdout.flush()


def get_num_cpus(n_cpus):
    if not n_cpus:
        n_cpus = cpu_count()
    elif n_cpus < 0:
        n_cpus = cpu_count() - n_cpus
    return n_cpus


def main(input_dir, output_file, verbose, n_cpus):
    n_cpus = get_num_cpus(n_cpus)
    dirpath = os.path.dirname(output_file)
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)
    mol2_files = get_mol2_files(dir_path=input_dir)
    read_and_write(mol2_files=mol2_files,
                   id_file_path=output_file,
                   verbose=verbose,
                   n_cpus=n_cpus)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
            description='Selecting molecules base on the presence'
                        '\nof certain atoms or functional groups.',
            epilog='Example:\n'
            'python funcgroup_presence_to_id.py --i mol2s/ -o mol2ids.txt\\'
            '\n  --selection ((atom_type == \'S.3\') | (atom_type == \'S.o2\')) --> (atom_type == \'O.2\') --processes 0',
            formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-i', '--input',
                        type=str,
                        help='Input directory with .mol2 and .mol2.gz files')
    parser.add_argument('-o', '--output',
                        type=str,
                        help='Directory for writing the output files')
    parser.add_argument('-s', '--selection',
                        type=str,
                        required=True,
                        help='Selection condition for the atom presence'
                        ' checks.'
                        '\n1) Require 2 atom types to be present:'
                        '\n    "(atom_type == \'S.o2\') -->'
                        ' (atom_type == \'O.2\')"'
                        '\n2) Selection example to consider either'
                        ' an S.o2 or S.3 atom and a O.2 atom to be present:'
                        '\n    "((atom_type == \'S.3\') |'
                        ' (atom_type == \'S.o2\')) -->'
                        ' (atom_type == \'O.2\')"'
                        '\n3) Selection example using logical ORs on '
                        'both sides:\n'
                        '    "((atom_type == \'S.3\') | (atom_type == '
                        '\'S.o2\'))'
                        ' -->  ((atom_type == \'O.2\') |'
                        ' (atom_type == \'O.3\'))"')
    parser.add_argument('--processes',
                        type=int,
                        default=1,
                        help='Number of processes to run in parallel.'
                             '\nIf processes > 0, the specified number of CPUs'
                             '\nwill be used.'
                             '\nIf processes = 0, all available CPUs will'
                             '\nbe used.'
                             '\nIf processes = -1, all available CPUs'
                             '\nminus `processes` will be used.')
    parser.add_argument('-v', '--verbose',
                        type=int,
                        default=1,
                        help='Verbosity level. If 0, does not print any'
                             '\noutput.'
                             '\nIf 1 (default), prints the file currently'
                             '\nprocessing.')

    parser.add_argument('--version', action='version', version='v. 1.0')

    args = parser.parse_args()
    SELECTION = parse_selection_string(args.selection)

    main(input_dir=args.input,
         output_file=args.output,
         verbose=args.verbose,
         n_cpus=args.processes)