#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
负责加载和管理项目配置
"""
import configparser
import os
import sys
from typing import Optional

class Config:
    """
    配置管理类
    加载项目配置并提供访问接口
    """
    def __init__(self):
        """初始化配置管理器"""
        self.config = configparser.ConfigParser()
        
        # 查找配置文件的多个可能位置
        config_paths = [
            # 1. 环境变量指定的路径
            os.environ.get('DINGTALK_A2A_CONFIG_PATH'),
            # 2. 当前脚本所在目录
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'),
            # 3. 当前工作目录
            os.path.join(os.getcwd(), 'config.ini'),
            # 4. 用户主目录
            os.path.join(os.path.expanduser("~"), '.dingtalk_a2a', 'config.ini')
        ]
        
        # 过滤掉None值并尝试每个路径
        config_found = False
        for path in [p for p in config_paths if p]:
            if os.path.exists(path):
                self.config.read(path, encoding='utf-8')
                print(f"已加载配置文件: {path}")
                config_found = True
                self.config_path = path
                break
        
        if not config_found:
            raise FileNotFoundError("无法找到配置文件config.ini，请确保它存在于项目目录中")
        
        # 检查必要的配置项
        self._check_required_configs()
    
    def _check_required_configs(self):
        """检查必要的配置项是否存在"""
        # 检查钉钉配置
        required_dingtalk_configs = [
            'dingtalk_client_id', 
            'dingtalk_client_secret', 
            'dingtalk_robot_code'
        ]
        
        for config_key in required_dingtalk_configs:
            if not self.config.has_option('dingtalk_config', config_key):
                raise ValueError(f"缺少必要的钉钉配置项: dingtalk_config.{config_key}")
        
        # 检查A2A配置
        if not self.config.has_option('a2a_config', 'a2a_server_url'):
            raise ValueError("缺少必要的A2A服务器配置: a2a_config.a2a_server_url")

    def get_config(self, section: str, key: str, default: Optional[str] = None) -> str:
        """
        获取配置项值
        
        Args:
            section: 配置区段名
            key: 配置键名
            default: 默认值（如果配置不存在）
            
        Returns:
            配置值或默认值
        """
        if self.config.has_option(section, key):
            return self.config.get(section, key)
        return default

# 全局配置实例
config = Config() 