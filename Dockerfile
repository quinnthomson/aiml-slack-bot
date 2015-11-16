FROM ubuntu
MAINTAINER quinn.thomson@robotsandpencils.com

# Install python
RUN apt-get install -qy python
RUN apt-get update
RUN apt-get install -qy python-pip

# Install dependencies
RUN pip install requests
RUN pip install websocket-client
RUN pip install importlib
RUN pip install slacker

# Add python slack bot vode
ADD . /python-slack-bot
WORKDIR python-slack-bot
RUN pip install .

# use this to test a SLACK_TOKEN environment variable
# ENV SLACK_TOKEN ###token###

# Run the slack bot
RUN python run.py
