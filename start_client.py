#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉 A2A 客户端启动脚本
"""
import os
import sys
import asyncio
import argparse

# 获取当前脚本的绝对路径
current_file = os.path.abspath(__file__)
# 获取项目目录
project_dir = os.path.dirname(current_file)
# 将项目目录添加到Python路径
sys.path.insert(0, project_dir)

# 处理命令行参数
def parse_arguments():
    parser = argparse.ArgumentParser(description='钉钉 A2A 客户端')
    parser.add_argument('--a2a-url', dest='a2a_url', 
                       default=None,
                       help='指定 A2A 服务器地址，例如 http://localhost:10003')
    
    return parser.parse_args()

async def start_client():
    """启动钉钉 A2A 客户端"""
    # 命令行参数
    args = parse_arguments()
    
    # 导入日志模块
    import logger
    
    # 如果指定了 A2A 服务器地址，则覆盖配置文件中的值
    if args.a2a_url:
        from config import config
        if not config.config.has_section('a2a_config'):
            config.config.add_section('a2a_config')
        config.config.set('a2a_config', 'a2a_server_url', args.a2a_url)
        logger.info(f"已设置 A2A 服务器地址: {args.a2a_url}")
    
    # 导入主模块
    try:
        from main import DingTalkA2AClient
        
        # 打印环境信息
        logger.info(f"Python版本: {sys.version}")
        logger.info(f"当前工作目录: {os.getcwd()}")
        logger.info(f"项目目录: {project_dir}")
        
        # 创建并启动客户端
        client = DingTalkA2AClient()
        await client.startup()
        
    except ImportError as e:
        logger.error(f"导入错误: {e}")
        logger.error("请确保已安装所有依赖。")
        sys.exit(1)
    except Exception as e:
        logger.error(f"启动客户端时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # 在Windows上使用asyncio需要设置策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 启动客户端
    asyncio.run(start_client()) 