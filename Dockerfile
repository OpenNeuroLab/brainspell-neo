FROM python:3
ADD . /brainspell-neo
ADD . /database_dumps/brainspell.pgsql
WORKDIR /brainspell-neo 
EXPOSE 5000
ENV PATH /opt/conda/envs/brainspell/bin:$PATH
RUN pip install -r requirements.txt
CMD ["python3", "brainspell/brainspell.py", "-p5000"]