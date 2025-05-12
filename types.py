#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A协议核心数据类型
提供A2A协议所需的所有数据结构定义
"""
from typing import Union, Any, Dict, List
from pydantic import BaseModel, Field, TypeAdapter
from typing import Literal, Annotated, Optional
from datetime import datetime
from pydantic import model_validator, ConfigDict, field_serializer
from uuid import uuid4
from enum import Enum
from typing_extensions import Self


class TaskState(str, Enum):
    """任务状态枚举"""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"
    UNKNOWN = "unknown"


class TextPart(BaseModel):
    """文本类型的消息部分"""
    type: Literal["text"] = "text"
    text: str
    metadata: Dict[str, Any] | None = None


class FileContent(BaseModel):
    """文件内容"""
    name: str | None = None
    mimeType: str | None = None
    bytes: str | None = None
    uri: str | None = None

    @model_validator(mode="after")
    def check_content(self) -> Self:
        if not (self.bytes or self.uri):
            raise ValueError("Either 'bytes' or 'uri' must be present in the file data")
        if self.bytes and self.uri:
            raise ValueError(
                "Only one of 'bytes' or 'uri' can be present in the file data"
            )
        return self


class FilePart(BaseModel):
    """文件类型的消息部分"""
    type: Literal["file"] = "file"
    file: FileContent
    metadata: Dict[str, Any] | None = None


class DataPart(BaseModel):
    """数据类型的消息部分"""
    type: Literal["data"] = "data"
    data: Dict[str, Any]
    metadata: Dict[str, Any] | None = None


Part = Annotated[Union[TextPart, FilePart, DataPart], Field(discriminator="type")]


class Message(BaseModel):
    """消息"""
    role: Literal["user", "agent"]
    parts: List[Part]
    metadata: Dict[str, Any] | None = None


class TaskStatus(BaseModel):
    """任务状态"""
    state: TaskState
    message: Message | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_serializer("timestamp")
    def serialize_dt(self, dt: datetime, _info):
        return dt.isoformat()


class Artifact(BaseModel):
    """结果构件"""
    name: str | None = None
    description: str | None = None
    parts: List[Part]
    metadata: Dict[str, Any] | None = None
    index: int = 0
    append: bool | None = None
    lastChunk: bool | None = None


class Task(BaseModel):
    """任务"""
    id: str
    session: Dict[str, str] | None = None
    status: TaskStatus
    artifacts: List[Artifact] | None = None
    messages: List[Message] | None = None
    metadata: Dict[str, Any] | None = None


class TaskStatusUpdateEvent(BaseModel):
    """任务状态更新事件"""
    id: str
    status: TaskStatus
    final: bool = False
    metadata: Dict[str, Any] | None = None


class TaskArtifactUpdateEvent(BaseModel):
    """任务构件更新事件"""
    id: str
    artifact: Artifact    
    metadata: Dict[str, Any] | None = None


class AuthenticationInfo(BaseModel):
    """认证信息"""
    model_config = ConfigDict(extra="allow")

    schemes: List[str]
    credentials: str | None = None


class PushNotificationConfig(BaseModel):
    """推送通知配置"""
    url: str
    token: str | None = None
    authentication: AuthenticationInfo | None = None


class TaskIdParams(BaseModel):
    """任务ID参数"""
    id: str
    metadata: Dict[str, Any] | None = None


class TaskQueryParams(TaskIdParams):
    """任务查询参数"""
    historyLength: int | None = None


class TaskSendParams(BaseModel):
    """发送任务参数"""
    id: str = Field(default_factory=lambda: uuid4().hex)
    session: Dict[str, str] = Field(default_factory=lambda: {"id": uuid4().hex})
    messages: List[Message]
    historyLength: int | None = None
    metadata: Dict[str, Any] | None = None


## RPC消息

class JSONRPCMessage(BaseModel):
    """JSON-RPC消息基类"""
    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None = Field(default_factory=lambda: uuid4().hex)


class JSONRPCRequest(JSONRPCMessage):
    """JSON-RPC请求"""
    method: str
    params: Dict[str, Any] | None = None


class JSONRPCError(BaseModel):
    """JSON-RPC错误"""
    code: int
    message: str
    data: Any | None = None


class JSONRPCResponse(JSONRPCMessage):
    """JSON-RPC响应"""
    result: Any | None = None
    error: JSONRPCError | None = None


class SendTaskRequest(JSONRPCRequest):
    """发送任务请求"""
    method: Literal["tasks/send"] = "tasks/send"
    params: TaskSendParams


class SendTaskResponse(JSONRPCResponse):
    """发送任务响应"""
    result: Task | None = None


class GetTaskRequest(JSONRPCRequest):
    """获取任务请求"""
    method: Literal["tasks/get"] = "tasks/get"
    params: TaskQueryParams


class GetTaskResponse(JSONRPCResponse):
    """获取任务响应"""
    result: Task | None = None


## 错误类型

class A2AError(Exception):
    """A2A错误基类"""
    pass


class A2AClientError(A2AError):
    """A2A客户端错误"""
    pass


class A2AClientHTTPError(A2AClientError):
    """A2A客户端HTTP错误"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP Error {status_code}: {message}")


class A2AClientJSONError(A2AClientError):
    """A2A客户端JSON错误"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"JSON Error: {message}") 