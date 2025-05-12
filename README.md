# 钉钉 A2A 客户端

本项目是一个基于钉钉机器人的A2A（Agent-to-Agent）协议客户端，它可以将钉钉消息转换为A2A协议请求，并将A2A服务端的响应返回给钉钉用户。

## 功能特点

* 完整支持A2A协议核心功能
* 支持钉钉单聊消息转发到A2A服务
* 支持A2A服务器端的响应转发回钉钉消息
* 支持长文本自动分段发送
* 支持配置文件和命令行参数
* 提供详细的日志记录
* 支持用户通过聊天命令自定义A2A服务器地址
* 多用户配置持久化存储
* 用户级别A2A客户端连接池，支持长期任务执行
* 智能资源管理，自动清理不活跃连接

## 安装

### 前提条件

* Python 3.8+
* 钉钉开发者账号和机器人配置
* A2A 协议服务端

### 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

在运行前，请确保config.ini文件已正确配置：

```ini
[dingtalk_config]
dingtalk_client_id = 你的钉钉应用Client ID
dingtalk_client_secret = 你的钉钉应用Secret
dingtalk_robot_code = 你的钉钉机器人Code
robot_name = A2A助手
api_endpoint_auth = https://oapi.dingtalk.com
api_endpoint_contact = https://api.dingtalk.com

[a2a_config]
a2a_server_url = http://localhost:10003
retry_times = 3
timeout = 120
auto_reconnect = true

[client_pool_config]
# 清理间隔，单位：秒，默认3600秒（1小时）
cleanup_interval = 3600
# 不活跃超时，单位：秒，默认14400秒（4小时）
client_inactive_timeout = 14400
```

### 客户端连接池配置

在`[client_pool_config]`部分，您可以调整以下参数：

* `cleanup_interval` - 定期清理不活跃客户端的间隔时间（单位：秒）
* `client_inactive_timeout` - 客户端被视为不活跃的超时时间（单位：秒）

这些参数可以根据您的需求调整，例如：
- 对于资源有限的环境，可以缩短超时时间（如7200秒=2小时）
- 对于长期任务较多的环境，可以延长超时时间（如86400秒=24小时）

## 使用方法

### 启动客户端

```bash
python start_client.py
```

### 指定A2A服务器地址

```bash
python start_client.py --a2a-url http://your-a2a-server:port
```

### 聊天命令

客户端支持以下聊天命令：

* `/help` - 显示所有可用命令的帮助信息
* `/server` - 查看当前正在使用的A2A服务器地址
* `/setserver <url>` - 设置个人专属的A2A服务器地址
* `/resetserver` - 重置为默认A2A服务器地址

例如，设置个人服务器地址：
```
/setserver http://my-personal-a2a-server:8080
```

## 多用户配置与资源管理

* 每个钉钉用户可以设置自己专属的A2A服务器地址
* 用户配置存储在SQLite数据库中，配置会在重启客户端后保持不变
* 系统为每个用户维护单独的A2A客户端连接，确保任务持续执行
* 长期运行的A2A任务可以持续保持连接，不会因请求结束而中断
* 系统会定期清理长时间不活跃的客户端连接，优化资源使用

## 项目结构

```
kbs_agent_dingtalk_a2aclient/
├── config.ini              # 配置文件
├── config.py               # 配置管理模块
├── types.py                # A2A协议类型定义
├── a2a_client.py           # A2A协议客户端实现
├── dingtalk_sender.py      # 钉钉消息发送器
├── db_manager.py           # 数据库管理模块
├── logger.py               # 日志工具
├── main.py                 # 主程序
├── requirements.txt        # 依赖列表
├── start_client.py         # 启动脚本
├── user_config.db          # 用户配置数据库（自动创建）
└── logs/                   # 日志目录（自动创建）
```

## A2A协议支持

客户端实现了A2A协议的核心功能：

* JSON-RPC 2.0通信
* 任务发送/获取
* 消息和构件处理
* 错误处理
* 健康检查
* 长期任务处理 - 保持连接用于长时间运行的智能体任务

## 日志

日志文件存储在`logs/`目录下，可通过环境变量`DINGTALK_A2A_LOG_LEVEL`设置日志级别：

```bash
# 设置日志级别为DEBUG
export DINGTALK_A2A_LOG_LEVEL=DEBUG
python start_client.py
```

## 贡献

欢迎提交问题或改进建议。

## 许可

本项目采用 Apache License 2.0 开源协议。 