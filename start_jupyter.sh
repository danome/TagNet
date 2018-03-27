#!/bin/sh
#cd o/Open/TagNet/
sudo jupyter nbextension enable --py --sys-prefix widgetsnbextension
jupyter nbextension enable --py gmaps
nohup jupyter notebook --no-browser --port=8999 &
