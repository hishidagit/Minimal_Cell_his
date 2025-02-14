rm -rf ./build
mkdir ./build
cd ./build
# システムのパスを先頭に
export PATH=/usr/bin:/usr/local/bin:$PATH
# システムの ld を優先
export LD=/usr/bin/ld
# もし CONDA_BUILD_SYSROOT などがセットされていれば外す
unset CONDA_BUILD_SYSROOT
cmake -S /root/project/Lattice_Microbes_his/src -B . \
  -D MPD_GLOBAL_T_MATRIX=True \
  -D MPD_GLOBAL_R_MATRIX=True \
  -DCMAKE_C_COMPILER=/usr/bin/gcc \
  -DCMAKE_CXX_COMPILER=/usr/bin/g++ \
  -DCMAKE_POLICY_DEFAULT_CMP0078=OLD \
   -DCMAKE_POLICY_DEFAULT_CMP0086=OLD \
   -DCMAKE_VERBOSE_MAKEFILE=ON  
#  -DOPT_PYTHON=OFF
make VERBOSE=0 
make install

cd ../