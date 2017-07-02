FROM python:3
ADD . /brainspell-neo
WORKDIR /brainspell-neo 
EXPOSE 5000
ENV PATH /opt/conda/envs/brainspell/bin:$PATH
RUN pip install -r requirements.txt
#Run Postgres Locally 
RUN apt install -y postgresql-9.6
RUN postgres restore database_dumps/brainspell.pgsql
CMD ["python3", "json_api/brainspell.py", "-p5000"]