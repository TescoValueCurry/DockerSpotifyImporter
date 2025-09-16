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
    print('DBWorker initialized')

    def run(self):
        while self.running:
            req = self.queue.get()
            if req is None:
                print('db worker received shutdown signal')
                break
            func_name = getattr(req.func, '__name__', str(req.func))
            # print(f'db worker received request: {func_name} args={req.args} kwargs={req.kwargs}')
            try:
                # print(f'db worker starting: {func_name}')
                result = req.func(self.db, *req.args, **req.kwargs)
                self.db.commit()
                # print(f'db worker committed: {func_name}')
                req.set_result(result)
            except Exception as e:
                self.db.rollback()
                # print(f'db worker rolled back: {func_name} error={e}')
                req.set_exception(e)
            finally:
                # print(f'db worker finished: {func_name}')
                self.queue.task_done()
        print('db worker closed session')
        self.db.close()

    def submit(self, func, *args, wait_for_result=True, **kwargs):
    # print(f'Submitting task: {getattr(func, "__name__", str(func))} with args={args} kwargs={kwargs} wait_for_result={wait_for_result}')
        req = DBRequest(func, args, kwargs, wait_for_result)
        self.queue.put(req)
        result = req.get() if wait_for_result else None
        if wait_for_result:
            # print(f'Result for {getattr(func, "__name__", str(func))}: {result}')
            pass
        return result


    def stop(self):
        print('Stopping DBWorker')
        self.running = False
        self.queue.put(None)

 # global db worker instance
db_worker = DBWorker()
db_worker.start()
