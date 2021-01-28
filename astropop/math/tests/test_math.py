# Licensed under a 3-clause BSD style license - see LICENSE.rst

import pytest
from astropop.math.hasher import hasher
from astropop.math.array import xy2r, iraf_indices, trim_array
from astropop.math.opd_utils import opd2jd, solve_decimal, \
                                    read_opd_header_number
from astropop.math import gaussian, moffat
import numpy as np

from astropop.testing import assert_equal, assert_in


def test_hasher():
    s = 'asdf1234 &*()[]'
    h = hasher(s, 10)
    assert_equal(h, '4b37febb5e')


@pytest.mark.parametrize('val, res', [('17jun19', 2457923.5),
                                      (['05ago04', '97jan01'],
                                       [2453586.5, 2450449.5])])
def test_opd2jd(val, res):
    assert_equal(opd2jd(val), res)


@pytest.mark.parametrize('val', ['2017-01-01', 'not a date', 42])
def test_opd2jd_invalid(val):
    with pytest.raises(ValueError) as exc:
        opd2jd(val)
        assert_in('Invalid OPD date to convert', str(exc.value))


@pytest.mark.parametrize('val, res', [('0,1', '0.1'), ('2005,000', '2005.000'),
                                      ('0.00001', '0.00001')])
def test_solve_decimal(val, res):
    assert_equal(solve_decimal(val), res)


@pytest.mark.parametrize('val, res', [('0,1', 0.1), ('2005,000', 2005),
                                      ('1.0', 1)])
def test_read_opd_header_number(val, res):
    assert_equal(read_opd_header_number(val), res)


@pytest.mark.parametrize('val', ['2017-01-01', 'not a number', 'nan'])
def test_read_opd_header_number_invalid(val):
    with pytest.raises(ValueError) as exc:
        read_opd_header_number(val)
        assert_in('Could not read the number:', str(exc.value))


def test_xy2r():
    f = np.arange(4).reshape((2, 2))
    x, y = iraf_indices(f)
    r, outf = xy2r(x, y, f, 0.0, 0.0)
    assert_equal(r, [0, 1, 1, np.sqrt(2)])
    assert_equal(f.ravel(), outf)  # no reordering expected


def test_iraf_indices():
    f = np.arange(4).reshape((2, 2))
    x, y = iraf_indices(f)
    assert_equal(x, [[0, 1], [0, 1]])
    assert_equal(y, [[0, 0], [1, 1]])


def test_trim_array_centered():
    y, x = np.indices((100, 100))
    a = x*y
    ta, tx, ty = trim_array(a, 21, (50, 50), (y, x))
    assert_equal(ta, a[39:61, 39:61])
    assert_equal(tx, x[39:61, 39:61])
    assert_equal(ty, y[39:61, 39:61])
    assert_equal(np.min(tx), 39)
    assert_equal(np.max(tx), 60)
    assert_equal(np.min(ty), 39)
    assert_equal(np.max(ty), 60)
    assert_equal(np.min(ta), 39*39)
    assert_equal(np.max(ta), 60*60)


def test_trim_array_right():
    y, x = np.indices((100, 100))
    a = x*y
    ta, tx, ty = trim_array(a, 21, (95, 50), (y, x))
    assert_equal(ta, a[39:61, 84:])
    assert_equal(tx, x[39:61, 84:])
    assert_equal(ty, y[39:61, 84:])
    assert_equal(np.min(tx), 84)
    assert_equal(np.max(tx), 99)
    assert_equal(np.min(ty), 39)
    assert_equal(np.max(ty), 60)
    assert_equal(np.min(ta), 84*39)
    assert_equal(np.max(ta), 99*60)


def test_trim_array_left():
    y, x = np.indices((100, 100))
    a = x*y
    ta, tx, ty = trim_array(a, 21, (5, 50), (y, x))
    assert_equal(ta, a[39:61, :16])
    assert_equal(tx, x[39:61, :16])
    assert_equal(ty, y[39:61, :16])
    assert_equal(np.min(tx), 0)
    assert_equal(np.max(tx), 15)
    assert_equal(np.min(ty), 39)
    assert_equal(np.max(ty), 60)
    assert_equal(np.min(ta), 0*39)
    assert_equal(np.max(ta), 15*60)


def test_trim_array_bottom():
    y, x = np.indices((100, 100))
    a = x*y
    ta, tx, ty = trim_array(a, 21, (50, 5), (y, x))
    assert_equal(ta, a[:16, 39:61])
    assert_equal(tx, x[:16, 39:61])
    assert_equal(ty, y[:16, 39:61])
    assert_equal(np.min(ty), 0)
    assert_equal(np.max(ty), 15)
    assert_equal(np.min(tx), 39)
    assert_equal(np.max(tx), 60)
    assert_equal(np.min(ta), 0*39)
    assert_equal(np.max(ta), 15*60)


def test_trim_array_top():
    y, x = np.indices((100, 100))
    a = x*y
    ta, tx, ty = trim_array(a, 21, (50, 95), (y, x))
    assert_equal(ta, a[84:, 39:61])
    assert_equal(tx, x[84:, 39:61])
    assert_equal(ty, y[84:, 39:61])
    assert_equal(np.min(ty), 84)
    assert_equal(np.max(ty), 99)
    assert_equal(np.min(tx), 39)
    assert_equal(np.max(tx), 60)
    assert_equal(np.min(ta), 84*39)
    assert_equal(np.max(ta), 99*60)


def test_trim_array_no_indices():
    y, x = np.indices((100, 100))
    a = x*y
    ta, tx, ty = trim_array(a, 21, (50, 95))
    assert_equal(ta, a[84:, 39:61])
    assert_equal(tx, 11)
    assert_equal(ty, 11)


def test_trim_array_one_origin():
    y, x = np.indices((100, 100))
    a = x*y
    ta, tx, ty = trim_array(a, 21, (50, 95), origin=1)
    assert_equal(ta, a[85:, 40:62])
    assert_equal(tx, 11)
    assert_equal(ty, 11)


def test_trim_array_even():
    y, x = np.indices((100, 100))
    a = x*y
    ta, tx, ty = trim_array(a, 20, (50, 95))
    assert_equal(ta, a[85:, 40:61])
    assert_equal(tx, 10)
    assert_equal(ty, 10)
