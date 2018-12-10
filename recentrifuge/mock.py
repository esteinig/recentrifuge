"""
Methods related to generation of mock data.

"""

import collections as col
import os
import random
import sys
from typing import Counter, List

from recentrifuge.centrifuge import select_centrifuge_inputs
from recentrifuge.config import Id, Filename
from recentrifuge.config import gray, blue, green, red, yellow, cyan
from recentrifuge.taxonomy import Taxonomy

# optional package pandas (to read Excel with mock layout)
_USE_PANDAS = True
try:
    import pandas as pd
except ImportError:
    pd = None
    _USE_PANDAS = False


MAX_HIT_LENGTH: int = 200  # Max hit length for random score generation


def generate_mock(ncbi: Taxonomy,
                  file: Filename,
                  rnd: int,
                  mocks: List[Filename],
                  xcel: Filename,
                  debug: bool,
                  ):
    
    def vprint(*args):
        """Print only if verbose/debug mode is enabled"""
        if debug:
            print(*args, end='')
            sys.stdout.flush()

    def read_mock_files(mock: Filename) -> Counter[Id]:
        """Read a mock layout (.mck) file"""
        mock_layout: Counter[Id] = col.Counter()
        with open(mock, 'r') as mck:
            vprint(gray('\nProcessing'), blue(mock), gray('file:\n'))
            for line in mck:
                if line.startswith('#'):
                    continue
                _tid, _num = line.split('\t')
                tid = Id(_tid)
                num = int(_num)
                mock_layout[tid] = num
                vprint(num, gray('\treads for taxid\t'), tid, '\t(',
                       cyan(ncbi.get_name(tid)), ')\n')
        return mock_layout

    def mock_from_source(out: Filename, mock_layout: Counter[Id]) -> None:
        """Generate a mock Centrifuge output file from source file"""
        with open(out, 'w') as fout, open(file) as fcfg:
            vprint(gray('Generating'), blue(out), gray('file... '))
            fout.write(fcfg.readline())  # copy cfg output file header
            reads_writen: int = 0
            for line in fcfg:
                tid = Id(line.split('\t')[2])
                if mock_layout[tid]:
                    fout.write(line)
                    mock_layout[tid] -= 1
                    reads_writen += 1
                    if not sum(mock_layout.values()):
                        vprint(reads_writen, 'reads', green('OK!\n'))
                        break
        if sum(mock_layout.values()):
            print(red('ERROR!\n'))
            print(gray('Incomplete read copy by taxid:'))
            mock_layout = +mock_layout  # Delete zero counts elements
            for tid in mock_layout:
                print(yellow(mock_layout[tid]), gray('reads missing for tid'),
                      tid, '(', cyan(ncbi.get_name(tid)), ')\n')

    def mock_from_scratch(out: Filename, mock_layout: Counter[Id]) -> None:
        """Generate a mock Centrifuge output file from scratch"""
        with open(out, 'w') as fout:
            vprint(gray('Generating'), blue(out), gray('file... '))
            fout.write('readID\tseqID\ttaxID\tscore\t2ndBestScore\t'
                       'hitLength\tqueryLength\tnumMatches\n')
            reads_writen: int = 0
            for numtid in mock_layout:
                tid = Id(numtid)  # Convert to Id the excel integer
                maxhl: int = random.randint(rnd + 1, MAX_HIT_LENGTH)
                rank: str = str(ncbi.get_rank(tid)).lower()
                for _ in range(int(mock_layout[numtid])):
                    hit_length = random.randint(rnd + 1, maxhl)
                    fout.write(f'test{reads_writen}\t{rank}\t'
                               f'{tid}\t{(hit_length - 15) ** 2}\t'
                               f'0\t{hit_length}\t{MAX_HIT_LENGTH}\t1\n')
                    reads_writen += 1
            vprint(reads_writen, 'reads', green('OK!\n'))

    def by_mock_files() -> None:
        """Do the job in case of mock files"""
        if len(mocks) == 1 and os.path.isdir(mocks[0]):
            select_centrifuge_inputs(mocks, ext='.mck')
        for mock in mocks:
            mock_layout: Counter[Id] = read_mock_files(mock)
            test: Filename = Filename(mock.split('.mck')[0] + '.out')
            if file:
                mock_from_source(test, mock_layout)
            else:
                mock_from_scratch(test, mock_layout)

    def by_excel_file() -> None:
        """Do the job in case of Excel file with all the details"""
        dirname = os.path.dirname(xcel)
        # Expected index (taxids) in column after taxa name, and last row will
        #  be removed (reserved for sum of reads in Excel file)
        mock_df = pd.read_excel(xcel, index_col=1, skipfooter=1,
                                dtype=str)
        del mock_df['RECENTRIFUGE MOCK']
        vprint(gray('Layout to generate the mock files:\n'), mock_df, '\n')
        for name, series in mock_df.iteritems():
            mock_layout: Counter[Id] = col.Counter(series.to_dict(dict))
            # In prev, series.to_dict(col.Counter) fails, so this is workaround
            test: Filename = Filename(os.path.join(dirname, name + '.out'))
            if file:
                mock_from_source(test, mock_layout)
            else:
                mock_from_scratch(test, mock_layout)

    if mocks:
        by_mock_files()
    elif xcel:
        by_excel_file()