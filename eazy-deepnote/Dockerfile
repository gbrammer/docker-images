#  docker build . -t gbrammer/eazy-deepnote:latest
#  docker run --rm -it gbrammer/eazy-deepnote:latest /bin/bash

FROM deepnote/python:3.7

RUN pip install plotly h5py matplotlib numpy scipy pandas astropy
RUN pip install awscli boto3
RUN pip install pyyaml sep stwcs
RUN pip install peakutils shapely pyregion 
RUN pip install photutils==1.0.*
RUN pip install drizzlepac

### JWST pipeline
# RUN pip install pandeia.engine jwst

RUN pip install git+https://github.com/gbrammer/astroquery.git

RUN git clone https://github.com/gbrammer/eazy-py.git --recurse-submodules
RUN cd eazy-py && pip install . -r requirements.txt

RUN git clone https://github.com/gbrammer/grizli.git --recurse-submodules
RUN cd grizli && pip install .  

RUN pip install git+https://github.com/gbrammer/tristars.git 
RUN pip install git+https://github.com/gbrammer/mastquery.git

RUN pip install git+https://github.com/bd-j/sedpy.git
RUN pip install git+https://github.com/bd-j/prospector.git
RUN pip install git+https://github.com/gbrammer/dust_attenuation.git
RUN pip install git+https://github.com/gbrammer/dust_extinction.git

# FSPS
RUN sudo apt-get update
RUN sudo apt-get install -y less gfortran

RUN git clone https://github.com/cconroy20/fsps.git
RUN cd fsps/src && make

ENV SPS_HOME ${HOME}/fsps/
RUN pip install git+https://github.com/gbrammer/python-fsps.git

RUN pip cache purge