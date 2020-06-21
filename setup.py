import os
os.environ["SETUPTOOLS_INSTALL"] = "TRUE"
import setuptools
import dbbs_models

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
     name='dbbs-models',
     version=dbbs_models.__version__,
     author="Martina Rizza, Stefano Masoli, Robin De Schepper, Egidio D'Angelo",
     author_email="robingilbert.deschepper@unipv.it",
     description="Collection of neuron models for the NEURON simulator",
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="https://github.com/dbbs-lab/models",
     include_package_data=True,
     package_data={
         # If any package contains *.txt or *.rst files, include them:
         "": ["morphologies/*.asc", "morphologies/*.swc"],
     },
     license='GPLv3',
     packages=setuptools.find_packages(),
     classifiers=[
         "Programming Language :: Python :: 3",
         "Operating System :: OS Independent",
     ],
     install_requires=[
        "arborize>=1.1.0",
        "nrn-glia>=0.3.5",
        "dbbs-mod-collection>=0.0.6",
        "nrn-patch>=1.4.0",
     ]
 )
