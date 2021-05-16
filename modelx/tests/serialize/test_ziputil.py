import zipfile
import filecmp
import pickle
from modelx.serialize import ziputil
import pytest
from itertools import product


def sample_root(path):
    return path / "rootルート", path / "rootルート.zip", path / "rootルートext"


def sample_path(root):
    return tuple(r / "abc漢字" / "fileファイル" for r in root)


def sample_pandas():
    import pandas as pd
    import numpy as np

    df = pd.DataFrame({"foo": range(5), "bar": range(5, 10)})
    series = pd.Series([1, 3, 5, np.nan, 6, 8])

    return df, series


def test_write_str(tmp_path):

    root, zip_root, ext_root = sample_root(tmp_path)
    path, zip_path, ext_path = sample_path(sample_root(tmp_path))

    ziputil.make_root(root, is_zip=False)
    ziputil.make_root(zip_root, is_zip=True,
                      compression=zipfile.ZIP_STORED)

    text = "Hello! Привет こんにちは 你好\n"

    ziputil.write_str_utf8(text, path)
    ziputil.write_str_utf8(text, zip_path,
                           compression=zipfile.ZIP_STORED)

    with zipfile.ZipFile(zip_root) as testzip:
        testzip.extractall(ext_root)

    assert filecmp.cmp(path, ext_path, shallow=False)


@pytest.mark.parametrize("pdobj", sample_pandas())
def test_pandas_to_pickle(tmp_path, pdobj):
    
    root, zip_root, ext_root = sample_root(tmp_path)
    path, zip_path, ext_path = sample_path(sample_root(tmp_path))
    
    ziputil.make_root(root, is_zip=False)
    ziputil.make_root(zip_root, is_zip=True, compression=zipfile.ZIP_STORED)
    
    ziputil.pandas_to_pickle(pdobj, path)
    ziputil.pandas_to_pickle(pdobj, zip_path, compression=zipfile.ZIP_STORED)

    with zipfile.ZipFile(zip_root) as testzip:
        testzip.extractall(ext_root)

    assert filecmp.cmp(path, ext_path, shallow=False)


@pytest.mark.parametrize("mode, encoding, newline, compression, compresslevel",
                         [["b", None, None, zipfile.ZIP_DEFLATED, None],
                          ["t", "utf-8", None, zipfile.ZIP_DEFLATED, 9],   # Error on encoding==None
                          ["t", "utf-8", "\n", zipfile.ZIP_STORED, None]])
def test_write_file(
        tmp_path, mode, encoding, newline, compression, compresslevel):

    root, zip_root, ext_root = sample_root(tmp_path)
    path, zip_path, ext_path = sample_path(sample_root(tmp_path))

    ziputil.make_root(root, is_zip=False,
                      compression=compression, compresslevel=compresslevel)
    ziputil.make_root(zip_root, is_zip=True,
                      compression=compression, compresslevel=compresslevel)

    data = {'a': [1, 2, 3], 'b': 4, 'c': '漢字'}

    if mode == "b":
        def callback(f):
            pickle.dump(data, f)
    else:
        def callback(f):
            for k, v in data.items():
                f.write("(%s, %s)\n" % (k, v))

    ziputil.write_file(callback, path, mode=mode, encoding=encoding, newline=newline)
    ziputil.write_file(callback, zip_path, mode=mode, encoding=encoding, newline=newline,
                       compression=zipfile.ZIP_STORED)

    with zipfile.ZipFile(zip_root) as testzip:
        testzip.extractall(ext_root)

    assert filecmp.cmp(path, ext_path, shallow=False)


def test_read_str(tmp_path):

    root, zip_root, _ = sample_root(tmp_path)
    path, zip_path, _ = sample_path(sample_root(tmp_path))

    ziputil.make_root(root, is_zip=False)
    ziputil.make_root(zip_root, is_zip=True, compression=zipfile.ZIP_STORED)

    text = "Hello! Привет こんにちは 你好\n"

    ziputil.write_str_utf8(text, path)
    ziputil.write_str_utf8(text, zip_path, compression=zipfile.ZIP_STORED)

    assert ziputil.read_str_utf8(path) == text
    assert ziputil.read_str_utf8(zip_path) == text


@pytest.mark.parametrize("mode, encoding, newline",
                         [["b", None, None],
                          ["t", None, None],
                          ["t", "utf-8", "\n"]])
def test_read_file(tmp_path, mode, encoding, newline):

    root, zip_root, _ = sample_root(tmp_path)
    path, zip_path, _ = sample_path(sample_root(tmp_path))

    ziputil.make_root(root, is_zip=False)
    ziputil.make_root(zip_root, is_zip=True, compression=zipfile.ZIP_STORED)

    data = {'a': [1, 2, 3], 'b': 4}

    if mode == "b":
        def callback(f):
            pickle.dump(data, f)

        def load(f):
            return pickle.load(f)

        result = data

    else:
        def callback(f):
            for k, v in data.items():
                f.write("(%s, %s)\n" % (k, v))

        def load(f):
            return f.read()

        result = "".join(["(%s, %s)\n" % (k, v) for k, v in data.items()])

    ziputil.write_file(callback, path, mode)
    ziputil.write_file(callback, zip_path, mode,
                       compression=zipfile.ZIP_STORED)

    assert ziputil.read_file(load, zip_path, mode) == result
    assert ziputil.read_file(load, path, mode) == result


@pytest.mark.parametrize("is_src_zip, is_dst_zip",
                         list(product((True, False), (True, False))))
def test_copy_file(tmp_path, is_src_zip, is_dst_zip):

    src_root = tmp_path / "src"
    dst_root = tmp_path / "dst"

    src = src_root / "abc漢字" / "fileファイル"
    dst = dst_root / "fileファイル"

    ziputil.make_root(src_root, is_zip=is_src_zip,
                      compression=zipfile.ZIP_STORED)
    ziputil.make_root(dst_root, is_zip=is_dst_zip,
                      compression=zipfile.ZIP_STORED)

    text = "Hello! Привет こんにちは 你好\n"
    ziputil.write_str_utf8(text, src,
                           compression=zipfile.ZIP_STORED)

    ziputil.copy_file(src, dst,
                      compression=zipfile.ZIP_DEFLATED,
                      compresslevel=None)

    assert ziputil.read_str_utf8(dst) == text
