from fastapi import WebSocket
import asyncio

class voice_ConnectionManager:
    def __init__(self):

        # 当前所有在线 websocket 连接
        # 结构：
        # {
        #     session_id: {
        #         user_id: websocket
        #     }
        # }
        self.active_connections: dict[int, dict[int, WebSocket]] = {} 

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


    async def connect(self, session_id: int, user_id: int, websocket: WebSocket):

        # 接受 websocket 连接
        await websocket.accept()

        # 加锁
        #
        # 保证同一时刻只有一个协程能修改 active_connections
        async with self.lock:

            # 如果这个 session 还不存在
            if session_id not in self.active_connections:

                # 初始化一个空字典
                self.active_connections[session_id] = {}

            # 将当前 websocket 加入该 session 的连接池
            self.active_connections[session_id][user_id] = websocket

    
    async def disconnect(self, session_id: int, user_id: int, websocket: WebSocket):

        # 加锁
        async with self.lock:

            # 如果该 session 存在
            if session_id in self.active_connections:

                # 如果 websocket 在连接列表中
                if user_id in self.active_connections[session_id]:

                    # 删除该 websocket
                    del self.active_connections[session_id][user_id]

                # 如果这个 session 已经没人在线
                if not self.active_connections[session_id]:

                    # 删除整个 session
                    del self.active_connections[session_id]

    
    async def close(self, session_id: int):

        # 加锁
        #
        # 使用 pop：
        # - 一次性取出整个 session 的 websocket
        # - 同时从 active_connections 删除
        #
        # 如果 session 不存在
        # 返回空字典
        async with self.lock:

            connections_dict = self.active_connections.pop(
                session_id,
                {}
            )

            # connections_dict 的结构：
            # {
            #     user_id: websocket,
            #     ...
            # }
            #
            # values() 取出所有 websocket
            connections = list(
                connections_dict.values()
            )

        # 注意：
        # websocket.close() 不放在 lock 里面
        #
        # 因为关闭连接可能比较慢
        # 如果放在锁里面
        # 会阻塞其它 websocket 操作
        for connection in connections:

            try:

                # 强制关闭 websocket
                await connection.close()

            except Exception:

                # 如果 websocket 本来已经断开
                # 忽略错误
                pass


    async def send_to_others(self,session_id: int,sender_user_id: int,message: dict):

        # 加锁
        #
        # 这里只复制当前 session 的连接
        # 不在锁里面真正发送消息
        async with self.lock:

            # copy 非常关键
            #
            # 否则：
            # 一边遍历
            # 一边 disconnect 删除 websocket
            #
            # 容易产生并发问题
            connections = self.active_connections.get(
                session_id,
                {}
            ).copy()

        # 保存发送失败的 user_id
        disconnected_user_ids = []

        # 遍历当前 session 所有 websocket
        for user_id, connection in connections.items():

            # 自己发送的消息
            # 不需要再发回自己
            if user_id == sender_user_id:
                continue

            try:

                # 转发 signaling 消息
                await connection.send_json(message)

            except Exception:

                # 如果发送失败
                # 说明 websocket 已经断开
                disconnected_user_ids.append(user_id)

        # 清理已经断开的 websocket
        for user_id in disconnected_user_ids:

            # disconnect 内部会自行加锁
            await self.disconnect(
                session_id,
                user_id
            )

manager = voice_ConnectionManager()