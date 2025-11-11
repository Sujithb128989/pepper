import asyncio
from twisted.internet import defer

def deferred_to_future(d: defer.Deferred) -> asyncio.Future:
    """Converts a Twisted Deferred to an asyncio Future."""
    future = asyncio.Future()

    def success(result):
        future.set_result(result)

    def failure(err):
        future.set_exception(err.value)

    d.addCallbacks(success, failure)
    return future
