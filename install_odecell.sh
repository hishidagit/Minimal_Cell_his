# change pip version
conda activate minimal-cell
conda install -n minimal-cell pip==20.3.1

# install libsundials-dev
conda install -n minimal-cell -c conda-forge sundials glpk

cd /root/project/Minimal_Cell_his/odecell
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