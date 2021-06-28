from setuptools import setup
from setuptools.extension import Extension
from setuptools.command.build_ext import build_ext as _build_ext
from setuptools.command.sdist import sdist as _sdist

def get_version(filename):
    """
    Get version from a file.
    Inspired by https://github.mabuchilab/QNET/.
    """
    with open(filename) as f:
        for line in f.readlines():
            if line.startswith("__version__"):
                return line.split("=")[1].strip()[1:-1]
    raise RuntimeError(
        "Could not get version from %s." % filename)


VERSION = get_version("yt_georaster/__init__.py")

dev_requirements = [
    'coveralls', 'flake8', 'pytest>=3.6', 'pytest-cov',
    'sphinx', 'sphinx_bootstrap_theme']

std_libs = []
cython_extensions = [
    Extension("yt_georaster.polygon_selector",
              ["yt_georaster/polygon_selector.pyx"],
              libraries=std_libs),
]

class build_ext(_build_ext):
    # subclass setuptools extension builder to avoid importing cython and numpy
    # at top level in setup.py. See http://stackoverflow.com/a/21621689/1382869
    def finalize_options(self):
        from Cython.Build import cythonize
        self.distribution.ext_modules[:] = cythonize(
                self.distribution.ext_modules)
        _build_ext.finalize_options(self)
        # Prevent numpy from thinking it is still in its setup process
        # see http://stackoverflow.com/a/21621493/1382869
        if isinstance(__builtins__, dict):
            # sometimes this is a dict so we need to check for that
            # https://docs.python.org/3/library/builtins.html
            __builtins__["__NUMPY_SETUP__"] = False
        else:
            __builtins__.__NUMPY_SETUP__ = False
        import numpy
        self.include_dirs.append(numpy.get_include())

class sdist(_sdist):
    # subclass setuptools source distribution builder to ensure cython
    # generated C files are included in source distribution.
    # See http://stackoverflow.com/a/18418524/1382869
    def run(self):
        # Make sure the compiled Cython files in the distribution are up-to-date
        from Cython.Build import cythonize
        cythonize(cython_extensions)
        _sdist.run(self)

setup(name="yt_georaster",
      version=VERSION,
      description="A yt extension for working with geotagged images loadable with rasterio.",
      author="Daniel Eastwood",
      author_email="eastwooddans@gmail.com",
      # license="BSD",
      url="https://github.com/ruithnadsteud/yt_georaster",
      packages=["yt_georaster"],
      keywords=["GeoTiff", "GTiff", "raster"],
      install_requires=[
          'fiona',
          'gdal',
          'numpy',
          'pyyaml',
          'rasterio',
          'shapely',
          'yt'
      ],
      classifiers=[
          "Development Status :: 4 - Beta",
          "Environment :: Console",
          "Intended Audience :: Science/Research",
          "Operating System :: MacOS :: MacOS X",
          "Operating System :: POSIX :: Linux",
          "Operating System :: Microsoft :: Windows",
          "Programming Language :: Python :: 3",
          "Topic :: Scientific/Engineering :: Image Processing",
          "Topic :: Scientific/Engineering :: GIS",
          "Topic :: Scientific/Engineering :: Visualization",
          ],
      extras_require={
          'dev': dev_requirements,
      },
      cmdclass={'sdist': sdist, 'build_ext': build_ext},
      ext_modules=cython_extensions,
      python_requires='>=3.7'
      )
