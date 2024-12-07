#!/usr/bin/python3.10
"""
setup function to be run when creating packages
command to be typed in:
python setup.py sdist bdist_wheel
"""

from setuptools import setup

setup(
    name='devtools',  # package name, used at pip or tar.
    version='0.0.0',  # version Nr.... whatever
    # ATTENTION: use different packages for use-cases
    packages=["shmc_api_classes", "shmc_backend_classes", "sz_messages", "sql_access", "sql_bases", "log_tools",
              "sql_bases/sqlbase_measurement",
              "sql_bases/sqlbase_node",
              "sql_bases/sqlbase_user",
              "sql_bases/sqlbase_user_anonym",
              "sql_bases/sqlbase_utxo",
              "sql_bases/sqlbase_dlc",
              ],
    include_package_data=True,
    url="sziller.eu",  # if url is used at all
    license='MIT',
    author='sziller',
    author_email='szillerke@gmail.com',
    description='Development tool for different projects',
    install_requires=[
        "pyzmq",
        "sqlalchemy",
        "fastapi",
        "python-jose",
        "passlib"
    ],  # ATTENTION! Wheel file needed, depending on environment
    dependency_links=[],  # if dependent on external projects
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',  # Specify minimum Python version requirement.
)
