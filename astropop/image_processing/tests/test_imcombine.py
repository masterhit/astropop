# Licensed under a 3-clause BSD style license - see LICENSE.rst

import os
import numpy as np
import pytest
import astropy

from astropy.io import fits

from astropop.framedata import FrameData
from astropop.logger import logger, log_to_list
from astropop.image_processing.imarith import imcombine, _sigma_clip, \
                                              _minmax_clip, ImCombiner
from astropop.testing import assert_equal, assert_true, assert_false, \
                             assert_is_instance, assert_is_none, assert_in


class Test_MinMaxClip():

    def test_1D_simple(self):
        arr = np.arange(10)
        low, high = (2, 6)
        expect = np.array([1, 1, 0, 0, 0, 0, 0, 1, 1, 1], dtype=bool)

        mask = _minmax_clip(arr, low, high)
        assert_equal(mask, expect)

    def test_2D_simple(self):
        arr = np.arange(10).reshape((2, 5))
        low, high = (2, 6)
        expect = np.array([1, 1, 0, 0, 0, 0, 0, 1, 1, 1],
                           dtype=bool).reshape((2, 5))

        mask = _minmax_clip(arr, low, high)
        assert_equal(mask, expect)

    def test_3D_simple(self):
        arr = np.array([[[0, 1, 1], [2, 3, 3], [1, 2, 3]],
                        [[2, 3, 4], [2, 5, 6], [1, 0, 0]],
                        [[0, 1, 1], [2, 3, 7], [7, 0, 1]]])
        low, high = (2, 6)
        exp = np.array([[[1, 1, 1], [0, 0, 0], [1, 0, 0]],
                        [[0, 0, 0], [0, 0, 0], [1, 1, 1]],
                        [[1, 1, 1], [0, 0, 1], [1, 1, 1]]], dtype=bool)

        mask = _minmax_clip(arr, low, high)
        assert_equal(mask, exp)

    def test_minimum_disabled(self):
        arr = np.array([0, 1, 0, 2, 3, 0])
        low, high = (None, 1)
        expect = np.array([0, 0, 0, 1, 1, 0])
        mask = _minmax_clip(arr, low, high)
        assert_equal(mask, expect)

    def test_maximum_disabled(self):
        arr = np.array([0, 1, 0, 2, 3, 0])
        low, high = (1, None)
        expect = np.array([1, 0, 1, 0, 0, 1])
        mask = _minmax_clip(arr, low, high)
        assert_equal(mask, expect)

    def test_invalid(self):
        # must mask invalid numbers
        arr = np.array([0, 1, 2, np.inf, np.nan, 5, 1])
        low, high = (1, 3)
        expect = np.array([1, 0, 0, 1, 1, 1, 0])
        mask = _minmax_clip(arr, low, high)
        assert_equal(mask, expect)


class Test_SigmaClip():
    # TODO: test 3D
    # TODO: test axis in 3D

    def test_unkown_sigmaclip(self):
        arr = np.arange(10)
        with pytest.raises(TypeError):
            _sigma_clip(arr, 'testing')

        with pytest.raises(TypeError):
            _sigma_clip(arr, '1,2')

        # too many values must raise
        with pytest.raises(ValueError):
            _sigma_clip(arr, [1, 2, 3])

    def test_sigmclip_types(self):
        arr = np.arange(10)

        # must work with numbers
        _sigma_clip(arr, 1)

        # must work with 2-elements array
        _sigma_clip(arr, np.array([1, 2]))
        _sigma_clip(arr, [1, 2])
        _sigma_clip(arr, (1, 2))

    def test_invalid(self):
        arr = np.ones((5, 5))

        indx = [(1, 1), (4, 1), (2, 3)]

        arr[indx[0]] = 1000
        arr[indx[1]] = np.inf
        arr[indx[2]] = np.nan

        mask = _sigma_clip(arr)

        for i in range(5):
            for j in range(5):
                if (i, j) in indx:
                    assert_true(mask[i, j])
                else:
                    assert_false(mask[i, j])

    def test_functions_names(self):
        arr = np.ones((5, 5))

        # all this should run
        _sigma_clip(arr, cen_func='median')
        _sigma_clip(arr, cen_func='mean')
        _sigma_clip(arr, dev_func='std')
        _sigma_clip(arr, cen_func='mean', dev_func='std')

        if astropy.version.major > 4 and astropy.version.minor > 2:
            _sigma_clip(arr, dev_func='mad_std')
            _sigma_clip(arr, cen_func='median', dev_func='mad_std')

    def test_functions_callable(self):
        arr = np.ones((5, 5))

        mask = _sigma_clip(arr, cen_func=np.median)
        mask = _sigma_clip(arr, dev_func=np.std)

        # testing forced 1.0pm0.5
        def _test_cen(*args, **kwargs):
            return 1.0

        def _test_dev(*args, **kwargs):
            return 0.5

        # 1.2 should not be masked with 1.0pm0.5, 2.0 and 1000 yes
        arr[0, 0] = 1.2
        arr[1, 1] = 2
        arr[3, 2] = 1000

        mask = _sigma_clip(arr, 1, cen_func=_test_cen, dev_func=_test_dev)
        for i in range(5):
            for j in range(5):
                if (i, j) in [(1, 1), (3, 2)]:
                    assert_true(mask[i, j])
                else:
                    assert_false(mask[i, j])

    def test_functions_invalid(self):
        arr = np.ones((5, 5))

        with pytest.raises(ValueError):
            _sigma_clip(arr, cen_func='invalid')
        with pytest.raises(ValueError):
            _sigma_clip(arr, dev_func='invalid')
        with pytest.raises(TypeError):
            _sigma_clip(arr, cen_func=1)
        with pytest.raises(TypeError):
            _sigma_clip(arr, dev_func=1)
        with pytest.raises(TypeError):
            _sigma_clip(arr, cen_func=[])
        with pytest.raises(TypeError):
            _sigma_clip(arr, dev_func=[])

    def test_1D_simple(self):
        arr = np.random.normal(5, 2, 1000)
        arr[322] = 1000
        arr[256] = 1000
        arr[12] = -1000
        exp = np.zeros(1000, dtype=bool)
        exp[322] = True
        exp[256] = True
        exp[12] = True

        mask = _sigma_clip(arr, 3)
        assert_equal(mask, exp)

    def test_2D_simple(self):
        # mean:4.532 median:4.847 std:282
        arr = np.array([[6.037, 5.972, 5.841, 2.775, 0.711],
                        [6.539, 4.677, -1000, 5.633, 3.478],
                        [4.847, 7.563, 3.323, 7.952, 6.646],
                        [6.136, 2.690, 4.193, 1000., 4.483],
                        [5.673, 7.479, 3.874, 4.756, 2.021]])

        mask = _sigma_clip(arr, 1)
        for i in range(5):
            for j in range(5):
                if (i, j) in [(1, 2), (3, 3)]:
                    assert_true(mask[i, j])
                else:
                    assert_false(mask[i, j])


class Test_ImCombineConformance():

    def test_class_creation(self):
        c = ImCombiner()
        assert_is_instance(c, ImCombiner)

        d = ImCombiner(max_memory=2e10)
        assert_equal(d._max_memory, 2e10)

    def test_class_set_sigmaclip(self):
        # empty must disable clipping
        c = ImCombiner()
        c.set_sigma_clip()
        assert_equal(c._sigma_clip, None)
        assert_equal(c._sigma_cen_func, None)
        assert_equal(c._sigma_dev_func, None)

        # set sigmaclip one value
        c = ImCombiner()
        c.set_sigma_clip(1)
        assert_equal(c._sigma_clip, 1)
        assert_equal(c._sigma_cen_func, 'median')
        assert_equal(c._sigma_dev_func, 'std')

        # set sigmaclip two values
        c = ImCombiner()
        c.set_sigma_clip((1, 2))
        assert_equal(c._sigma_clip, (1, 2))
        assert_equal(c._sigma_cen_func, 'median')
        assert_equal(c._sigma_dev_func, 'std')

        # Enable and disable
        c = ImCombiner()
        c.set_sigma_clip((1, 2))
        c.set_sigma_clip()
        assert_equal(c._sigma_clip, None)
        assert_equal(c._sigma_cen_func, None)
        assert_equal(c._sigma_dev_func, None)

        # set functions
        c = ImCombiner()
        c.set_sigma_clip((1, 2), 'mean', 'mad_std')
        assert_equal(c._sigma_clip, (1, 2))
        assert_equal(c._sigma_cen_func, 'mean')
        assert_equal(c._sigma_dev_func, 'mad_std')

    def test_class_set_sigmaclip_errors(self):
        # more then 2 elements must fail
        with pytest.raises(ValueError):
            c = ImCombiner()
            c.set_sigma_clip((1, 2, 3))

        # problematic functions
        with pytest.raises(ValueError):
            c = ImCombiner()
            c.set_sigma_clip((1, 2), 'no-existing')

        with pytest.raises(ValueError):
            c = ImCombiner()
            c.set_sigma_clip((1, 2), 'mean', 'no-existing')

        # None should fail
        with pytest.raises(ValueError):
            c = ImCombiner()
            c.set_sigma_clip((1, 2), None)

        with pytest.raises(ValueError):
            c = ImCombiner()
            c.set_sigma_clip((1, 2), 'mean', None)

    def test_class_set_minmax(self):
        c = ImCombiner()
        c.set_minmax_clip(0, 1)
        assert_equal(c._minmax, (0, 1))

        # test flipping
        c = ImCombiner()
        c.set_minmax_clip(1, 0)
        assert_equal(c._minmax, (0, 1))

        # test nones
        c = ImCombiner()
        c.set_minmax_clip(None, 0)
        assert_equal(c._minmax, (None, 0))
        c = ImCombiner()
        c.set_minmax_clip(0, None)
        assert_equal(c._minmax, (0, None))

        # test one element setting
        c = ImCombiner()
        c.set_minmax_clip(0)
        assert_equal(c._minmax, (0, None))
        c = ImCombiner()
        c.set_minmax_clip(min_value=0)
        assert_equal(c._minmax, (0, None))
        c = ImCombiner()
        c.set_minmax_clip(max_value=0)
        assert_equal(c._minmax, (None, 0))

        # disable
        c = ImCombiner()
        c.set_minmax_clip()
        assert_equal(c._minmax, None)
        c.set_minmax_clip(0, 1)
        assert_equal(c._minmax, (0, 1))
        c.set_minmax_clip()
        assert_equal(c._minmax, None)

    def test_class_set_minmax_errors(self):
        c = ImCombiner()

        # not numbers should fail
        with pytest.raises(ValueError):
            c.set_minmax_clip('a')

        # not numbers should fail
        with pytest.raises(ValueError):
            c.set_minmax_clip(0, 'a')

        # not numbers should fail
        with pytest.raises(ValueError):
            c.set_minmax_clip([1, 2])

        # not numbers should fail
        with pytest.raises(ValueError):
            c.set_minmax_clip(0, [1, 2])


class Test_ImCombiner_Combine():
    def test_image_loading_framedata(self, tmpdir):
        tmp = tmpdir.strpath
        n = 10
        d = np.ones((10, 10))
        l = [FrameData(d, unit='adu', uncertainty=d, cache_folder=tmp,
                       cache_filename=f'test{i}') for i in range(n)]

        comb = ImCombiner()
        # must start empty
        assert_equal(len(comb._images), 0)
        assert_is_none(comb._buffer)
        comb._load_images(l)
        assert_equal(len(comb._images), n)
        assert_is_none(comb._buffer)
        for i, v in enumerate(comb._images):
            fil = os.path.join(tmp, f'test{i}')
            assert_is_instance(v, FrameData)
            assert_true(v._memmapping)
            assert_true(os.path.exists(fil+'.data'))
            assert_true(os.path.exists(fil+'.unct'))
            assert_true(os.path.exists(fil+'.mask'))

        comb._clear()
        # must start empty
        assert_equal(len(comb._images), 0)
        assert_is_none(comb._buffer)

        # ensure tmp files cleaned
        for i in range(n):
            fil = os.path.join(tmp, f'test{i}')
            assert_false(os.path.exists(fil+'.data'))
            assert_false(os.path.exists(fil+'.unct'))
            assert_false(os.path.exists(fil+'.mask'))

    def test_image_loading_fitsfile(self, tmpdir):
        tmp = tmpdir.strpath
        n = 10
        d = np.ones((10, 10))
        l = [os.path.join(tmp, f'fits_test{i}') for i in range(n)]
        for f in l:
            fits.PrimaryHDU(d).writeto(f)

        logs = []
        lh = log_to_list(logger, logs, full_record=True)
        comb = ImCombiner()
        comb._load_images(l)

        # check if the logging is properly being emitted.
        log = [i for i in logs if i.msg == 'The images to combine are not '
               'FrameData. Some features may be disabled.']
        assert_equal(len(logs),  1)
        assert_equal(logs[0].levelname, 'WARNING')

        assert_equal(len(comb._images), n)
        assert_is_none(comb._buffer)
        for i, v in enumerate(comb._images):
            assert_is_instance(v, FrameData)
            assert_true(v._memmapping)

        comb._clear()
        # must start empty
        assert_equal(len(comb._images), 0)
        assert_is_none(comb._buffer)

    def test_image_loading_fitshdu(self, tmpdir):
        tmp = tmpdir.strpath
        n = 10
        d = np.ones((10, 10))
        l = [fits.PrimaryHDU(d) for i in range(n)]

        logs = []
        lh = log_to_list(logger, logs, full_record=True)
        comb = ImCombiner()
        comb._load_images(l)

        # check if the logging is properly being emitted.
        log = [i for i in logs if i.msg == 'The images to combine are not '
               'FrameData. Some features may be disabled.']
        assert_equal(len(logs),  1)
        assert_equal(logs[0].levelname, 'WARNING')
        logger.removeHandler(lh)

        assert_equal(len(comb._images), n)
        assert_is_none(comb._buffer)
        for i, v in enumerate(comb._images):
            assert_is_instance(v, FrameData)
            assert_true(v._memmapping)

        comb._clear()
        # must start empty
        assert_equal(len(comb._images), 0)
        assert_is_none(comb._buffer)

    def test_image_loading_empty(self):
        comb = ImCombiner()
        with pytest.raises(ValueError, match='Image list is empty.'):
            comb._load_images([])

    def test_check_consistency(self):
        n = 10
        d = np.ones((10, 10))
        l = [FrameData(d, unit='adu') for i in range(n)]
        comb = ImCombiner()
        # empty should raise
        with pytest.raises(ValueError, match='Combiner have no images.'):
            comb._check_consistency()

        comb._load_images(l)
        # nothing should raise
        comb._check_consistency()

        # incompatible unit should raise
        comb._images[3].unit = 'm'
        with pytest.raises(ValueError, match='.* unit incompatible .*'):
            comb._check_consistency()
        comb._images[3].unit = 'adu'

        # incompatible shape should raise
        comb._images[4].data = np.ones((2, 2))
        with pytest.raises(ValueError, match='.* shape incompatible .*'):
            comb._check_consistency()

    def test_invalid_method(self):
        n = 10
        d = np.ones((10, 10))
        l = [FrameData(d, unit='adu') for i in range(n)]
        comb = ImCombiner()
        with pytest.raises(ValueError, match='hulk-smash is not a valid '
                           'combining method.'):
            comb.combine(l, method='hulk-smash')
