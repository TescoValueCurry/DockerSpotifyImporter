import threading
from queue import Queue
from database import SessionLocal

class DBRequest:
    def __init__(self, func, args=(), kwargs=None, wait_for_result=True):
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.wait_for_result = wait_for_result
        self.result = None
        self.exception = None
        self._event = threading.Event() if wait_for_result else None

    def set_result(self, result):
        self.result = result
        if self._event:
            self._event.set()

    def set_exception(self, exc):
        self.exception = exc
        if self._event:
            self._event.set()

    def get(self):
        if self._event:
            self._event.wait()
            if self.exception:
                raise self.exception
            return self.result
        return None

class DBWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.queue = Queue()
        self.db = SessionLocal()
        self.running = True
        print('DBWorker initialized', flush=True)

    def run(self):
        while self.running:
            req = self.queue.get()
            if req is None:
                print('db worker received shutdown signal', flush=True)
                break
            func_name = getattr(req.func, '__name__', str(req.func))
            try:
                result = req.func(self.db, *req.args, **req.kwargs)

                # Only commit if function is not marked as read-only
                requires_commit = getattr(req.func, 'requires_commit', True)
                if requires_commit:
                    self.db.commit()

                req.set_result(result)
            except Exception as e:
                self.db.rollback()
                req.set_exception(e)
            finally:
                self.queue.task_done()
        print('db worker closed session', flush=True)
        self.db.close()

    def submit(self, func, *args, wait_for_result=True, **kwargs):
        req = DBRequest(func, args, kwargs, wait_for_result)
        self.queue.put(req)
        result = req.get() if wait_for_result else None
        return result

    def stop(self):
        print('Stopping DBWorker', flush=True)
        self.running = False
        self.queue.put(None)

# global db worker instance
db_worker = DBWorker()
db_worker.start()
