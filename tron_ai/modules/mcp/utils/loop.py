import asyncio
import logging
import threading
from typing import Callable, Coroutine
import queue

from concurrent.futures import Future

logger = logging.getLogger(__name__)


class EventLoopManager:
    """
    Manages a single event loop running in a dedicated thread.
    Provides thread-safe methods to submit coroutines to this loop.
    """

    def __init__(self):
        self._loop = None
        self._thread = None
        self._running = False
        self._tasks = queue.Queue()
        self._results = {}
        self._lock = threading.Lock()
        self._task_id = 0
        self._exception_callbacks = []

    def start(self):
        """Start the event loop in a dedicated thread"""
        if self._running:
            logger.warning("EventLoopManager is already running")
            return

        with self._lock:
            if self._running:
                return

            self._running = True
            self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self._thread.start()
            logger.info("EventLoopManager started")

    def stop(self):
        """Stop the event loop and clean up resources"""
        if not self._running:
            return

        with self._lock:
            if not self._running:
                return

            self._running = False

            # Add a dummy task to unblock the event loop if it's waiting
            future = Future()
            self._tasks.put((lambda: None, future, None))

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
            logger.info("EventLoopManager stopped")

    def submit(self, coro_func: Callable[[], Coroutine]) -> Future:
        """
        Submit a coroutine factory function to be executed in the event loop.

        Args:
            coro_func: A function that returns a coroutine when called

        Returns:
            Future object that will contain the result when completed
        """
        if not self._running:
            self.start()

        future = Future()

        with self._lock:
            task_id = self._task_id
            self._task_id += 1

        self._tasks.put((coro_func, future, task_id))
        return future

    def _run_event_loop(self):
        """Main loop that runs in the dedicated thread"""
        try:
            # Create new event loop for this thread
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # Run the event loop processor
            self._loop.run_until_complete(self._process_tasks())
        except Exception as e:
            logger.error(f"Error in event loop thread: {str(e)}")
        finally:
            # Clean up
            try:
                if self._loop and not self._loop.is_closed():
                    pending = asyncio.all_tasks(self._loop)
                    for task in pending:
                        task.cancel()

                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                    self._loop.close()
            except Exception as e:
                logger.error(f"Error cleaning up event loop: {str(e)}")

            self._loop = None
            self._running = False
            logger.info("Event loop thread terminated")

    async def _process_tasks(self):
        """Process tasks from the queue until stopping is requested"""
        pending_tasks = set()

        while self._running:
            # Process all available tasks
            while not self._tasks.empty() and self._running:
                try:
                    coro_func, future, task_id = self._tasks.get_nowait()

                    if coro_func is None:
                        continue

                    # Create the actual coroutine
                    try:
                        coro = coro_func()
                        task = asyncio.create_task(
                            self._run_task(coro, future, task_id)
                        )
                        pending_tasks.add(task)
                        task.add_done_callback(lambda t: pending_tasks.discard(t))
                    except Exception as e:
                        future.set_exception(e)

                except queue.Empty:
                    break

            # Wait a bit before checking for new tasks
            await asyncio.sleep(0.01)

        # Process remaining tasks before shutting down
        while not self._tasks.empty():
            try:
                coro_func, future, task_id = self._tasks.get_nowait()
                if future and not future.done():
                    future.cancel()
            except queue.Empty:
                break

        # Wait for pending tasks to complete
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)

    async def _run_task(self, coro, future, task_id):
        """Execute a coroutine and set its result in the corresponding future"""
        try:
            result = await coro
            if not future.cancelled():
                future.set_result(result)
        except asyncio.CancelledError:
            if not future.cancelled():
                future.cancel()
        except Exception as e:
            if not future.cancelled():
                future.set_exception(e)

            # Call exception callbacks
            for callback in self._exception_callbacks:
                try:
                    callback(e, task_id)
                except Exception as cb_error:
                    logger.error(f"Error in exception callback: {str(cb_error)}")

    def add_exception_callback(self, callback):
        """Add a callback to be called when a task raises an exception"""
        self._exception_callbacks.append(callback)

    def run_sync(self, coro_func):
        """
        Run a coroutine synchronously, blocking until it completes

        Args:
            coro_func: A function that returns a coroutine when called

        Returns:
            The result of the coroutine

        Raises:
            Any exception raised by the coroutine
        """
        future = self.submit(coro_func)
        return future.result()

