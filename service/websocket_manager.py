from fastapi import WebSocket
import asyncio


class ConnectionManager:
    def __init__(self):

        # 当前所有在线 websocket 连接
        # 结构：
        # {
        #     session_id: [websocket1, websocket2, ...]
        # }
        self.active_connections: dict[int, list[WebSocket]] = {}

        # asyncio 异步锁
        #
        # 用来保护 active_connections 这个共享数据结构
        #
        # 否则可能出现：
        # - 一边 broadcast 遍历 list
        # - 一边 disconnect 删除 websocket
        #
        # 导致并发问题
        self.lock = asyncio.Lock()

    async def connect(self, session_id: int, websocket: WebSocket):

        # 接受 websocket 连接
        await websocket.accept()

        # 加锁
        #
        # 保证同一时刻只有一个协程能修改 active_connections
        async with self.lock:

            # 如果这个 session 还不存在
            if session_id not in self.active_connections:

                # 初始化一个空列表
                self.active_connections[session_id] = []

            # 将当前 websocket 加入该 session 的连接池
            self.active_connections[session_id].append(websocket)

    async def disconnect(self, session_id: int, websocket: WebSocket):

        # 加锁
        async with self.lock:

            # 如果该 session 存在
            if session_id in self.active_connections:

                # 如果 websocket 在连接列表中
                if websocket in self.active_connections[session_id]:

                    # 删除该 websocket
                    self.active_connections[session_id].remove(websocket)

                # 如果这个 session 已经没人在线
                if not self.active_connections[session_id]:

                    # 删除整个 session
                    del self.active_connections[session_id]

    async def close(self, session_id: int):

        # 加锁
        #
        # 这里使用 pop：
        # - 直接取出整个连接列表
        # - 同时从 active_connections 删除
        #
        # 如果 session 不存在，返回空列表
        async with self.lock:

            connections = self.active_connections.pop(
                session_id,
                []
            ).copy()

        # 注意：
        # websocket.close() 不放在 lock 里面
        #
        # 因为关闭连接可能很慢
        # 如果放在锁里，会卡住整个系统
        for connection in connections:

            try:
                # 强制关闭 websocket
                await connection.close()

            except Exception:
                # 如果连接本来就断了
                # 忽略错误
                pass

    async def broadcast(self, session_id: int, message: dict):

        # 加锁
        #
        # 这里只复制连接列表
        # 不在锁里真正发送消息
        async with self.lock:

            # copy 非常关键
            #
            # 否则：
            # 一边遍历
            # 一边 disconnect remove
            #
            # 会导致并发问题
            connections = self.active_connections.get(
                session_id,
                []
            ).copy()

        # 存储已经断开的 websocket
        disconnected = []

        # 遍历所有 websocket
        for connection in connections:

            try:
                # 向前端发送 json 消息
                await connection.send_json(message)

            except Exception:

                # 如果发送失败
                # 说明 websocket 已断开
                disconnected.append(connection)

        # 清理断开的 websocket
        for connection in disconnected:

            # disconnect 里面本身会加锁
            await self.disconnect(session_id, connection)


# 全局 websocket 管理器
#
# 整个项目只需要一个实例
manager = ConnectionManager()