from setuptools import setup

setup(
    name='SQLPackage',              # Name of the package
    version='0.1.0',                       # Package version
    description='SQL alchemy based database management tools',  # Short description
    long_description=open('_README_SQLPackage.adoc').read(),  # Long description from the AsciiDoc file
    long_description_content_type='text/x-asciidoc',  # Content type for AsciiDoc
    author='Sziller',
    author_email='szillerke@gmail.com',
    url='https://github.com/sziller',
    license='MIT',                         # License type (choose the one you use)
    packages=['sql_bases.sqlbase_node', 'sql_bases.sqlbase_utxo', 'sql_access'],  # string-list of packages to be translated
    install_requires=[
        'python-dotenv',
        'sqlalchemy'
    ],
    classifiers=[                          # Metadata for the package
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires='>=3.6',               # Specify the Python version requirement
)


# python3 setup_sql.py sdist bdist_wheel
