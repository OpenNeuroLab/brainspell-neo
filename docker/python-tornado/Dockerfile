FROM python:3
ADD . /brainspell-neo
ADD . /brainspell-neo/brainspell/brainspell.py
ADD . /brainspell-neo/requirements.txt
WORKDIR /brainspell-neo
EXPOSE 5000
ENV PATH /opt/conda/envs/brainspell/bin:$PATH


CMD ["pip3 install", "requirements.txt"]
#RUN pip install -r requirements.txt

CMD ["python3", "brainspell.py", "-p5000"]
