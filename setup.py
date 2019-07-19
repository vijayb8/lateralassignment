from distutils.core import setup

setup(
    name='LateralAssignment',
    version='1.0.0',
    requires=[
        'tornado',
        'aiopg',
        'psycopg2'
    ],
)