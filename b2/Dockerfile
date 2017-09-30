FROM python:3
ADD .  /brainspell-neo



WORKDIR /brainspell-neo
EXPOSE 5000

RUN ls

COPY /brainspell-neo/requirements.txt .
RUN pip3 install -r /brainspell-neo/requirements.txt

#COPY requirements.txt /tmp/
#RUN pip3 install -r /tmp/requirements.txt
#COPY . /tmp/
# RUN pip install -r requirements.txt

CMD ["python3", "brainspell.py", "-p5000"]
