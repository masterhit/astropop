# Licensed under a 3-clause BSD style license - see LICENSE.rst

import pytest
import hashlib
from astropop.math.hasher import hasher
from astropop.math.array import xy2r, iraf_indices
from astropop.math.opd_utils import opd2jd, solve_decimal, \
                                    read_opd_header_number
from astropop.math import gaussian, moffat
import numpy as np


def test_hasher():
    s = 'asdf1234 &*()[]'
    h = hasher(s, 10)
    assert h == '4b37febb5e'


@pytest.mark.parametrize('val, res', [('17jun19', 2457923.5),
                                      (['05ago04', '97jan01'],
                                       [2453586.5, 2450449.5])])
def test_opd2jd(val, res):
    assert np.array(opd2jd(val) == res).all()


@pytest.mark.parametrize('val', ['2017-01-01', 'not a date', 42])
def test_opd2jd_invalid(val):
    with pytest.raises(ValueError) as exc:
        opd2jd(val)
        assert 'Invalid OPD date to convert' in str(exc.value)


@pytest.mark.parametrize('val, res', [('0,1', '0.1'), ('2005,000', '2005.000'),
                                      ('0.00001', '0.00001')])
def test_solve_decimal(val, res):
    assert solve_decimal(val) == res


@pytest.mark.parametrize('val, res', [('0,1', 0.1), ('2005,000', 2005),
                                      ('1.0', 1)])
def test_read_opd_header_number(val, res):
    assert read_opd_header_number(val) == res


@pytest.mark.parametrize('val', ['2017-01-01', 'not a number', 'nan'])
def test_read_opd_header_number_invalid(val):
    with pytest.raises(ValueError) as exc:
        read_opd_header_number(val)
        assert 'Could not read the number:' in str(exc.value)


def test_xy2r():
    f = np.arange(4).reshape((2, 2))
    x, y = iraf_indices(f)
    r, outf = xy2r(x, y, f, 0.0, 0.0)
    assert np.array_equal(r, [0, 1, 1, np.sqrt(2)])
    assert np.array_equal(f.ravel(), outf)  # no reordering expected


def test_iraf_indices():
    f = np.arange(4).reshape((2, 2))
    x, y = iraf_indices(f)
    assert np.array_equal(x, [[0, 1], [0, 1]])
    assert np.array_equal(y, [[0, 0], [1, 1]])
