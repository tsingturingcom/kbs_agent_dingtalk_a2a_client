#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块
提供全局一致的日志记录功能
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import datetime

# 创建日志目录
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# 设置日志文件名（带日期）
current_date = datetime.datetime.now().strftime('%Y-%m-%d')
log_file = os.path.join(log_dir, f'dingtalk_a2a_{current_date}.log')

# 配置日志格式
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s')

# 创建文件处理器（带文件轮换）
file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(log_formatter)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# 配置根日志记录器
logger = logging.getLogger('dingtalk_a2a')
logger.setLevel(logging.INFO)  # 默认INFO级别
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 设置日志级别（可通过环境变量覆盖）
log_level = os.environ.get('DINGTALK_A2A_LOG_LEVEL', 'INFO').upper()
if log_level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
    logger.setLevel(getattr(logging, log_level))
    logger.info(f"日志级别设置为: {log_level}")

# 导出为模块级别方法
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical

# 在启动时输出版本信息
info(f"钉钉A2A客户端日志系统初始化, Python版本: {sys.version}") 