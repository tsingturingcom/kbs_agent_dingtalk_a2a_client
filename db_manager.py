#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理模块
负责存储和管理用户的个性化配置
"""
import os
import json
import sqlite3
from typing import Dict, Any, Optional
import logger

class DBManager:
    """数据库管理类，用于存储用户配置"""
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径，默认为当前目录下的user_config.db
        """
        if db_path is None:
            # 默认在当前目录创建数据库文件
            self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_config.db')
        else:
            self.db_path = db_path
            
        logger.info(f"初始化数据库，路径: {self.db_path}")
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建用户配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_configs (
            user_id TEXT PRIMARY KEY,
            config_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")
    
    def get_user_config(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户配置
        
        Args:
            user_id: 钉钉用户ID
            
        Returns:
            用户配置字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT config_data FROM user_configs WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                logger.error(f"解析用户 {user_id} 的配置数据时出错")
                return {}
        return {}
    
    def set_user_config(self, user_id: str, config: Dict[str, Any]) -> bool:
        """
        设置用户配置
        
        Args:
            user_id: 钉钉用户ID
            config: 用户配置字典
            
        Returns:
            操作是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            config_json = json.dumps(config, ensure_ascii=False)
            
            # 检查用户是否已存在
            cursor.execute('SELECT 1 FROM user_configs WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # 更新配置
                cursor.execute('''
                UPDATE user_configs 
                SET config_data = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = ?
                ''', (config_json, user_id))
            else:
                # 插入新配置
                cursor.execute('''
                INSERT INTO user_configs (user_id, config_data) 
                VALUES (?, ?)
                ''', (user_id, config_json))
            
            conn.commit()
            conn.close()
            
            logger.info(f"已更新用户 {user_id} 的配置")
            return True
            
        except Exception as e:
            logger.error(f"保存用户 {user_id} 的配置时出错: {str(e)}")
            return False
    
    def update_user_key(self, user_id: str, key: str, value: Any) -> bool:
        """
        更新用户配置中的特定键值
        
        Args:
            user_id: 钉钉用户ID
            key: 配置键名
            value: 配置值
            
        Returns:
            操作是否成功
        """
        # 获取当前配置
        config = self.get_user_config(user_id)
        # 更新值
        config[key] = value
        # 保存配置
        return self.set_user_config(user_id, config)
    
    def get_user_key(self, user_id: str, key: str, default: Any = None) -> Any:
        """
        获取用户配置中的特定键值
        
        Args:
            user_id: 钉钉用户ID
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        config = self.get_user_config(user_id)
        return config.get(key, default)

# 全局数据库实例
db_manager = DBManager() 