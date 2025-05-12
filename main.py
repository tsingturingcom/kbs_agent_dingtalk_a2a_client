#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉 A2A 客户端主程序
将钉钉消息转换为A2A协议请求，并将A2A响应发送回钉钉
"""

import os
import sys
import json
import uuid
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
import aiohttp
from datetime import datetime, timezone
import configparser

# 导入自定义模块
import logger
from config import config
from dingtalk_sender import DingTalkSender
from a2a_client import A2AClient
# 修改导入路径，防止与Python内置的types模块冲突
import types as a2a_types
# 导入数据库管理模块
from db_manager import db_manager

# 导入钉钉SDK
from dingtalk_stream import AckMessage, DingTalkStreamClient
from dingtalk_stream.credential import Credential
from dingtalk_stream.handlers import CallbackHandler
from dingtalk_stream.chatbot import ChatbotMessage

class DingTalkA2AClient:
    """钉钉A2A客户端主类，处理钉钉消息并转换为A2A协议请求"""
    
    def __init__(self):
        """初始化钉钉A2A客户端"""
        # 创建钉钉消息发送器
        self.sender = DingTalkSender()
        
        # 获取配置项
        self.robot_code = config.config.get('dingtalk_config', 'dingtalk_robot_code')
        
        # A2A服务端URL - 默认值
        self.default_a2a_server_url = config.config.get('a2a_config', 'a2a_server_url')
        logger.info(f"默认A2A服务端URL: {self.default_a2a_server_url}")
        
        # 创建A2A客户端 - 初始设置为默认服务器，作为系统级客户端
        self.a2a_client = A2AClient(url=self.default_a2a_server_url)
        
        # 用户A2A客户端映射 {user_id: (client, last_active_time)}
        self.user_a2a_clients = {}
        
        # 会话ID映射，用于跟踪用户会话
        self.session_mapping = {}
        
        # 命令处理函数映射
        self.command_handlers = {
            '/help': self.handle_help_command,
            '/server': self.handle_server_command,
            '/setserver': self.handle_setserver_command,
            '/resetserver': self.handle_resetserver_command,
        }
        
        # 从配置文件中读取客户端池参数
        try:
            # 使用config.get_config方法或直接访问configparser对象
            if hasattr(config, 'get_config'):
                cleanup_interval = config.get_config('client_pool_config', 'cleanup_interval', '3600')
                client_inactive_timeout = config.get_config('client_pool_config', 'client_inactive_timeout', '14400')
            else:
                cleanup_interval = config.config.get('client_pool_config', 'cleanup_interval', fallback='3600')
                client_inactive_timeout = config.config.get('client_pool_config', 'client_inactive_timeout', fallback='14400')
            
            self.cleanup_interval = int(cleanup_interval)
            self.client_inactive_timeout = int(client_inactive_timeout)
            logger.info(f"已加载客户端池配置: 清理间隔={self.cleanup_interval}秒, 超时时间={self.client_inactive_timeout}秒")
        except (ValueError, TypeError, configparser.NoSectionError) as e:
            logger.warning(f"读取客户端池配置出错，将使用默认值: {str(e)}")
            # 客户端清理间隔（秒）
            self.cleanup_interval = 3600  # 1小时
            # 客户端不活跃超时（秒）
            self.client_inactive_timeout = 3600 * 4  # 4小时不活跃就清理
    
    async def startup(self):
        """启动并运行钉钉A2A客户端"""
        logger.info("启动钉钉A2A客户端...")
        
        # 检查A2A服务健康状态
        is_healthy = await self.a2a_client.check_health()
        if not is_healthy:
            logger.error(f"A2A服务不可用，请检查服务是否启动: {self.default_a2a_server_url}")
            logger.info("将继续启动，但可能无法正常处理请求，直到A2A服务可用")
        else:
            logger.info("A2A服务健康检查通过")
        
        # 创建钉钉消息处理器
        class MessageHandler(CallbackHandler):
            def __init__(self, client):
                super().__init__()
                self.client = client
                # 获取机器人名称
                if config.config.has_option('dingtalk_config', 'robot_name'):
                    self.robot_name = config.config.get('dingtalk_config', 'robot_name')
                else:
                    self.robot_name = 'A2A助手'
            
            async def process(self, callback):
                """处理钉钉回调数据"""
                try:
                    # 解析回调数据
                    data = callback.data
                    logger.debug(f"接收到钉钉回调: {json.dumps(data, ensure_ascii=False)}")
                    
                    # 确保是文本消息
                    if 'text' not in data or 'senderStaffId' not in data:
                        logger.info("收到非文本消息，忽略。")
                        return AckMessage.STATUS_OK, "ignore: not a text message"
                    
                    # 提取消息内容
                    message_text = data.get('text', {}).get('content', '').strip()
                    sender_staff_id = data.get('senderStaffId')
                    sender_nick = data.get('senderNick', '未知用户')
                    conversation_id = data.get('conversationId')
                    conversation_type = data.get('conversationType')
                    
                    if not message_text or not sender_staff_id or not conversation_id:
                        logger.warning("收到的消息缺少必要字段，忽略。")
                        return AckMessage.STATUS_OK, "ignore: missing fields"
                    
                    # 处理单聊消息
                    if conversation_type == '1':  # 单聊
                        logger.info(f"收到来自 '{sender_nick}' ({sender_staff_id}) 的单聊消息: '{message_text[:50]}...'")
                        
                        # 创建后台任务处理消息
                        asyncio.create_task(
                            self.client.handle_text_message(
                                sender_staff_id=sender_staff_id,
                                sender_nick=sender_nick,
                                conversation_id=conversation_id,
                                message_text=message_text
                            )
                        )
                        
                        return AckMessage.STATUS_OK, "success (processing started)"
                    else:
                        logger.info(f"收到非单聊消息，暂不支持: {conversation_type}")
                        return AckMessage.STATUS_OK, "ignore: only supporting 1-to-1 chat"
                
                except Exception as e:
                    logger.error(f"处理钉钉消息时出错: {str(e)}", exc_info=True)
                    return AckMessage.STATUS_OK, "error during processing"
        
        # 获取钉钉机器人配置
        client_id = config.config.get('dingtalk_config', 'dingtalk_client_id')
        client_secret = config.config.get('dingtalk_config', 'dingtalk_client_secret')
        
        logger.info(f"配置钉钉Stream SDK (ClientID: {client_id})")
        credential = Credential(client_id, client_secret)
        client = DingTalkStreamClient(credential)
        
        # 创建处理器实例
        message_handler = MessageHandler(self)
        # 注册消息主题
        client.register_callback_handler(ChatbotMessage.TOPIC, message_handler)
        
        # 启动定期清理不活跃客户端的任务
        asyncio.create_task(self.cleanup_inactive_clients_task())
        
        logger.info("启动钉钉Stream连接...")
        client.start_forever()
    
    async def cleanup_inactive_clients_task(self):
        """定期清理不活跃的客户端连接任务"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_inactive_clients()
            except Exception as e:
                logger.error(f"清理不活跃客户端时出错: {str(e)}", exc_info=True)
    
    async def cleanup_inactive_clients(self):
        """清理不活跃的客户端连接"""
        current_time = time.time()
        clients_to_remove = []
        
        logger.info(f"开始清理不活跃客户端，当前有 {len(self.user_a2a_clients)} 个客户端")
        
        for user_id, (client, last_active) in self.user_a2a_clients.items():
            if current_time - last_active > self.client_inactive_timeout:
                clients_to_remove.append(user_id)
                logger.info(f"用户 {user_id} 的客户端已 {(current_time - last_active) / 3600:.1f} 小时不活跃，将被清理")
        
        for user_id in clients_to_remove:
            client, _ = self.user_a2a_clients[user_id]
            await client.close()
            del self.user_a2a_clients[user_id]
        
        logger.info(f"清理完成，移除了 {len(clients_to_remove)} 个不活跃客户端，剩余 {len(self.user_a2a_clients)} 个")
    
    async def get_user_a2a_client(self, user_id: str) -> A2AClient:
        """
        获取用户的A2A客户端实例
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户的A2A客户端实例
        """
        # 检查用户是否已有客户端
        if user_id in self.user_a2a_clients:
            client, _ = self.user_a2a_clients[user_id]
            # 更新最后活动时间
            self.user_a2a_clients[user_id] = (client, time.time())
            return client
            
        # 获取用户配置的服务器地址
        server_url = db_manager.get_user_key(
            user_id, 'a2a_server_url', self.default_a2a_server_url
        )
        
        logger.info(f"为用户 {user_id} 创建新的A2A客户端，服务器地址: {server_url}")
        
        # 创建新客户端
        client = A2AClient(url=server_url)
        # 存储客户端及当前时间
        self.user_a2a_clients[user_id] = (client, time.time())
        return client
    
    async def update_user_a2a_client(self, user_id: str, server_url: str) -> bool:
        """
        更新用户的A2A客户端
        
        Args:
            user_id: 用户ID
            server_url: 新的服务器地址
            
        Returns:
            更新是否成功
        """
        try:
            # 如果用户有现有客户端，关闭它
            if user_id in self.user_a2a_clients:
                old_client, _ = self.user_a2a_clients[user_id]
                await old_client.close()
                
            # 创建新客户端
            client = A2AClient(url=server_url)
            # 存储新客户端
            self.user_a2a_clients[user_id] = (client, time.time())
            
            logger.info(f"已更新用户 {user_id} 的A2A客户端，新地址: {server_url}")
            return True
        except Exception as e:
            logger.error(f"更新用户 {user_id} 的A2A客户端时出错: {str(e)}", exc_info=True)
            return False
    
    def get_user_session_id(self, user_id: str) -> str:
        """获取或创建用户的会话ID"""
        if user_id not in self.session_mapping:
            self.session_mapping[user_id] = str(uuid.uuid4())
            logger.info(f"为用户 {user_id} 创建新会话ID: {self.session_mapping[user_id]}")
        return self.session_mapping[user_id]
    
    async def handle_text_message(self, sender_staff_id: str, sender_nick: str, conversation_id: str, message_text: str):
        """处理单聊文本消息"""
        if not message_text:
            logger.warning(f"收到空消息，已忽略")
            return
        
        logger.info(f"处理单聊消息: '{message_text[:50]}...' 来自 {sender_nick} ({sender_staff_id})")
        
        # 检查是否是命令（以/开头）
        if message_text.startswith('/'):
            await self.handle_command(sender_staff_id, message_text)
            return
        
        # 获取会话ID
        session_id = self.get_user_session_id(sender_staff_id)
        
        # 向用户发送消息指示正在处理
        await self.sender.send_text_to_user(sender_staff_id, "正在处理您的请求...")
        
        try:
            # 获取用户的A2A客户端
            a2a_client = await self.get_user_a2a_client(sender_staff_id)
            
            # 创建任务ID
            task_id = str(uuid.uuid4())
            logger.info(f"创建新任务 ID: {task_id}")
            
            # 发送A2A任务请求
            response = await a2a_client.send_task(
                task_id=task_id,
                session_id=session_id,
                user_message=message_text
            )
            
            # 处理A2A响应
            await self.process_a2a_response(response, sender_staff_id)
            
        except a2a_types.A2AClientHTTPError as e:
            logger.error(f"A2A HTTP请求错误: {e.status_code} - {e.message}")
            await self.sender.send_text_to_user(
                sender_staff_id, 
                f"连接A2A服务时出错 (HTTP {e.status_code})，请稍后再试。"
            )
        except a2a_types.A2AClientJSONError as e:
            logger.error(f"A2A JSON解析错误: {e.message}")
            await self.sender.send_text_to_user(
                sender_staff_id, 
                "处理服务响应时出错，请稍后再试。"
            )
        except Exception as e:
            logger.error(f"处理消息时发生未知错误: {str(e)}", exc_info=True)
            await self.sender.send_text_to_user(
                sender_staff_id, 
                f"处理消息时出错: {str(e)}"
            )
    
    async def handle_command(self, user_id: str, command_text: str):
        """处理命令消息"""
        # 解析命令和参数
        parts = command_text.strip().split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        logger.info(f"处理命令: {command}，参数: {args}")
        
        # 检查命令是否存在
        if command in self.command_handlers:
            # 调用相应的命令处理函数
            await self.command_handlers[command](user_id, args)
        else:
            # 未知命令
            await self.sender.send_text_to_user(
                user_id,
                f"未知命令: {command}\n请使用 /help 查看可用命令列表"
            )
    
    async def handle_help_command(self, user_id: str, args: List[str]):
        """处理/help命令"""
        help_text = """可用命令列表：

/help - 显示此帮助信息
/server - 显示当前使用的A2A服务器地址
/setserver <url> - 设置你自己的A2A服务器地址
/resetserver - 重置为默认A2A服务器地址

示例：
/setserver http://example.com:10003
"""
        await self.sender.send_text_to_user(user_id, help_text)
    
    async def handle_server_command(self, user_id: str, args: List[str]):
        """处理/server命令，显示当前服务器地址"""
        # 获取用户配置的服务器地址
        user_server_url = db_manager.get_user_key(
            user_id, 
            'a2a_server_url', 
            self.default_a2a_server_url
        )
        
        # 检查是否使用的是默认地址
        if user_server_url == self.default_a2a_server_url:
            await self.sender.send_text_to_user(
                user_id,
                f"当前使用的是默认A2A服务器地址：\n{user_server_url}"
            )
        else:
            await self.sender.send_text_to_user(
                user_id,
                f"当前使用的是你配置的自定义A2A服务器地址：\n{user_server_url}"
            )
    
    async def handle_setserver_command(self, user_id: str, args: List[str]):
        """处理/setserver命令，设置自定义服务器地址"""
        if not args:
            await self.sender.send_text_to_user(
                user_id,
                "缺少服务器地址参数。请使用格式：\n/setserver http://example.com:10003"
            )
            return
        
        # 获取新的服务器地址
        new_server_url = args[0]
        
        # 验证URL格式
        if not new_server_url.startswith(('http://', 'https://')):
            await self.sender.send_text_to_user(
                user_id,
                "服务器地址格式不正确。必须以http://或https://开头"
            )
            return
        
        # 保存用户配置
        success = db_manager.update_user_key(user_id, 'a2a_server_url', new_server_url)
        
        if success:
            # 更新用户的A2A客户端
            client_updated = await self.update_user_a2a_client(user_id, new_server_url)
            
            if client_updated:
                await self.sender.send_text_to_user(
                    user_id,
                    f"已成功设置你的A2A服务器地址为：\n{new_server_url}"
                )
            else:
                await self.sender.send_text_to_user(
                    user_id,
                    f"服务器地址已保存，但更新客户端连接时出错。将在下次请求时使用新地址。"
                )
        else:
            await self.sender.send_text_to_user(
                user_id,
                "设置A2A服务器地址时出错，请稍后再试"
            )
    
    async def handle_resetserver_command(self, user_id: str, args: List[str]):
        """处理/resetserver命令，重置为默认服务器地址"""
        # 保存默认服务器地址到用户配置
        success = db_manager.update_user_key(user_id, 'a2a_server_url', self.default_a2a_server_url)
        
        if success:
            # 更新用户的A2A客户端
            client_updated = await self.update_user_a2a_client(user_id, self.default_a2a_server_url)
            
            if client_updated:
                await self.sender.send_text_to_user(
                    user_id,
                    f"已重置为默认A2A服务器地址：\n{self.default_a2a_server_url}"
                )
            else:
                await self.sender.send_text_to_user(
                    user_id,
                    f"已重置为默认服务器地址，但更新客户端连接时出错。将在下次请求时使用默认地址。"
                )
        else:
            await self.sender.send_text_to_user(
                user_id,
                "重置A2A服务器地址时出错，请稍后再试"
            )
    
    async def process_a2a_response(self, response: a2a_types.SendTaskResponse, user_id: str):
        """处理A2A响应并发送到钉钉"""
        if not response:
            await self.sender.send_text_to_user(user_id, "抱歉，服务器没有返回响应。")
            return
            
        # 检查响应错误
        if response.error:
            error = response.error
            error_message = f"错误 [{error.code}]: {error.message}"
            logger.error(f"A2A响应错误: {error_message}")
            await self.sender.send_text_to_user(user_id, error_message)
            return
            
        # 处理正常响应
        result = response.result
        if not result:
            await self.sender.send_text_to_user(user_id, "服务器返回了空的结果。")
            return
            
        # 检查任务状态
        status = result.status
        state = status.state
        
        if state == a2a_types.TaskState.COMPLETED:
            # 获取构件
            artifacts = result.artifacts or []
            if not artifacts:
                await self.sender.send_text_to_user(user_id, "任务完成，但没有生成任何内容。")
                return
                
            # 处理所有构件
            for artifact in artifacts:
                parts = artifact.parts
                for part in parts:
                    if part.type == "text":
                        text = part.text
                        # 将长消息拆分发送
                        await self.send_long_text(user_id, text)
                    elif part.type == "data":
                        # 发送结构化数据的摘要
                        data_summary = f"收到结构化数据: {json.dumps(part.data, ensure_ascii=False)[:100]}..."
                        await self.sender.send_text_to_user(user_id, data_summary)
                    elif part.type == "file":
                        # 发送文件信息
                        file_info = "收到文件: "
                        if part.file.name:
                            file_info += part.file.name
                        if part.file.uri:
                            file_info += f" (链接: {part.file.uri})"
                        await self.sender.send_text_to_user(user_id, file_info)
                        
        elif state == a2a_types.TaskState.INPUT_REQUIRED:
            # 需要用户输入
            message = status.message
            if message and message.parts:
                for part in message.parts:
                    if part.type == "text":
                        await self.sender.send_text_to_user(user_id, part.text)
            else:
                await self.sender.send_text_to_user(user_id, "需要更多信息，请提供详细说明。")
        else:
            # 其他状态
            status_text = f"任务状态: {state.value}"
            if status.message and status.message.parts:
                for part in status.message.parts:
                    if part.type == "text":
                        status_text += f"\n{part.text}"
            
            await self.sender.send_text_to_user(user_id, status_text)
    
    async def send_long_text(self, user_id: str, text: str, max_length: int = 2000):
        """分段发送长文本消息"""
        if len(text) <= max_length:
            await self.sender.send_text_to_user(user_id, text)
            return
            
        # 拆分文本
        parts = []
        for i in range(0, len(text), max_length):
            parts.append(text[i:i+max_length])
            
        # 发送多个部分
        for i, part in enumerate(parts, 1):
            part_text = f"[{i}/{len(parts)}]\n{part}"
            await self.sender.send_text_to_user(user_id, part_text)
            # 防止发送过快导致消息顺序错乱
            await asyncio.sleep(0.5)
    
    async def close(self):
        """关闭客户端连接"""
        logger.info("关闭所有A2A客户端连接...")
        
        # 关闭系统级A2A客户端
        await self.a2a_client.close()
        
        # 关闭所有用户级A2A客户端
        for user_id, (client, _) in self.user_a2a_clients.items():
            logger.info(f"关闭用户 {user_id} 的A2A客户端")
            await client.close()
        
        logger.info("所有A2A客户端已关闭")

async def main():
    """程序入口点"""
    try:
        # 创建并启动客户端
        client = DingTalkA2AClient()
        await client.startup()
    except Exception as e:
        logger.error(f"启动钉钉A2A客户端时出错: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 