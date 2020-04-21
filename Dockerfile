FROM lambci/lambda:build-python3.7
WORKDIR /build
RUN rm -rf *
COPY deployment_requirements.txt .
RUN mkdir pkgs && pip3 install -r deployment_requirements.txt -t pkgs/
CMD ["/bin/bash"]