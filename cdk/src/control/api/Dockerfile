# Define function directory
ARG FUNCTION_DIR="/var/task"

FROM public.ecr.aws/lambda/python:3.9

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Install the runtime interface client
RUN pip install \
  --target ${FUNCTION_DIR} \
  awslambdaric

COPY requirements.txt ${FUNCTION_DIR}/requirements.txt

RUN pip install \
  --target ${FUNCTION_DIR} \
  -r ${FUNCTION_DIR}/requirements.txt

# Copy function code
COPY . ${FUNCTION_DIR}

#ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "handler.app" ]