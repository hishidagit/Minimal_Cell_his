# successfully installed odecell with 
#   - SUNDIALS: 6.7.0 (compatible version)
#   - pycvodes: 0.14.2 (working version)
#   - Cython: 0.29.4 (required version)
#  - SWIG: 3.0.12 (downgraded from 4.3.1)

#   2. ✅ SWIG Policies: Set compatibility policies (CMAKE_POLICY_DEFAULT_CMP0078:UNINITIALIZED=OLD and
#   CMAKE_POLICY_DEFAULT_CMP0086:UNINITIALIZED=OLD)

# change pip version
conda activate minimal-cell
conda install -n minimal-cell pip==20.3.1

# install libsundials-dev
conda install -n minimal-cell -c conda-forge sundials glpk

cd ./odecell
pip install -r requirements.txt

pip install --upgrade cython
CFLAGS="-I$CONDA_PREFIX/include" LDFLAGS="-L$CONDA_PREFIX/lib" pip install --no-binary :all: pycvodes
pip install importlib_resources

conda install -c conda-forge pydantic=1.8.2

# conda install -c conda-forge cobra

conda install -c anaconda xlrd==1.2.0

conda install -c anaconda mpi4py
    


pip install .

cd ../