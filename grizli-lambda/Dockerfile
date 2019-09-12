FROM amazonlinux:2017.09

#  docker build . -t gbrammer/grizli-lambda-test:latest
#  docker run --rm -it gbrammer/grizli-lambda-test:latest /bin/bash

#  ## Run with working directory
#  docker run -v $(pwd):/workdir -i -t gbrammer/grizli-lambda-test /bin/bash
#  (in the environment)  
#  export VIRTUAL_ENV=/venv; source ${VIRTUAL_ENV}/bin/activate; cd /workdir
#

#  ## Build the full venv.zip file and copy to AWS
#  cd /tmp/ ; docker run -v $(pwd):/workdir -i -t gbrammer/grizli-lambda-test /bin/bash -c "cp /tmp/venv.zip /workdir/"; cd - ; aws s3 cp /tmp/venv.zip s3://aws-grivam/tmp/venv.zip --acl public-read

#ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

##
## Linux tools
##

# RUN pwd # Force rebuild from here

RUN yum update -y && \
    yum install -y atlas-devel \
                   atlas-sse3-devel \
                   blas-devel \
                   gcc \
                   gcc-c++ \
                   lapack-devel \
                   python36-devel \
                   python36-virtualenv \
                   findutils \
                   git \
                   vi \
                   which \
                   zip

ENV VIRTUAL_ENV /venv

### Initialize Python3.6  virtualenv
RUN /usr/bin/virtualenv-3.6 \
    --python /usr/bin/python3.6 ${VIRTUAL_ENV} \
    --always-copy \
    --no-site-packages

### For cc1plus compiler
ENV PATH "${PATH}:/usr/libexec/gcc/x86_64-amazon-linux/4.8.5/"
 
# RUN pwd # Force rebuild from here
  
### Install minimal Python tools
RUN source ${VIRTUAL_ENV}/bin/activate && \
    pip install --upgrade setuptools && \
    pip install wheel && \
    pip install numpy && \
    pip install scipy && \
    pip install matplotlib && \
    pip install astropy && \
    pip install pyyaml && \
    pip install drizzlepac && \
    pip install peakutils && \
    pip install extinction && \
    pip install descartes && \
    pip install shapely && \
    pip install pyregion 
    
# RUN pwd # Force rebuild from here

### Additional dependencies
# RUN source ${VIRTUAL_ENV}/bin/activate && \
#     pip install git+https://github.com/gbrammer/tristars.git
    
# RUN source ${VIRTUAL_ENV}/bin/activate && \
#     pip install cython && \
#     pip install git+https://github.com/kbarbary/sep.git
        
##### Special matplotlibrc file

# Initialize matplotib directory
RUN source ${VIRTUAL_ENV}/bin/activate && \
    python -c "import matplotlib"

ADD ./Install/matplotlibrc /root/.config/matplotlib/matplotlibrc
ADD ./Install/matplotlibrc ${VIRTUAL_ENV}/
ADD ./Install/matplotlibrc /venv/lib64/python3.6/site-packages/matplotlib/mpl-data/matplotlibrc

RUN date # Force rebuild from here
RUN echo "2019-09-12e" # Force rebuild from here

####
# Install grizli
####
RUN cd /tmp/ && \
    source ${VIRTUAL_ENV}/bin/activate && \
    git clone https://github.com/gbrammer/grizli.git && \
    cd grizli && \
    #python setup.py install && \
    # rm grizli/data/templates/stars/bt-settl_t400-3500_z0.0.fits && \
    pip install . && \
    cd ../ && \
    rm -rf grizli
    
# Config files in GRIZLI_PATH
RUN source ${VIRTUAL_ENV}/bin/activate && \
    GRIZLI_PATH=`python -c "import grizli; print(grizli.GRIZLI_PATH)" | tail -1`  && \
    echo $GRIZLI_PATH && \
    cp ${VIRTUAL_ENV}/matplotlibrc ${GRIZLI_PATH}/matplotlibrc && \
    mkdir $GRIZLI_PATH/CONF/ && \
    ln -s $GRIZLI_PATH/CONF /tmp/

ADD ./Install/setup_grizli.py /tmp/
RUN source ${VIRTUAL_ENV}/bin/activate && \
    cd /tmp/ && \
    python setup_grizli.py

## Eazy-py
RUN cd /tmp/ && \
    source ${VIRTUAL_ENV}/bin/activate && \
    git clone https://github.com/gbrammer/eazy-py.git && \
    cd eazy-py && \
    python setup.py install && \
    cd ../ && \
    rm -rf eazy-py

## Prospector for grizli + eazy, just uses the smoothing function....
RUN cd /tmp/ && \
    source ${VIRTUAL_ENV}/bin/activate && \
    git clone https://github.com/bd-j/prospector.git && \
    cd prospector && \
    python setup.py install && \
    cd ../ && \
    rm -rf prospector

### SQL tools
RUN source ${VIRTUAL_ENV}/bin/activate && \
    pip install setuptools && \
    pip install pandas && \
    pip install sqlalchemy && \
    cd /tmp/ && \
    git clone https://github.com/jkehler/awslambda-psycopg2.git && \
    mkdir /venv/lib/python3.6/site-packages/psycopg2 && \
    cp awslambda-psycopg2/psycopg2-3.6/* /venv/lib/python3.6/site-packages/psycopg2/
    
### Problem with paths
RUN mv /venv/lib/python3.6/site-packages/stsci/skypac /venv/lib64/python3.6/site-packages/stsci/ && \
    mv /venv/lib/python3.6/site-packages/stsci/tools /venv/lib64/python3.6/site-packages/stsci/
   
############
## Final stripped and zipped virtual environment
ADD ./Install/process.py ${VIRTUAL_ENV}/
ADD ./Install/aws_drizzler.py ${VIRTUAL_ENV}/

ADD ./Install/db.yml ${VIRTUAL_ENV}/lib64/python3.6/site-packages/grizli/data/

ADD ./Install/package_venv.sh /tmp/
RUN source ${VIRTUAL_ENV}/bin/activate && \
    cd /tmp/ && \
    bash /tmp/package_venv.sh ${VIRTUAL_ENV}

#############
## Install boto3 for testing, credentials file
RUN source ${VIRTUAL_ENV}/bin/activate && \
    pip install boto3 && \
    mkdir ~/.aws/ && \
    echo "Put AWS credentials in ~/.aws/credentials"

ADD ./Install/aws_credentials ~/.aws/credentials

ADD ./Install/add_workdir_python /usr/local/bin/add_workdir_python

# ############
# ## Working directory for passing data in/out
# RUN mkdir /workdir

#############
# REF directories
RUN mkdir /tmp/iref && \
    mkdir /tmp/uref && \
    mkdir /tmp/jref

ENV iref /tmp/iref/
ENV jref /tmp/jref/
ENV uref /tmp/uref/
     
CMD [ "/bin/bash" ]