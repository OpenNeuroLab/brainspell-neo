FROM python:3
ADD . /brainspell-neo
WORKDIR /brainspell-neo 
EXPOSE 5000
ENV PATH /opt/conda/envs/brainspell/bin:$PATH
#RUN source activate brainspell
# RUN apt-get -y install python-dev libpq-dev
# RUN conda install pip
# RUN conda install pycurl tornado psycopg2 simplejson biopython
RUN pip install -r requirements.txt
# RUN conda install -c conda-forge peewee=2.8.5
#RUN apt-get -y install gcc
#RUN pip install -r requirements2.txt
CMD ["python", "json_api/brainspell.py"]