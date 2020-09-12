from setuptools import setup

def readme():
    with open('README') as file:
        return file.read()

setup(
    name='zbot',
    version='58',
    url='https://github.com/bthate/zbot',
    author='Bart Thate',
    author_email='bthate@dds.nl',
    description="24/7 channel daaemon.",
    long_description=readme(),
    license='Public Domain',
    zip_safe=True,
    py_modules=["cmd", "csl", "hdl", "obj", "irc"], 
    packages=["madbot"],
    scripts=["bin/madbot"],
    classifiers=['Development Status :: 3 - Alpha',
                 'License :: Public Domain',
                 'Operating System :: Unix',
                 'Programming Language :: Python',
                 'Topic :: Utilities'
                ]
)
