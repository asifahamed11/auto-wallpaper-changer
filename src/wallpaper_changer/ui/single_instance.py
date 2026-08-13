from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QIODevice, QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    def __init__(self, name: str, on_activate: Callable[[], None]):
        super().__init__()
        self.name = name
        self.on_activate = on_activate
        self.server: QLocalServer | None = None

    def notify_existing(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self.name, QIODevice.OpenModeFlag.WriteOnly)
        if not socket.waitForConnected(300):
            return False
        socket.write(b"show")
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        return True

    def listen(self) -> None:
        QLocalServer.removeServer(self.name)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._accept)
        if not self.server.listen(self.name):
            raise RuntimeError(f"Could not create the local app server: {self.server.errorString()}")

    def _accept(self) -> None:
        if not self.server:
            return
        socket = self.server.nextPendingConnection()
        if socket:
            socket.waitForReadyRead(100)
            self.on_activate()
            socket.disconnectFromServer()
