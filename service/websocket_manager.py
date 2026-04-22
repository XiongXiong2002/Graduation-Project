from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # 存储当前所有在线连接
        # 结构：{session_id: [websocket1, websocket2, ...]}
        # 表示每个会话里有哪些用户在线（通过 websocket 表示）
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, session_id: int, websocket: WebSocket):
        # 接受 WebSocket 连接（必须调用，否则前端无法建立连接）
        await websocket.accept()

        # 如果这个 session 还没有任何连接，初始化一个列表
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []

        # 将当前 websocket 加入该 session 的在线列表
        self.active_connections[session_id].append(websocket)

    def disconnect(self, session_id: int, websocket: WebSocket):
        # 如果该 session 存在于连接管理中
        if session_id in self.active_connections:
            # 如果该 websocket 在这个 session 的连接列表中
            if websocket in self.active_connections[session_id]:
                # 从列表中移除该连接（用户离开）
                self.active_connections[session_id].remove(websocket)

            # 如果这个 session 已经没有任何在线连接了
            if not self.active_connections[session_id]:
                # 删除该 session，释放内存
                del self.active_connections[session_id]

    async def broadcast(self, session_id: int, message: dict):
        # 如果该 session 当前有在线用户
        if session_id in self.active_connections:
            # 用来记录发送失败（断开的连接）
            disconnected = []

            # 遍历该 session 中的所有 websocket 连接
            for connection in self.active_connections[session_id]:
                try:
                    # 向每一个连接发送消息（实时推送）
                    await connection.send_json(message)
                except:
                    # 如果发送失败（说明连接已断开），先记录下来
                    disconnected.append(connection)

            # 清理所有已经断开的连接
            for connection in disconnected:
                self.disconnect(session_id, connection)