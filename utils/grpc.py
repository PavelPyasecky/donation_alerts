import logging
from collections import namedtuple

import grpc

from configs import config


_ClientCallDetails = namedtuple(
    "_ClientCallDetails",
    ("method", "timeout", "metadata", "credentials", "wait_for_ready"),
)


class GRPCAuthInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    def __init__(self, header_name: str = "authorization", token: str = None):
        self._header_name = header_name
        self._token = token

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        metadata = list(client_call_details.metadata or [])
        metadata.append((self._header_name, self._token))

        new_details = _ClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
        )
        return await continuation(new_details, request)


def handle_grpc_errors(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except grpc.aio.AioRpcError as e:
            code = e.code()
            details = e.details()

            match code:
                case grpc.StatusCode.NOT_FOUND:
                    return None
                case grpc.StatusCode.INVALID_ARGUMENT:
                    raise ValueError(f"Invalid gRPC request: {details}")
                case grpc.StatusCode.PERMISSION_DENIED:
                    raise PermissionError(f"gRPC call permission denied: {details}")
                case _:
                    logging.error(f"gRPC call failed: {details}", exc_info=True)
                    return None
        except Exception as e:
            logging.error(f"Unexpected error in gRPC client: {e}", exc_info=True)
            raise e

    return wrapper


class GRPCClient:
    def __init__(self, url):
        self.channel = grpc.aio.insecure_channel(
            url, interceptors=[GRPCAuthInterceptor(config.GRPC_AUTH_HEADER_NAME, config.GRPC_AUTH_TOKEN)]
        )
