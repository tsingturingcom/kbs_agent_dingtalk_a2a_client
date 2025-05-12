#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A客户端核心实现
负责与A2A服务通信的客户端逻辑
"""
import asyncio
import json
from typing import Any, AsyncIterable, Dict, List, Optional
import aiohttp
# 修改导入路径，防止与Python内置的types模块冲突
import types as a2a_types
from logger import info, error, debug


class A2AClient:
    """A2A协议客户端实现"""
    
    def __init__(self, url: str):
        """
        初始化A2A客户端
        
        Args:
            url (str): A2A服务端URL
        """
        self.url = url.rstrip('/')
        self.session = aiohttp.ClientSession(headers={"Content-Type": "application/json"})
    
    async def close(self):
        """关闭客户端会话"""
        await self.session.close()
    
    async def send_task(self, task_id: str, session_id: str, user_message: str) -> a2a_types.SendTaskResponse:
        """
        发送任务请求到A2A服务
        
        Args:
            task_id (str): 任务ID
            session_id (str): 会话ID
            user_message (str): 用户消息文本
            
        Returns:
            SendTaskResponse: 任务发送响应
        """
        # 构建消息对象
        message = a2a_types.Message(
            role="user",
            parts=[a2a_types.TextPart(text=user_message)]
        )
        
        # 构建请求参数
        payload = {
            "id": task_id,
            "session": {"id": session_id},
            "messages": [message.model_dump()]
        }
        
        # 创建请求对象
        request = a2a_types.SendTaskRequest(params=payload)
        
        # 发送请求
        response_data = await self._send_request(request)
        info(f"A2A服务返回响应: {response_data.get('id')}")
        
        # 返回响应对象
        return a2a_types.SendTaskResponse(**response_data)
    
    async def get_task(self, task_id: str) -> a2a_types.GetTaskResponse:
        """
        获取任务状态和结果
        
        Args:
            task_id (str): 任务ID
            
        Returns:
            GetTaskResponse: 任务响应
        """
        # 构建请求参数
        payload = {
            "id": task_id
        }
        
        # 创建请求对象
        request = a2a_types.GetTaskRequest(params=payload)
        
        # 发送请求
        response_data = await self._send_request(request)
        
        # 返回响应对象
        return a2a_types.GetTaskResponse(**response_data)
    
    async def _send_request(self, request: a2a_types.JSONRPCRequest) -> Dict[str, Any]:
        """
        发送JSON-RPC请求到A2A服务
        
        Args:
            request (JSONRPCRequest): 请求对象
            
        Returns:
            Dict[str, Any]: 服务器响应JSON数据
            
        Raises:
            A2AClientHTTPError: HTTP请求错误
            A2AClientJSONError: JSON解析错误
        """
        debug(f"向A2A服务发送请求: {self.url}, 方法: {request.method}")
        
        try:
            async with self.session.post(
                self.url, 
                json=request.model_dump(),
                timeout=120  # 任务可能需要较长时间处理
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    error(f"A2A请求失败，状态码: {response.status}, 响应: {error_text}")
                    raise a2a_types.A2AClientHTTPError(response.status, error_text)
                
                # 解析响应JSON
                try:
                    response_data = await response.json()
                    debug(f"A2A响应: {json.dumps(response_data, ensure_ascii=False)[:500]}")
                    return response_data
                except json.JSONDecodeError as e:
                    error(f"A2A响应JSON解析错误: {str(e)}")
                    raise a2a_types.A2AClientJSONError(str(e)) from e
                
        except aiohttp.ClientError as e:
            error(f"A2A请求网络错误: {str(e)}")
            raise a2a_types.A2AClientHTTPError(500, str(e)) from e
        except asyncio.TimeoutError as e:
            error(f"A2A请求超时: {str(e)}")
            raise a2a_types.A2AClientHTTPError(408, "Request timeout") from e
    
    async def check_health(self) -> bool:
        """
        检查A2A服务健康状态
        
        Returns:
            bool: 服务是否健康
        """
        agent_card_url = f"{self.url}/.well-known/agent.json"
        
        try:
            async with self.session.get(agent_card_url, timeout=10) as response:
                if response.status == 200:
                    try:
                        agent_card = await response.json()
                        debug(f"获取到A2A代理卡片: {agent_card.get('name', 'unknown')}")
                        return True
                    except json.JSONDecodeError:
                        error("A2A代理卡片JSON解析错误")
                else:
                    error(f"A2A服务健康检查失败，状态码: {response.status}")
                
                return False
        except Exception as e:
            error(f"A2A服务健康检查出错: {str(e)}")
            return False 