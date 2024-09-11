FROM ros:kinetic
LABEL maintainer Kyle Usbeck

# Trick to get apt-get to not prompt for timezone in tzdata
ENV DEBIAN_FRONTEND=noninteractive

ARG STARTDELAY=5
ENV STARTDELAY=$STARTDELAY

# Install MAVROS and some other dependencies for later
RUN apt-get update && apt-get install -y ros-kinetic-mavros ros-kinetic-mavros-extras ros-kinetic-mavros-msgs vim wget screen
RUN apt install -y ssh 
RUN apt install -y curl 
RUN curl https://bootstrap.pypa.io/pip/3.5/get-pip.py -o get-pip.py
RUN apt install -y python3-dev 

RUN apt-get install python-catkin-tools python-rosinstall-generator -y
RUN python3 get-pip.py
# RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install numpy==1.16 
RUN pip3 install -U rosdep rosinstall_generator wstool rosinstall

# Dependency from https://github.com/mavlink/mavros/blob/master/mavros/README.md
RUN wget https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh
RUN chmod +x install_geographiclib_datasets.sh
RUN ./install_geographiclib_datasets.sh

# Fix the broken apm_config.yaml
COPY apm_config.yaml /opt/ros/kinetic/share/mavros/launch/apm_config.yaml

# MAVLink Input
EXPOSE 5760

# Envs
ENV FCUURL=tcp://localhost:5760

# Finally the command
COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT /entrypoint.sh ${FCUURL}
