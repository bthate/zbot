# ZBOT - 24/7 channel daemon
#
#

from setuptools import setup

def readme():
    with open('README') as file:
        return file.read()

setup(
    name='zbot',
    version='59',
    url='https://github.com/bthate/zbot',
    author='Bart Thate',
    author_email='bthate@dds.nl',
    description="24/7 channel daaemon",
    long_description=readme(),
    license='Public Domain',
    zip_safe=False,
    packages=["zbot"],
    namespace_packages=["zbot"],
    scripts=["bin/zbot", "bin/zbotd", "bin/zcmd"],
    classifiers=['Development Status :: 3 - Alpha',
                 'License :: Public Domain',
                 'Operating System :: Unix',
                 'Programming Language :: Python',
                 'Topic :: Utilities'
                ]
)
