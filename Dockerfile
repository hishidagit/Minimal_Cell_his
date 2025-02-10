# continuumio/miniconda3イメージをベースにする
# docker build -t minimal-cell-img .
# docker run -it --name minimal-cell-cont minimal-cell-img
FROM continuumio/miniconda3

# 非対話モードに設定（必要に応じて）
ENV DEBIAN_FRONTEND=noninteractive

# 作業ディレクトリの作成
WORKDIR /root/project

# conda環境の作成とパッケージのインストール
RUN conda create -n minimal-cell -c conda-forge python=3.7.3 -y && \
    /bin/bash -c "source activate minimal-cell && \
    conda install -c conda-forge -y git gcc_linux-64==7.3.0 gxx_linux-64==7.3.0 binutils_linux-64==2.31.1 && \
    conda install -c anaconda -y hdf5==1.10.4 h5py==2.10.0 protobuf==3.13.0.1 && \
    conda install -c conda-forge -y numpy==1.19.2 cython==0.29.4 cmake==3.14.0 xlrd swig==4.0.2 jupyter matplotlib ipywidgets tqdm pillow jinja2 scipy pybind11 pandas pytables biopython"

# # Gitやその他必要なパッケージをapt経由でインストール（必要に応じて）
# RUN apt-get update && apt-get install -y \
#     git \
#     bzip2 

# Gitリポジトリをクローン
RUN git clone https://github.com/Luthey-Schulten-Lab/Minimal_Cell.git && \
    git clone https://github.com/Luthey-Schulten-Lab/Lattice_Microbes.git

# コンテナ起動時はbashを起動
CMD ["/bin/bash"]
