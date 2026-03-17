import asyncio


class TaskManager:
    def __init__(self):
        self.single_tasks: dict[any, asyncio.Task] = {}
        self.single_tasks_lock = asyncio.Lock()
        self.tasks: dict[any, list[asyncio.Task]] = {}
        self.lock = asyncio.Lock()

        self._cleanup_task: asyncio.Task | None = None
        self.start_cleanup_loop(60)
    
    async def start_single_async_task(self, key: any, action: callable, *args, **kwargs) -> asyncio.Task:
        async with self.single_tasks_lock:
            existing = self.single_tasks.get(key)
            if existing is not None and not existing.done():
                return existing

            task = asyncio.create_task(action(*args, **kwargs))
            self.single_tasks[key] = task
            return task
    
    async def stop_single_async_task(self, key: any):
        async with self.single_tasks_lock:
            if key in self.single_tasks:
                self.single_tasks[key].cancel()
                self.single_tasks.pop(key)
    
    async def start_async_task(self, key: any, action: callable, *args, **kwargs):
        async with self.lock:
            if key not in self.tasks:
                self.tasks[key] = []
            task = asyncio.create_task(action(*args, **kwargs))
            self.tasks[key].append(task)
        return task
    
    async def stop_async_task(self, key: any):
        async with self.lock:
            if key in self.tasks:
                for task in self.tasks[key]:
                    task.cancel()
                self.tasks.pop(key)
    
    def start_schedule_task(
        self, key: any, interval_seconds: float, action: callable, *args, **kwargs
    ) -> asyncio.Task:
        async def scheduler(*args, **kwargs):
            while True:
                result = await action(*args, **kwargs)
                if not result:
                    break
                await asyncio.sleep(interval_seconds)

        return self.start_async_task(key, scheduler, *args, **kwargs)
    
    def start_single_schedule_task(
        self, key: any, interval_seconds: float, action: callable, *args, **kwargs
    ) -> asyncio.Task:
        async def scheduler(*args, **kwargs):
            while True:
                await asyncio.sleep(interval_seconds)
                result = await action(*args, **kwargs)
                if not result:
                    break
        
        return self.start_single_async_task(key, scheduler, *args, **kwargs)

    async def cleanup_finished_tasks(self) -> None:
        async with self.single_tasks_lock:
            finished_single_keys = [k for k, t in self.single_tasks.items() if t.done()]
            for k in finished_single_keys:
                self.single_tasks.pop(k, None)

        async with self.lock:
            empty_keys: list[any] = []
            for k, task_list in self.tasks.items():
                self.tasks[k] = [t for t in task_list if not t.done()]
                if not self.tasks[k]:
                    empty_keys.append(k)
            for k in empty_keys:
                self.tasks.pop(k, None)

    def start_cleanup_loop(self, interval_seconds: float = 60.0) -> asyncio.Task:
        if self._cleanup_task is not None and not self._cleanup_task.done():
            return self._cleanup_task

        async def _loop():
            while True:
                await asyncio.sleep(interval_seconds)
                await self.cleanup_finished_tasks()

        self._cleanup_task = asyncio.create_task(_loop())
        return self._cleanup_task
