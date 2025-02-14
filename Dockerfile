# continuumio/miniconda3イメージをベースにする
# docker build -t minimal-cell-img .
# docker run -it --name minimal-cell-cont minimal-cell-img
FROM continuumio/miniconda3

# 非対話モードに設定（必要に応じて）
ENV DEBIAN_FRONTEND=noninteractive

# 作業ディレクトリの作成
WORKDIR /root/project
# install build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libprotobuf-dev protobuf-compiler \
    swig

# conda環境の作成とパッケージのインストール
RUN conda create -n minimal-cell -c conda-forge python=3.7.3 -y &&  \
    conda install -n minimal-cell -c anaconda "hdf5<1.12" "h5py<3.12" && \
    conda install -n minimal-cell -c conda-forge -y numpy==1.19.2 cython jupyter matplotlib ipywidgets tqdm pillow jinja2 scipy pybind11 pandas pytables biopython

RUN export LD_LIBRARY_PATH=/opt/conda/envs/minimal-cell/lib:$LD_LIBRARY_PATH

# # Gitやその他必要なパッケージをapt経由でインストール（必要に応じて）
# RUN apt-get update && apt-get install -y \
#     git \
#     bzip2 

# Gitリポジトリをクローン
RUN git clone https://github.com/hishidagit/Minimal_Cell_his.git && \
    git clone https://github.com/hishidagit/Lattice_Microbes_his.git

# コンテナ起動時はbashを起動
CMD ["/bin/bash"]
