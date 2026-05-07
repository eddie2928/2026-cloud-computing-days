#!/usr/bin/env bash
# Generate Python gRPC stubs from proto/inspect.proto
# Run from project root: bash scripts/gen_proto.sh
set -e

pip install grpcio-tools --quiet
python -m grpc_tools.protoc \
    -I proto \
    --python_out=src/agentbox/grpc \
    --grpc_python_out=src/agentbox/grpc \
    proto/inspect.proto

# Fix relative import in generated grpc file
sed -i 's/^import inspect_pb2/from agentbox.grpc import inspect_pb2/' \
    src/agentbox/grpc/inspect_pb2_grpc.py

echo "gRPC stubs generated in src/agentbox/grpc/"
