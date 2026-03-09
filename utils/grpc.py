import logging
import grpc


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
                case _:
                    raise RuntimeError(f"gRPC call failed: {details}")
        except Exception as e:
            logging.error(f"Unexpected error in gRPC client: {e}", exc_info=True)
            raise e

    return wrapper
