#!/usr/bin/bash
docker run -it --rm -p 8888:8888 --name jcq -p 5555:5555 bwalter42/jupyter_cadquery:3.5.2 -v