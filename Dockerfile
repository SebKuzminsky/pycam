FROM debian:9

COPY . /root/pycam

RUN apt-get update && apt-get install -y python3 \
    python3-gi \
    python3-opengl \
    python3-yaml \
    gir1.2-gtk-3.0

CMD [ "/root/pycam/pycam/run_gui.py" ]
